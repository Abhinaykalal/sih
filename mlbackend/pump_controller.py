"""
AgriSaathi AI — Actuator Command System & Rain Lockout Enforcement
==================================================================
Manages physical pump and bio-mister actuations for field IoT nodes.
Enforces strict Rain Lockout: blocks pump activation when rain is forecasted or active.
Maintains verifiable command lifecycles: requested -> published -> acknowledged -> executed.
"""

import time
import uuid
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone

try:
    from .mqtt_service import mqtt_manager
    from .config import settings
    from .internal_notifications import notification_service, NotificationType
except ImportError:
    from mqtt_service import mqtt_manager
    from config import settings
    from internal_notifications import notification_service, NotificationType

# In-memory command registry and idempotency cache
_commands_db: Dict[str, Dict[str, Any]] = {}
_idempotency_map: Dict[str, str] = {} # idempotency_key -> command_id

class PumpCommandRequest(BaseModel):
    device_id: str = "ESP32_NODE_01"
    command_type: str = "PUMP_ON" # PUMP_ON | PUMP_OFF | MISTER_ON | MISTER_OFF
    duration_sec: int = Field(default=300, ge=0, le=7200) # Max 2 hours
    reason: str = "Automated soil moisture replenishment"
    farm_id: Optional[str] = None
    zone_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    manual_override: bool = False
    active_rain: bool = False
    rain_probability_pct: float = 0.0
    rain_forecast_mm: float = 0.0

class PumpCommandResult(BaseModel):
    command_id: str
    device_id: str
    command_type: str
    status: str # requested | blocked | published | acknowledged | executed | failed | expired
    rain_lockout: bool
    reason: str
    created_at: str
    published_at: Optional[str] = None
    idempotency_key: Optional[str] = None

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
    """Controls and audits all actuator dispatch operations."""

    def __init__(self):
        self._audit_log: List[Dict[str, Any]] = []

    def dispatch(self, req: PumpCommandRequest, actor_id: Optional[str] = None) -> Dict[str, Any]:
        """Validates, checks rain lockout, and executes actuator commands."""
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # 1. Idempotency Check
        if req.idempotency_key and req.idempotency_key in _idempotency_map:
            existing_id = _idempotency_map[req.idempotency_key]
            if existing_id in _commands_db:
                return _commands_db[existing_id]

        cmd_id = f"cmd_{uuid.uuid4().hex[:12]}"
        if req.idempotency_key:
            _idempotency_map[req.idempotency_key] = cmd_id

        # 2. Rain Lockout Check for Activation Commands
        is_activation = req.command_type in ("PUMP_ON", "MISTER_ON")
        is_locked_out, lockout_reason = RainLockoutDecision.evaluate(
            active_rain=req.active_rain,
            rain_prob=req.rain_probability_pct,
            rain_mm=req.rain_forecast_mm
        )

        if is_activation and is_locked_out and not req.manual_override:
            # Command is BLOCKED by safety guardrails
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
            _commands_db[cmd_id] = record
            self._log_audit("ACTUATOR_COMMAND_BLOCKED", req.device_id, record)
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

        # 3. Publish to MQTT Downlink Topic
        record = {
            "command_id": cmd_id,
            "device_id": req.device_id,
            "command_type": req.command_type,
            "status": "published",
            "rain_lockout": False,
            "reason": req.reason if not req.manual_override else f"MANUAL_OVERRIDE: {req.reason}",
            "duration_sec": req.duration_sec,
            "created_at": now_iso,
            "published_at": now_iso,
            "idempotency_key": req.idempotency_key,
            "requested_by": actor_id
        }
        _commands_db[cmd_id] = record

        # Dispatch through MQTT Service Manager
        if mqtt_manager:
            mqtt_manager.publish_command(
                device_id=req.device_id,
                command=req.command_type,
                duration_sec=req.duration_sec,
                reason=record["reason"]
            )

        self._log_audit("ACTUATOR_COMMAND_PUBLISHED", req.device_id, record)
        return record

    def acknowledge_command(self, command_id: str, ack_payload: Optional[Dict[str, Any]] = None) -> bool:
        """Records hardware receipt acknowledgement."""
        if command_id in _commands_db:
            cmd = _commands_db[command_id]
            cmd["status"] = "acknowledged"
            cmd["acknowledged_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            cmd["acknowledgement_payload"] = ack_payload
            return True
        return False

    def confirm_execution(self, device_id: str, pump_active: bool, last_cmd_id: Optional[str] = None):
        """Confirms actual physical relay state change from inbound telemetry."""
        target_cmd_id = last_cmd_id
        if not target_cmd_id:
            # Find latest published command for this device
            for cid in reversed(list(_commands_db.keys())):
                c = _commands_db[cid]
                if c["device_id"] == device_id and c["status"] in ("published", "acknowledged"):
                    target_cmd_id = cid
                    break

        if target_cmd_id and target_cmd_id in _commands_db:
            cmd = _commands_db[target_cmd_id]
            expected_active = cmd["command_type"] == "PUMP_ON"
            if pump_active == expected_active:
                cmd["status"] = "executed"
                cmd["executed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                try:
                    notification_service.create_notification(
                        notification_type=NotificationType.PUMP_COMMAND_EXECUTED.value,
                        title="Pump Command Executed",
                        message=f"Actuator command {cmd['command_type']} confirmed active on {device_id}.",
                        severity="INFO",
                        device_id=device_id,
                        source_event_id=f"exec_{target_cmd_id}",
                        metadata={"command_id": target_cmd_id}
                    )
                except Exception:
                    pass

    def get_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Returns single command by ID."""
        return _commands_db.get(command_id)

    def get_history(self, device_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns list of recent commands sorted newest first."""
        cmds = list(_commands_db.values())
        if device_id:
            cmds = [c for c in cmds if c["device_id"] == device_id]
        return sorted(cmds, key=lambda x: x.get("created_at", ""), reverse=True)[:limit]

    def get_actuator_state(self, device_id: str = "ESP32_NODE_01") -> Dict[str, Any]:
        """Returns comprehensive actuator state breakdown adhering to the 12-state safety machine."""
        history = self.get_history(device_id=device_id, limit=1)
        latest_cmd = history[0] if history else None

        desired_state = latest_cmd.get("command_type") if latest_cmd else "PUMP_OFF"
        command_state = latest_cmd.get("status", "UNKNOWN").upper() if latest_cmd else "UNKNOWN"
        
        # Check if latest command is expired (published > 15 min ago with no execution confirmation)
        if latest_cmd and latest_cmd.get("status") in ("published", "acknowledged"):
            try:
                pub_time = datetime.fromisoformat(latest_cmd["created_at"].replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - pub_time).total_seconds() > 900:
                    command_state = "EXPIRED"
                    latest_cmd["status"] = "expired"
            except Exception:
                pass

        reported_state = "ON" if latest_cmd and latest_cmd.get("status") == "executed" and desired_state == "PUMP_ON" else "OFF"

        is_locked_out, lockout_reason = RainLockoutDecision.evaluate(
            active_rain=False,
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
            "provenance": "LIVE_SENSOR" if latest_cmd and latest_cmd.get("status") == "executed" else "RULE_BASED"
        }

    def _log_audit(self, event_type: str, device_id: str, details: Dict[str, Any]):
        self._audit_log.append({
            "event_type": event_type,
            "device_id": device_id,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "details": details
        })

pump_controller = PumpCommandController()

