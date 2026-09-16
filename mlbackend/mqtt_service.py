"""Real MQTT transport and strict telemetry validation for AgriSaathi."""
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple, Union

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

try:
    from .config import settings
except ImportError:
    from config import settings

_latest_telemetry: Dict[str, Dict[str, Any]] = {}
_device_lifecycle: Dict[str, Dict[str, Any]] = {}
_command_history: List[Dict[str, Any]] = []


def parse_and_validate_telemetry_payload(raw_payload: Union[str, Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:
    errors: List[str] = []
    try:
        data = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
    except Exception as exc:
        return False, None, [f"JSON parse failure: {exc}"]
    if not isinstance(data, dict):
        return False, None, ["Payload must be a JSON object"]

    device_id = data.get("device_id")
    if not isinstance(device_id, str) or not device_id.strip():
        return False, None, ["Missing or invalid device_id"]

    t = data.get("telemetry")
    if not isinstance(t, dict):
        return False, None, ["telemetry must be a JSON object"]
    actuator = data.get("actuator") if isinstance(data.get("actuator"), dict) else {}
    edge_ai = data.get("edge_ai") if isinstance(data.get("edge_ai"), dict) else {}

    def number(name, low=None, high=None):
        value = t.get(name)
        if value is None:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            errors.append(f"{name} must be numeric or null")
            return None
        if (low is not None and value < low) or (high is not None and value > high):
            errors.append(f"{name} outside allowed range")
        return value

    soil_moisture = number("soil_moisture_pct", 0, 100)
    soil_adc = t.get("soil_raw_adc")
    if soil_adc is not None:
        try:
            soil_adc = int(soil_adc)
            if not 0 <= soil_adc <= 4095:
                errors.append("soil_raw_adc outside 0-4095")
        except (TypeError, ValueError):
            errors.append("soil_raw_adc must be integer or null")
            soil_adc = None

    temperature = number("temperature_c", -10, 60)
    humidity = number("humidity_pct", 0, 100)
    vibration_rms = number("vibration_rms", 0, None)

    def nonnegative(name):
        value = t.get(name)
        if value is None:
            return None
        try:
            value = float(value)
            if value < 0:
                errors.append(f"{name} cannot be negative")
                return None
            return value
        except (TypeError, ValueError):
            errors.append(f"{name} must be numeric or null")
            return None

    nitrogen = nonnegative("nitrogen")
    phosphorus = nonnegative("phosphorus")
    potassium = nonnegative("potassium")

    sunlight = t.get("sunlight_detected")
    if sunlight is not None and not isinstance(sunlight, bool):
        errors.append("sunlight_detected must be boolean or null")
        sunlight = None
    vibration_detected = t.get("vibration_detected")
    if vibration_detected is not None and not isinstance(vibration_detected, bool):
        errors.append("vibration_detected must be boolean or null")
        vibration_detected = None
    pump_active = actuator.get("pump_active")
    if pump_active is not None and not isinstance(pump_active, bool):
        errors.append("pump_active must be boolean or null")
        pump_active = None

    confidence = edge_ai.get("confidence_pct")
    if confidence is not None:
        try:
            confidence = float(confidence)
            if not 0 <= confidence <= 100:
                errors.append("confidence_pct outside 0-100")
                confidence = None
        except (TypeError, ValueError):
            errors.append("confidence_pct must be numeric or null")
            confidence = None

    received = datetime.now(timezone.utc)
    record = {
        "device_id": device_id,
        "received_at": received.isoformat(),
        "received_at_timestamp": received.timestamp(),
        "device_timestamp": data.get("timestamp"),
        "telemetry": {
            "soil_moisture_pct": soil_moisture,
            "soil_raw_adc": soil_adc,
            "temperature_c": temperature,
            "humidity_pct": humidity,
            "sunlight_detected": sunlight,
            "vibration_detected": vibration_detected,
            "vibration_rms": vibration_rms,
            "nitrogen": nitrogen,
            "phosphorus": phosphorus,
            "potassium": potassium,
        },
        "actuator": {"pump_active": pump_active},
        "edge_ai": {"last_scan_result": edge_ai.get("last_scan_result"), "confidence_pct": confidence},
        "raw_payload": data,
        "ingestion_status": "VALID" if not errors else "INVALID",
        "validation_errors": errors,
        "data_source": data.get("data_source", "MQTT_EDGE"),
    }
    return not errors, record, errors


class MQTTServiceManager:
    def __init__(self):
        self.connected = False
        self.client_id = f"agrisaathi-backend-{uuid.uuid4().hex[:10]}"
        self.broker = settings.MQTT_BROKER_HOST
        self.port = settings.MQTT_BROKER_PORT
        self.uplink_topic = settings.MQTT_UPLINK_TOPIC
        self.downlink_topic = settings.MQTT_DOWNLINK_TOPIC
        self.status_topic = settings.MQTT_STATUS_TOPIC
        self.client = None

    @property
    def is_connected(self):
        return self.connected

    def connect(self) -> bool:
        if mqtt is None or not self.broker:
            self.connected = False
            return False
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id)
            if settings.MQTT_USERNAME:
                self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
            if settings.MQTT_USE_TLS:
                if settings.MQTT_CA_CERT:
                    self.client.tls_set(ca_certs=settings.MQTT_CA_CERT)
                else:
                    self.client.tls_set()
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            deadline = time.time() + 5
            while not self.connected and time.time() < deadline:
                time.sleep(0.05)
            return self.connected
        except Exception:
            self.connected = False
            return False

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        self.connected = int(reason_code) == 0
        if self.connected:
            client.subscribe(self.uplink_topic)
            client.subscribe(self.status_topic)

    def _on_message(self, client, userdata, message):
        payload = message.payload.decode("utf-8", errors="replace")
        if message.topic.endswith("/telemetry"):
            self.handle_telemetry_message(payload)
        elif message.topic.endswith("/status"):
            try:
                data = json.loads(payload)
                self.handle_status_message(data.get("device_id", "unknown"), data.get("status", "unknown"))
            except Exception:
                pass

    def disconnect(self):
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
        self.connected = False

    def handle_status_message(self, device_id: str, status_payload: str):
        status = str(status_payload).lower()
        if status not in {"online", "offline", "unknown"}:
            status = "unknown"
        node = _device_lifecycle.setdefault(device_id, {"device_id": device_id, "capabilities": {}})
        node.update({"status": status, "last_seen_at": datetime.now(timezone.utc).isoformat(), "last_seen_seconds_ago": 0})

    def handle_telemetry_message(self, raw_payload_str: str):
        ok, record, errors = parse_and_validate_telemetry_payload(raw_payload_str)
        if not ok or record is None:
            return {"status": "error", "errors": errors}
        device_id = record["device_id"]
        _latest_telemetry[device_id] = record
        _device_lifecycle.setdefault(device_id, {"device_id": device_id, "capabilities": {}}).update({
            "status": "online", "last_seen_at": record["received_at"], "last_seen_seconds_ago": 0
        })
        return {"status": "success", "device_id": device_id, "errors": errors}

    def get_latest_telemetry(self, device_id="ESP32_NODE_01"):
        return _latest_telemetry.get(device_id)

    def get_device_lifecycle(self, device_id="ESP32_NODE_01"):
        node = _device_lifecycle.get(device_id)
        if node and _latest_telemetry.get(device_id, {}).get("received_at_timestamp"):
            node["last_seen_seconds_ago"] = max(0, int(time.time() - _latest_telemetry[device_id]["received_at_timestamp"]))
        return node

    def publish_command(self, device_id: str, command: str, duration_sec=0, reason=""):
        if not self.connected or self.client is None:
            raise RuntimeError("MQTT broker is not connected; command was NOT published")
        command_id = f"cmd_{uuid.uuid4().hex}"
        now = int(time.time())
        topic = self.downlink_topic.format(device_id=device_id)
        payload = {
            "protocol_version": "1.0",
            "message_id": command_id,
            "command_id": command_id,
            "device_id": device_id,
            "command": command,
            "duration_sec": int(duration_sec),
            "reason": reason,
            "timestamp": now,
            "expires_at": now + max(60, int(duration_sec) + 120),
        }
        info = self.client.publish(topic, json.dumps(payload), qos=1, retain=False)
        info.wait_for_publish(timeout=5)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed with code {info.rc}")
        record = {"command_id": command_id, "device_id": device_id, "command": command, "status": "published", "published_at": datetime.now(timezone.utc).isoformat(), "payload": payload}
        _command_history.append(record)
        return record

    def get_command_history(self, device_id=None, limit=50):
        records = _command_history if device_id is None else [x for x in _command_history if x["device_id"] == device_id]
        return list(reversed(records[-limit:]))

mqtt_manager = MQTTServiceManager()
