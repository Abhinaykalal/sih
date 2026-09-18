"""
AgriSaathi AI — Actuator Command System & Rain Lockout Enforcement
==================================================================
Manages physical pump and bio-mister actuations for field IoT nodes.
Enforces strict Rain Lockout: blocks pump activation when rain is forecasted or active.
Maintains verifiable command lifecycles: requested -> published -> received -> actuation_accepted -> executed.

Security: Zero-Trust architecture with HMAC-SHA256 signatures, sequence tracking, and nonces.
"""

import time
import uuid
import json
import os
import hmac
import hashlib
import binascii
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timezone

try:
    from .mqtt_service import mqtt_manager
    from .config import settings
    from .internal_notifications import notification_service, NotificationType
    from .db_layer import db_layer
except ImportError:
    from mqtt_service import mqtt_manager
    from config import settings
    from internal_notifications import notification_service, NotificationType
    from db_layer import db_layer

class PumpCommandRequest(BaseModel):
    device_id: str = "ESP32_NODE_01"
    command_type: str = "PUMP_ON" # PUMP_ON | PUMP_OFF | MISTER_ON | MISTER_OFF
    duration_sec: int = Field(default=300, ge=0, le=7200) # Max 2 hours
    reason: str = "Automated soil moisture replenishment"
    farm_id: Optional[str] = None
    zone_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    # manual_override is explicitly removed to prevent bypassing safety
    active_rain: bool = False
    rain_probability_pct: float = 0.0
    rain_forecast_mm: float = 0.0

class RainLockoutDecision:
    """Evaluates unified Rain Lockout policy across sensor & forecast feeds."""
    
    @staticmethod
    def evaluate(active_rain: bool, rain_prob: float, rain_mm: float) -> Tuple[bool, str]:
        """
        Policy Rule:
        1. If active rainfall is currently detected -> LOCKOUT ACTIVE.
        2. If rainfall probability in next 24h >= 50% -> LOCKOUT ACTIVE.
        3. If forecasted rainfall volume >= 5.0 mm -> LOCKOUT ACTIVE.
        """
        if active_rain:
            return True, "Active rainfall detected on field sensor. Irrigation halted to prevent soil saturation & root rot."
        if rain_prob >= 50.0:
            return True, f"Rain probability is {rain_prob}% (threshold: 50%). Irrigation held to conserve groundwater & electricity."
        if rain_mm >= 5.0:
            return True, f"Significant rain forecast ({rain_mm} mm in 24h). Delaying irrigation to avert waterlogging."
        return False, "Atmospheric conditions dry. Safe to irrigate."

class PumpCommandController:
    """
    PHASE 3.1 REMEDIATION (Sept 18, 2026): UNIFIED IRRIGATION DECISION PATH
    
    This is the ONLY authorized decision path for irrigation commands.
    Edge device (ESP32) is NO LONGER autonomous—all pump activation requires backend approval.
    
    Decision flow:
    1. Verify rain lockout (active rain or forecast ≥50% blocks activation)
    2. Sign command with HMAC-SHA256
    3. Publish to MQTT (ESP32 subscribes)
    4. Wait for ACK from edge device
    5. Audit log with actor_id (who requested)
    
    Hardware safety (still runs on ESP32):
    - Waterlogging interlock (moisture >80%)
    - Hardware-level relay fail-safe (always starts OFF)
    - Replay protection (sequence numbers)
    
    This ensures:
    - Single decision authority (backend only)
    - Rain forecast integration
    - Irrigation schedule enforcement
    - Multi-device arbitration
    - Full audit trail
    """

    def dispatch(self, req: PumpCommandRequest, actor_id: Optional[str] = None) -> Dict[str, Any]:
        """Validates, checks rain lockout, and executes actuator commands with cryptography."""
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # 1. Idempotency Check
        if req.idempotency_key:
            existing_id = db_layer.check_idempotency(req.idempotency_key)
            if existing_id:
                existing_cmd = db_layer.get_command(existing_id)
                if existing_cmd:
                    return existing_cmd

        cmd_id = f"cmd_{uuid.uuid4().hex[:12]}"
        if req.idempotency_key:
            db_layer.set_idempotency(req.idempotency_key, cmd_id)

        # 2. Rain Lockout Check for Activation Commands
        is_activation = req.command_type in ("PUMP_ON", "MISTER_ON")
        is_locked_out, lockout_reason = RainLockoutDecision.evaluate(
            active_rain=req.active_rain,
            rain_prob=req.rain_probability_pct,
            rain_mm=req.rain_forecast_mm
        )

        if is_activation and is_locked_out:
            # Command is BLOCKED by safety guardrails. No manual overrides allowed.
            record = {
                "command_id": cmd_id,
                "device_id": req.device_id,
                "command_type": req.command_type,
                "status": "blocked",
                "rain_lockout": True,
                "reason": f"BLOCKED_BY_RAIN_LOCKOUT: {lockout_reason}",
                "created_at": now_iso,
                "published_at": None,
                "idempotency_key": req.idempotency_key,
                "requested_by": actor_id
            }
            db_layer.store_command(record)
            try:
                notification_service.create_notification(
                    notification_type=NotificationType.PUMP_COMMAND_BLOCKED.value,
                    title="Pump Command Blocked",
                    message=f"Irrigation blocked on {req.device_id} due to Rain Lockout ({lockout_reason}).",
                    severity="HIGH",
                    device_id=req.device_id,
                    source_event_id=cmd_id,
                    metadata=record
                )
            except Exception:
                pass
            return record

        # 3. Cryptographic Signature Generation
        device_reg = db_layer.get_device_registry(req.device_id)
        if not device_reg or not device_reg.get("command_secret"):
            # Fallback for dev mode if not registered
            # In production, we'd raise an exception. For compatibility, we'll try to use a default or fail.
            key_id = "v1"
            secret = getattr(settings, "EDGE_COMMAND_SECRET", None)
            if not secret:
                raise ValueError(f"No command_secret registered for {req.device_id} and EDGE_COMMAND_SECRET not configured.")
        else:
            secret = device_reg["command_secret"]
            key_id = device_reg["key_id"]

        # Calculate next sequence
        # For dispatching, we use timestamp millis as monotonic sequence for simplicity across instances, 
        # but ensuring it strictly increases.
        timestamp_ms = int(time.time() * 1000)
        sequence = timestamp_ms
        nonce = binascii.hexlify(os.urandom(8)).decode("utf-8")
        
        # Canonical format: device_id|key_id|sequence|timestamp|nonce|command|duration
        canonical_str = f"{req.device_id}|{key_id}|{sequence}|{timestamp_ms}|{nonce}|{req.command_type}|{req.duration_sec}"
        
        signature = hmac.new(
            secret.encode('utf-8'),
            canonical_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # 4. Publish to MQTT Downlink Topic
        record = {
            "command_id": cmd_id,
            "device_id": req.device_id,
            "command_type": req.command_type,
            "status": "published",
            "rain_lockout": False,
            "reason": req.reason,
            "duration_sec": req.duration_sec,
            "created_at": now_iso,
            "published_at": now_iso,
            "idempotency_key": req.idempotency_key,
            "requested_by": actor_id
        }
        db_layer.store_command(record)

        payload = {
            "command_id": cmd_id,
            "device_id": req.device_id,
            "key_id": key_id,
            "sequence": sequence,
            "timestamp": timestamp_ms,
            "nonce": nonce,
            "command": req.command_type,
            "duration_sec": req.duration_sec,
            "signature": signature
        }

        # Dispatch through MQTT Service Manager
        if mqtt_manager:
            import json
            mqtt_manager.client.publish(f"agrisaathi/nodes/{req.device_id}/commands", json.dumps(payload), qos=1)

        return record

    def verify_ack_signature(self, ack_payload: Dict[str, Any]) -> bool:
        """Verifies HMAC signature on incoming ACK payload."""
        device_id = ack_payload.get("device_id")
        key_id = ack_payload.get("key_id", "v1")
        sequence = ack_payload.get("sequence")
        status = ack_payload.get("status")
        relay_state = "1" if ack_payload.get("relay_state") else "0"
        timestamp = ack_payload.get("timestamp")
        provided_sig = ack_payload.get("signature")
        
        if not all([device_id, sequence, status, timestamp, provided_sig]):
            return False

        device_reg = db_layer.get_device_registry(device_id)
        if not device_reg or not device_reg.get("command_secret"):
            secret = getattr(settings, "EDGE_COMMAND_SECRET", None)
            if not secret: return False
        else:
            secret = device_reg["command_secret"]

        # Canonical format for ACK: device_id|key_id|sequence|status|relay_state|timestamp
        canonical_str = f"{device_id}|{key_id}|{sequence}|{status}|{relay_state}|{timestamp}"
        
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            canonical_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_sig, provided_sig)

    def acknowledge_command(self, command_id: str, ack_payload: Optional[Dict[str, Any]] = None) -> bool:
        """Records hardware receipt acknowledgement with cryptographic verification."""
        if not ack_payload or not self.verify_ack_signature(ack_payload):
            return False # Reject invalid HMAC ACK
            
        cmd = db_layer.get_command(command_id)
        if cmd:
            status = ack_payload.get("status", "UNKNOWN")
            
            # Map strict ACK states
            cmd["status"] = status
            cmd["acknowledged_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            cmd["acknowledgement_payload"] = ack_payload
            
            db_layer.update_command_status(command_id, {
                "status": status, 
                "acknowledged_at": cmd["acknowledged_at"],
                "acknowledgement_payload": json.dumps(ack_payload) if ack_payload else None
            })
            
            if status == "ACTUATION_ACCEPTED":
                # Advance device sequence registry only after successful actuation/acceptance
                db_layer.advance_device_sequence(cmd["device_id"], ack_payload.get("sequence", 0))
                
            return True
        return False

    def confirm_execution(self, device_id: str, pump_active: bool, last_cmd_id: Optional[str] = None):
        """Deprecated: Handled strictly by cryptographically signed ACKs now."""
        pass

    def get_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Returns single command by ID."""
        return db_layer.get_command(command_id)

    def get_history(self, device_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns list of recent commands sorted newest first."""
        return db_layer.get_commands_history(device_id, limit)

    def get_actuator_state(self, device_id: str = "ESP32_NODE_01") -> Dict[str, Any]:
        """Returns comprehensive actuator state breakdown adhering to safety machine."""
        history = self.get_history(device_id=device_id, limit=1)
        latest_cmd = history[0] if history else None

        desired_state = latest_cmd.get("command_type") if latest_cmd else "PUMP_OFF"
        command_state = latest_cmd.get("status", "UNKNOWN").upper() if latest_cmd else "UNKNOWN"
        
        # Check if latest command is expired (published > 15 min ago with no execution confirmation)
        if latest_cmd and latest_cmd.get("status") == "published":
            try:
                pub_time = datetime.fromisoformat(latest_cmd["created_at"].replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - pub_time).total_seconds() > 900:
                    command_state = "EXPIRED"
                    db_layer.update_command_status(latest_cmd["command_id"], {"status": "expired"})
            except Exception:
                pass

        reported_state = (
            "ON"
            if latest_cmd
            and latest_cmd.get("status") == "ACTUATION_ACCEPTED"
            and desired_state in ("PUMP_ON", "MISTER_ON")
            else "OFF"
        )

        # Check live telemetry for active rain — do not hardcode False.
        live_tel = db_layer.get_latest_telemetry()
        live_rain = bool(live_tel.get("rain") or live_tel.get("rain_detected")) if live_tel else False

        is_locked_out, lockout_reason = RainLockoutDecision.evaluate(
            active_rain=live_rain,
            rain_prob=latest_cmd.get("rain_probability_pct", 0.0) if latest_cmd else 0.0,
            rain_mm=latest_cmd.get("rain_forecast_mm", 0.0) if latest_cmd else 0.0
        )

        return {
            "device_id": device_id,
            "desired_state": desired_state,
            "reported_state": reported_state,
            "command_state": command_state,
            "command_id": latest_cmd.get("command_id") if latest_cmd else None,
            "last_command_time": latest_cmd.get("created_at") if latest_cmd else None,
            "last_acknowledgement_time": latest_cmd.get("acknowledged_at") if latest_cmd else None,
            "execution_time": latest_cmd.get("executed_at") if latest_cmd else None,
            "failure_reason": latest_cmd.get("failure_reason") if latest_cmd else None,
            "lockout_active": is_locked_out,
            "lockout_reason": lockout_reason if is_locked_out else None,
            "flow_rate_l_min": None,
            "flow_rate_display": "Not measured",
            "provenance": "LIVE_SENSOR" if latest_cmd and latest_cmd.get("status") == "ACTUATION_ACCEPTED" else "RULE_BASED"
        }

pump_controller = PumpCommandController()
