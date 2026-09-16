"""Actuator command validation and safety state handling.

This controller never treats a backend timer as physical execution and never
allows a mobile/client flag to bypass the server-side rain interlock.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field

try:
    from .mqtt_service import mqtt_manager
    from .internal_notifications import notification_service, NotificationType
except ImportError:
    from mqtt_service import mqtt_manager
    from internal_notifications import notification_service, NotificationType

_commands_db: Dict[str, Dict[str, Any]] = {}
_idempotency_map: Dict[str, str] = {}


class PumpCommandRequest(BaseModel):
    device_id: str = "ESP32_NODE_01"
    command_type: str = "PUMP_ON"
    duration_sec: int = Field(default=300, ge=0, le=7200)
    reason: str = "Farmer initiated irrigation"
    farm_id: Optional[str] = None
    zone_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    manual_override: bool = False
    active_rain: bool = False
    rain_probability_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    rain_forecast_mm: float = Field(default=0.0, ge=0.0)


class PumpCommandResult(BaseModel):
    command_id: str
    device_id: str
    command_type: str
    status: str
    rain_lockout: bool
    reason: str
    created_at: str
    published_at: Optional[str] = None
    idempotency_key: Optional[str] = None


class RainLockoutDecision:
    @staticmethod
    def evaluate(active_rain: bool, rain_prob: float, rain_mm: float) -> Tuple[bool, str]:
        if active_rain:
            return True, "Active rainfall detected; irrigation activation is blocked."
        if rain_prob >= 50.0:
            return True, f"Rain probability is {rain_prob:.1f}% (threshold: 50%)."
        if rain_mm >= 5.0:
            return True, f"Forecast rainfall is {rain_mm:.1f} mm (threshold: 5 mm)."
        return False, "No rain lockout condition detected."


class PumpCommandController:
    def __init__(self):
        self._audit_log: List[Dict[str, Any]] = []

    def dispatch(self, req: PumpCommandRequest, actor_id: Optional[str] = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        allowed_commands = {"PUMP_ON", "PUMP_OFF", "MISTER_ON", "MISTER_OFF"}
        if req.command_type not in allowed_commands:
            raise ValueError(f"Unsupported actuator command: {req.command_type}")

        if req.idempotency_key and req.idempotency_key in _idempotency_map:
            existing = _idempotency_map[req.idempotency_key]
            return _commands_db[existing]

        cmd_id = f"cmd_{uuid.uuid4().hex[:12]}"
        if req.idempotency_key:
            _idempotency_map[req.idempotency_key] = cmd_id

        activation = req.command_type in {"PUMP_ON", "MISTER_ON"}
        locked, lock_reason = RainLockoutDecision.evaluate(
            req.active_rain, req.rain_probability_pct, req.rain_forecast_mm
        )

        # A client cannot bypass a safety interlock by setting manualOverride.
        if activation and locked:
            record = {
                "command_id": cmd_id,
                "device_id": req.device_id,
                "command_type": req.command_type,
                "status": "blocked",
                "rain_lockout": True,
                "reason": f"BLOCKED_BY_RAIN_LOCKOUT: {lock_reason}",
                "created_at": now,
                "published_at": None,
                "idempotency_key": req.idempotency_key,
                "requested_by": actor_id,
                "manual_override_requested": bool(req.manual_override),
            }
            _commands_db[cmd_id] = record
            self._log_audit("ACTUATOR_COMMAND_BLOCKED", req.device_id, record)
            return record

        record = {
            "command_id": cmd_id,
            "device_id": req.device_id,
            "command_type": req.command_type,
            "status": "requested",
            "rain_lockout": False,
            "reason": req.reason,
            "duration_sec": req.duration_sec,
            "created_at": now,
            "published_at": None,
            "idempotency_key": req.idempotency_key,
            "requested_by": actor_id,
        }
        _commands_db[cmd_id] = record

        if not mqtt_manager:
            record["status"] = "failed"
            record["failure_reason"] = "MQTT service unavailable"
            return record
        try:
            transport = mqtt_manager.publish_command(
                device_id=req.device_id,
                command=req.command_type,
                duration_sec=req.duration_sec,
                reason=req.reason,
            )
        except Exception as exc:
            record["status"] = "failed"
            record["failure_reason"] = str(exc)
            self._log_audit("ACTUATOR_COMMAND_FAILED", req.device_id, record)
            return record

        record["status"] = "published"
        record["published_at"] = datetime.now(timezone.utc).isoformat()
        record["transport_command_id"] = transport.get("command_id")
        self._log_audit("ACTUATOR_COMMAND_PUBLISHED", req.device_id, record)
        return record

    def acknowledge_command(self, command_id: str, ack_payload: Optional[Dict[str, Any]] = None) -> bool:
        command = _commands_db.get(command_id)
        if not command:
            return False
        command["status"] = "acknowledged"
        command["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
        command["acknowledgement_payload"] = ack_payload or {}
        return True

    def confirm_execution(self, device_id: str, pump_active: bool, last_cmd_id: Optional[str] = None):
        target = _commands_db.get(last_cmd_id) if last_cmd_id else None
        if target is None:
            for command in reversed(list(_commands_db.values())):
                if command["device_id"] == device_id and command["status"] in {"published", "acknowledged"}:
                    target = command
                    break
        if not target:
            return False
        expected = target["command_type"] == "PUMP_ON"
        if pump_active != expected:
            target["status"] = "failed"
            target["failure_reason"] = "Physical actuator state did not match requested command."
            return False
        target["status"] = "executed"
        target["executed_at"] = datetime.now(timezone.utc).isoformat()
        return True

    def get_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        return _commands_db.get(command_id)

    def get_history(self, device_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        commands = list(_commands_db.values())
        if device_id:
            commands = [c for c in commands if c["device_id"] == device_id]
        return sorted(commands, key=lambda x: x.get("created_at", ""), reverse=True)[:limit]

    def get_actuator_state(self, device_id: str = "ESP32_NODE_01") -> Dict[str, Any]:
        history = self.get_history(device_id, 1)
        latest = history[0] if history else None
        telemetry = mqtt_manager.get_latest_telemetry(device_id) if mqtt_manager else None
        physical = None
        if telemetry:
            physical = telemetry.get("actuator", {}).get("pump_active")

        command_state = latest.get("status", "UNKNOWN").upper() if latest else "UNKNOWN"
        desired = latest.get("command_type", "PUMP_OFF") if latest else "PUMP_OFF"
        reported = "ON" if physical is True else "OFF" if physical is False else "UNKNOWN"

        return {
            "device_id": device_id,
            "desired_state": desired,
            "reported_state": reported,
            "command_state": command_state,
            "command_id": latest.get("command_id") if latest else None,
            "last_command_time": latest.get("created_at") if latest else None,
            "last_acknowledgement_time": latest.get("acknowledged_at") if latest else None,
            "execution_time": latest.get("executed_at") if latest else None,
            "failure_reason": latest.get("failure_reason") if latest else None,
            "lockout_active": False,
            "lockout_reason": None,
            "flow_rate_l_min": None,
            "flow_rate_display": "Not measured",
            "provenance": "LIVE_SENSOR" if physical is not None else "UNAVAILABLE",
        }

    def _log_audit(self, event_type: str, device_id: str, details: Dict[str, Any]):
        self._audit_log.append({
            "event_type": event_type,
            "device_id": device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        })


pump_controller = PumpCommandController()
