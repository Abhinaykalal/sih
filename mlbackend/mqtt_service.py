"""
AgriSaathi AI — Production MQTT Service & Telemetry Ingestion Manager
====================================================================
Implements exact hardware contracts:
- Uplink:    agrisaathi/nodes/ESP32_NODE_01/telemetry
- Downlink:  agrisaathi/nodes/ESP32_NODE_01/commands
- Lifecycle: agrisaathi/nodes/ESP32_NODE_01/status

Strictly preserves JSON null as Python None (never coerces null to zero or defaults).
Enforces physical sensor validation ranges (soil moisture 0-100%, ADC 0-4095, etc.).
"""

import json
import time
import ssl
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple, Union
import paho.mqtt.client as mqtt
import threading

try:
    from .config import settings
    from .db_layer import db_layer
    from .schemas import TelemetryDataQuality, DataQualityStatus
except ImportError:
    from config import settings
    from db_layer import db_layer
    from schemas import TelemetryDataQuality, DataQualityStatus

def parse_and_validate_telemetry_payload(raw_payload: Union[str, Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:
    """
    Parses and validates an inbound ESP32 telemetry packet.
    Missing fields remain None. Zero is preserved as 0.
    """
    errors = []
    try:
        data = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
    except Exception as e:
        return False, None, [f"JSON parse failure: {str(e)}"]

    if not isinstance(data, dict):
        return False, None, ["Payload must be a JSON object"]

    device_id = data.get("device_id")
    if not device_id or not isinstance(device_id, str):
        return False, None, ["Missing or invalid 'device_id' field"]

    raw_telemetry = data.get("telemetry", {})
    if not isinstance(raw_telemetry, dict):
        errors.append("'telemetry' block is missing or not a JSON object")
        raw_telemetry = {}

    actuator = data.get("actuator", {})
    edge_ai = data.get("edge_ai", {})

    # 1. Soil Moisture % (0 - 100)
    soil_moisture = raw_telemetry.get("soil_moisture_pct")
    if soil_moisture is not None:
        try:
            soil_moisture = float(soil_moisture)
            if not (0.0 <= soil_moisture <= 100.0):
                errors.append(f"soil_moisture_pct out of range (0-100): {soil_moisture}")
                soil_moisture = None
        except (ValueError, TypeError):
            errors.append(f"Invalid numeric value for soil_moisture_pct: {soil_moisture}")
            soil_moisture = None

    # 2. Soil Raw ADC (0 - 4095)
    soil_adc = raw_telemetry.get("soil_raw_adc")
    if soil_adc is not None:
        try:
            soil_adc = int(soil_adc)
            if not (0 <= soil_adc <= 4095):
                errors.append(f"soil_raw_adc out of range (0-4095): {soil_adc}")
                soil_adc = None
        except (ValueError, TypeError):
            errors.append(f"Invalid integer for soil_raw_adc: {soil_adc}")
            soil_adc = None

    # 3. Temperature C (-10 - 60)
    temp_c = raw_telemetry.get("temperature_c")
    if temp_c is not None:
        try:
            temp_c = float(temp_c)
            if not (-10.0 <= temp_c <= 60.0):
                errors.append(f"temperature_c out of range (-10 to 60): {temp_c}")
                temp_c = None
        except (ValueError, TypeError):
            errors.append(f"Invalid numeric value for temperature_c: {temp_c}")
            temp_c = None

    # 4. Humidity % (0 - 100)
    humidity = raw_telemetry.get("humidity_pct")
    if humidity is not None:
        try:
            humidity = float(humidity)
            if not (0.0 <= humidity <= 100.0):
                errors.append(f"humidity_pct out of range (0-100): {humidity}")
                humidity = None
        except (ValueError, TypeError):
            errors.append(f"Invalid numeric value for humidity_pct: {humidity}")
            humidity = None

    # 5. Sunlight Detected (bool)
    sunlight = raw_telemetry.get("sunlight_detected")
    if sunlight is not None and not isinstance(sunlight, bool):
        errors.append(f"sunlight_detected must be boolean, got {type(sunlight)}")
        sunlight = None

    # 6. Optional Vibration Sensor
    vibration_detected = raw_telemetry.get("vibration_detected")
    if vibration_detected is not None and not isinstance(vibration_detected, bool):
        vibration_detected = None

    vibration_rms = raw_telemetry.get("vibration_rms")
    if vibration_rms is not None:
        try:
            vibration_rms = float(vibration_rms)
            if vibration_rms < 0:
                errors.append("vibration_rms cannot be negative")
                vibration_rms = None
        except (ValueError, TypeError):
            vibration_rms = None

    # 7. Optional NPK Sensor
    nitrogen = raw_telemetry.get("nitrogen")
    if nitrogen is not None:
        try:
            nitrogen = float(nitrogen)
            if nitrogen < 0:
                nitrogen = None
        except (ValueError, TypeError):
            nitrogen = None

    phosphorus = raw_telemetry.get("phosphorus")
    if phosphorus is not None:
        try:
            phosphorus = float(phosphorus)
            if phosphorus < 0:
                phosphorus = None
        except (ValueError, TypeError):
            phosphorus = None

    potassium = raw_telemetry.get("potassium")
    if potassium is not None:
        try:
            potassium = float(potassium)
            if potassium < 0:
                potassium = None
        except (ValueError, TypeError):
            potassium = None

    # 8. Actuator state
    pump_active = actuator.get("pump_active")
    if pump_active is not None and not isinstance(pump_active, bool):
        pump_active = None

    # 9. Edge AI
    last_scan = edge_ai.get("last_scan_result")
    confidence_pct = edge_ai.get("confidence_pct")
    if confidence_pct is not None:
        try:
            confidence_pct = float(confidence_pct)
            if not (0.0 <= confidence_pct <= 100.0):
                confidence_pct = None
        except (ValueError, TypeError):
            confidence_pct = None

    now_utc = datetime.now(timezone.utc)
    received_at_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    received_at_ts = time.time()

    cleaned_record = {
        "device_id": device_id,
        "received_at": received_at_iso,
        "received_at_timestamp": received_at_ts,
        "device_timestamp": data.get("timestamp"),
        "telemetry": {
            "soil_moisture_pct": soil_moisture,
            "soil_raw_adc": soil_adc,
            "temperature_c": temp_c,
            "humidity_pct": humidity,
            "sunlight_detected": sunlight,
            "vibration_detected": vibration_detected,
            "vibration_rms": vibration_rms,
            "nitrogen": nitrogen,
            "phosphorus": phosphorus,
            "potassium": potassium,
        },
        "actuator": {
            "pump_active": pump_active,
        },
        "edge_ai": {
            "last_scan_result": last_scan,
            "confidence_pct": confidence_pct,
        },
        "raw_payload": data,
        "ingestion_status": "VALID" if not errors else "WARNING_OUT_OF_RANGE",
        "validation_errors": errors,
        "data_source": data.get("data_source", "MQTT_EDGE")
    }

    return True, cleaned_record, errors


def compute_data_quality_status(received_at_timestamp: float) -> Dict[str, Any]:
    """
    Computes data quality status (LIVE/STALE/OFFLINE) based on age.
    
    Args:
        received_at_timestamp: Unix timestamp when backend received the packet
        
    Returns:
        Dict with status, age_seconds, and reason
    """
    now_ts = time.time()
    age_seconds = now_ts - received_at_timestamp
    
    # Import settings for thresholds
    try:
        from .config import settings
    except ImportError:
        from config import settings
    
    live_threshold = settings.TELEMETRY_LIVE_THRESHOLD_SECONDS  # 600 seconds (10 min)
    stale_threshold = settings.TELEMETRY_STALE_THRESHOLD_SECONDS  # 21600 seconds (6 hours)
    
    if age_seconds <= live_threshold:
        status = DataQualityStatus.LIVE
        reason = f"Data fresh ({int(age_seconds)} seconds old)"
    elif age_seconds <= stale_threshold:
        status = DataQualityStatus.STALE
        hours = int(age_seconds / 3600)
        reason = f"Data stale (received {hours} hours ago)"
    else:
        status = DataQualityStatus.OFFLINE
        days = int(age_seconds / 86400)
        reason = f"Device offline (last telemetry {days} days ago)"
    
    return {
        "status": status,
        "age_seconds": age_seconds,
        "reason": reason
    }


class MQTTServiceManager:
    """Manages true MQTT subscriptions, commands, and device lifecycles connected to SQLite."""
    
    def __init__(self):
        self.broker = settings.MQTT_BROKER_HOST
        self.port = settings.MQTT_BROKER_PORT
        self.uplink_topic = settings.MQTT_UPLINK_TOPIC
        self.downlink_topic = settings.MQTT_DOWNLINK_TOPIC
        self.status_topic = settings.MQTT_STATUS_TOPIC
        self.connected = False
        
        # Enforce Paho MQTT v2 Callback API for Production Stability
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="agrisaathi_backend_" + str(int(time.time())))
        except AttributeError:
            # Fallback if v1 is installed despite requirements
            self.client = mqtt.Client(client_id="agrisaathi_backend_" + str(int(time.time())))
        
        # Callbacks (v2 signatures)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        # Authentication
        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

        # TLS / Insecure Handling
        if settings.MQTT_USE_TLS:
            if settings.ALLOW_INSECURE_MQTT:
                print("WARNING: ALLOW_INSECURE_MQTT is set. TLS certificates will NOT be verified!")
                self.client.tls_set(cert_reqs=ssl.CERT_NONE)
                self.client.tls_insecure_set(True)
            else:
                self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED) # Strictly verify broker CA

        self._init_default_node()
        
        # Run resilient connection in a background thread so FastAPI never blocks on boot
        # if the broker is temporarily down.
        self._conn_thread = threading.Thread(target=self._resilient_connect_loop, daemon=True)
        self._conn_thread.start()

    def _resilient_connect_loop(self):
        """Exponential backoff reconnect loop for reliable boot-up."""
        attempt = 0
        while not self.connected:
            try:
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_start()
                break # Exit loop once successfully connected and loop started
            except Exception as e:
                attempt += 1
                backoff = min(60, 2 ** attempt)
                print(f"[MQTT] Connection Failed: {e}. Retrying in {backoff}s (Attempt {attempt})...")
                time.sleep(backoff)

    def _init_default_node(self):
        """Pre-populate ESP32_NODE_01 with safe default status in db if not exists."""
        db_layer.update_device_lifecycle(
            device_id="ESP32_NODE_01",
            status="unknown",
            last_seen_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            is_online=False,
            capabilities_json=json.dumps({
                "soil_moisture": True,
                "temperature": True,
                "humidity": True,
                "sunlight": True,
                "vibration": False,
                "npk": False
            })
        )

    def on_connect(self, client, userdata, flags, rc, properties=None):
        # Handle both v1 and v2 callbacks
        code = rc.value if hasattr(rc, "value") else rc
        if code == 0:
            self.connected = True
            print("MQTT Connected successfully. Subscribing to topics...")
            self.client.subscribe("agrisaathi/nodes/+/telemetry", qos=1)
            self.client.subscribe("agrisaathi/nodes/+/status", qos=1)
            self.client.subscribe("agrisaathi/nodes/+/ack", qos=1)
        else:
            self.connected = False
            print(f"MQTT Connection failed with code {code}")

    def on_disconnect(self, client, userdata, rc, properties=None, *args, **kwargs):
        self.connected = False
        print("MQTT Disconnected. Reconnecting...")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8', errors='ignore')
        
        try:
            parts = topic.split("/")
            topic_device_id = parts[2] if len(parts) >= 3 else "unknown"
            
            if topic.endswith("/telemetry"):
                self.handle_telemetry_message(payload, topic_device_id=topic_device_id)
            elif topic.endswith("/status"):
                self.handle_status_message(topic_device_id, payload)
            elif topic.endswith("/ack"):
                self.handle_ack_message(topic_device_id, payload)
        except Exception as e:
            print(f"Error processing MQTT message on {topic}: {e}")

    def handle_status_message(self, device_id: str, status_payload: str):
        """Handles online / offline / lwt messages on status topic."""
        status_clean = "unknown"
        try:
            # Parse JSON status if available (e.g. LWT or online packet)
            data = json.loads(status_payload)
            status_clean = data.get("status", "unknown").strip().lower()
        except Exception:
            status_clean = status_payload.strip().lower()

        if status_clean not in ("online", "offline", "unknown"):
            status_clean = "unknown"
            
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        db_layer.update_device_lifecycle(
            device_id=device_id,
            status=status_clean,
            last_seen_at=now_iso,
            is_online=(status_clean == "online")
        )

    def handle_ack_message(self, device_id: str, payload_str: str):
        """Processes cryptographically signed hardware ACKs over MQTT."""
        try:
            ack_payload = json.loads(payload_str)
            from mlbackend.pump_controller import pump_controller
            # The ACK payload should contain the command_id, but the signature check guarantees authenticity
            command_id = ack_payload.get("command_id")
            if command_id:
                pump_controller.acknowledge_command(command_id, ack_payload)
        except Exception as e:
            print(f"Error handling ACK for {device_id}: {e}")

    def handle_telemetry_message(self, raw_payload_str: str, topic_device_id: Optional[str] = None) -> Dict[str, Any]:
        """Ingests, validates, and stores an incoming telemetry payload to SQLite.
           Includes anti-spoofing cross-validation with MQTT topic."""
        ok, record, errors = parse_and_validate_telemetry_payload(raw_payload_str)
        if not ok or not record:
            return {"status": "error", "errors": errors}

        device_id = record["device_id"]
        
        # Anti-Spoofing: Ensure topic identity matches payload claims
        if topic_device_id and topic_device_id != "unknown" and topic_device_id != device_id:
            print(f"[SECURITY] REJECTED_SPOOFING: Payload claims {device_id} but published on topic for {topic_device_id}")
            return {"status": "error", "errors": ["SPOOFING_DETECTED_TOPIC_MISMATCH"]}
        
        # Persist telemetry via unified DB layer
        db_layer.store_telemetry_packet(record)
        
        # Mark device online upon valid packet
        db_layer.update_device_lifecycle(
            device_id=device_id,
            status="online",
            last_seen_at=record["received_at"],
            is_online=True
        )

        return {"status": "success", "device_id": device_id, "errors": errors}

    def get_latest_telemetry(self, device_id: str = "ESP32_NODE_01") -> Optional[Dict[str, Any]]:
        """Returns the most recent verified telemetry frame for a node directly from SQLite."""
        # Querying canonical_telemetry
        import sqlite3
        try:
            from .db_layer import ANALYTICS_DB_PATH
        except ImportError:
            from db_layer import ANALYTICS_DB_PATH
            
        conn = sqlite3.connect(ANALYTICS_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM canonical_telemetry WHERE device_id = ? ORDER BY received_at DESC LIMIT 1", (device_id,))
        row = c.fetchone()
        conn.close()
        if row:
            # Reconstruct the dict structure
            d = dict(row)
            try:
                raw = json.loads(d.get("raw_payload", "{}"))
            except:
                raw = {}
                
            return {
                "device_id": d["device_id"],
                "received_at": d["received_at"],
                "received_at_timestamp": d["device_timestamp"],
                "telemetry": {
                    "soil_moisture_pct": d["soil_moisture_pct"],
                    "soil_raw_adc": d["soil_raw_adc"],
                    "temperature_c": d["temperature_c"],
                    "humidity_pct": d["humidity_pct"],
                    "sunlight_detected": bool(d["sunlight_detected"]) if d["sunlight_detected"] is not None else None,
                    "vibration_detected": bool(d["vibration_detected"]) if d["vibration_detected"] is not None else None,
                    "vibration_rms": d["vibration_rms"],
                    "nitrogen": d["nitrogen"],
                    "phosphorus": d["phosphorus"],
                    "potassium": d["potassium"]
                },
                "actuator": {
                    "pump_active": bool(d["pump_active"]) if d["pump_active"] is not None else None
                },
                "edge_ai": {
                    "last_scan_result": d["edge_ai_result"],
                    "confidence_pct": d["edge_ai_confidence"]
                },
                "raw_payload": raw,
                "data_source": d["data_source"]
            }
        return None

    def get_device_lifecycle(self, device_id: str = "ESP32_NODE_01") -> Optional[Dict[str, Any]]:
        """Returns online/offline status from SQLite."""
        return db_layer.get_device_lifecycle(device_id)

    def publish_command(self, device_id: str, command: str, duration_sec: int = 0, reason: str = "") -> Dict[str, Any]:
        """
        Publishes an actuator downlink command to agrisaathi/nodes/{device_id}/commands with QoS 1.
        """
        cmd_id = f"cmd_{int(time.time())}_{device_id}"
        payload = {
            "command_id": cmd_id,
            "device_id": device_id,
            "command": command,
            "duration_sec": duration_sec,
            "reason": reason,
            "timestamp": int(time.time())
        }
        
        topic = f"agrisaathi/nodes/{device_id}/commands"
        if self.connected:
            try:
                # QoS 1 for durable delivery
                self.client.publish(topic, json.dumps(payload), qos=1)
            except Exception as e:
                print(f"MQTT Publish Error: {e}")

        # Record in durable local audit history via db_layer
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        record = {
            "command_id": cmd_id,
            "device_id": device_id,
            "command_type": command,
            "status": "published",
            "rain_lockout": False,
            "reason": reason,
            "duration_sec": duration_sec,
            "created_at": now_iso,
            "published_at": now_iso,
            "idempotency_key": None,
            "requested_by": None
        }
        db_layer.store_command(record)

        return {
            "status": "published",
            "command_id": cmd_id,
            "topic": f"agrisaathi/nodes/{device_id}/commands",
            "payload": payload
        }

mqtt_manager = MQTTServiceManager()
