# AgriSaathi — Canonical Schema Designs

This document defines the exact schema contracts that all components must implement to fix the architecture.

---

## SCHEMA 1: Canonical Telemetry Response (Task #3)

This is the single response schema used by all telemetry endpoints.

### Core Principle

**Every telemetry response MUST include:**
1. **Actual sensor values** (null if not received)
2. **Freshness metadata** (age_seconds, received_at)
3. **Data quality classification** (LIVE, STALE, OFFLINE, UNAVAILABLE)
4. **Explicit data sources** (where each field came from)
5. **No defaults** (null stays null)

### Schema

```python
# File: mlbackend/schemas.py (NEW FILE)

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel
from datetime import datetime

class TelemetryDataQuality(BaseModel):
    """Classification of data freshness and reliability"""
    status: Literal["LIVE", "STALE", "OFFLINE", "UNAVAILABLE"]
    age_seconds: Optional[int] = None
    threshold_exceeded: bool = False
    reason: Optional[str] = None
    
    @property
    def is_usable_for_ai(self) -> bool:
        """Can AI predictions be made with this data?"""
        return self.status in ("LIVE", "STALE") and self.age_seconds is not None and self.age_seconds < 86400

class SensorReading(BaseModel):
    """Single sensor value with provenance"""
    value: Optional[float] = None
    unit: Optional[str] = None
    sensor_type: Optional[str] = None
    data_source: Optional[Literal["ESP32", "API", "MANUAL", "SIMULATED"]] = None
    confidence: Optional[float] = None  # 0.0-1.0, null if unknown
    
    def is_valid(self) -> bool:
        """Can this value be used for AI?"""
        return self.value is not None and self.data_source != "SIMULATED"

class CanonicalTelemetry(BaseModel):
    """
    Single canonical telemetry response used by ALL endpoints.
    Rules:
    - No synthetic defaults
    - Null stays null
    - Every field includes data_source and timestamp
    """
    
    status: Literal["OK", "PARTIAL_DATA", "INSUFFICIENT_DATA", "ERROR"]
    device_id: str
    
    # Timestamps
    received_at: str  # ISO format, when backend received the packet
    device_timestamp: Optional[int] = None  # Milliseconds from device clock (if available)
    age_seconds: int  # How old is this data? (computed as now - received_at)
    
    # Data Quality
    data_quality: TelemetryDataQuality
    
    # Actual Sensor Values (null if not received)
    telemetry: Dict[str, Optional[float]] = {
        "soil_moisture_pct": None,
        "soil_temperature_c": None,
        "air_temperature_c": None,
        "humidity_pct": None,
        "ph": None,
        "ec_ms_cm": None,
        "nitrogen_ppm": None,
        "phosphorus_ppm": None,
        "potassium_ppm": None,
        "rainfall_mm": None,
        "sunlight_detected": None,
        "vibration_detected": None,
        "vibration_rms": None,
    }
    
    # Actuator State
    actuator: Dict[str, Optional[bool]] = {
        "pump_active": None,
        "mister_active": None,
    }
    
    # Edge AI (if device computed local risk)
    edge_ai: Optional[Dict[str, Any]] = {
        "last_scan_result": None,
        "confidence_pct": None,
    }
    
    # Data Sources (transparency)
    data_sources: Dict[str, str] = {
        # Example:
        # "soil_moisture_pct": "ESP32_MQTT",
        # "air_temperature_c": "ESP32_MQTT",
        # "ph": "NOT_AVAILABLE",
        # "rainfall_mm": "OPENWEATHER_API"
    }
    
    # Warnings & Issues
    validation_errors: list[str] = []
    warnings: list[str] = []
    
    # Lineage & Audit
    packet_hash: Optional[str] = None  # MD5 of raw payload (for deduplication)
    data_source: Literal["MQTT_EDGE", "HTTP_DIRECT", "SIMULATED", "UNAVAILABLE"] = "MQTT_EDGE"

class TelemetryResponse(BaseModel):
    """Wrapper for all telemetry API responses"""
    error: bool = False
    message: Optional[str] = None
    telemetry: Optional[CanonicalTelemetry] = None
    timestamp: str  # When response was generated

```

### Example: Device ONLINE with LIVE Data

```json
{
  "error": false,
  "telemetry": {
    "status": "OK",
    "device_id": "ESP32_NODE_01",
    "received_at": "2026-09-17T13:20:15Z",
    "device_timestamp": null,
    "age_seconds": 42,
    "data_quality": {
      "status": "LIVE",
      "age_seconds": 42,
      "threshold_exceeded": false,
      "reason": "Data received within 10-minute threshold"
    },
    "telemetry": {
      "soil_moisture_pct": 42.7,
      "soil_temperature_c": null,
      "air_temperature_c": 29.4,
      "humidity_pct": 68.2,
      "ph": null,
      "ec_ms_cm": null,
      "nitrogen_ppm": null,
      "phosphorus_ppm": null,
      "potassium_ppm": null,
      "rainfall_mm": null,
      "sunlight_detected": null,
      "vibration_detected": null,
      "vibration_rms": null
    },
    "actuator": {
      "pump_active": false,
      "mister_active": null
    },
    "edge_ai": {
      "last_scan_result": "NORMAL",
      "confidence_pct": null
    },
    "data_sources": {
      "soil_moisture_pct": "ESP32_MQTT",
      "air_temperature_c": "ESP32_MQTT",
      "humidity_pct": "ESP32_MQTT",
      "pump_active": "ESP32_MQTT",
      "ph": "NOT_AVAILABLE",
      "rainfall_mm": "NOT_AVAILABLE"
    },
    "validation_errors": [],
    "warnings": [],
    "packet_hash": "a3f2e8d1c9b4e7f2a5d8c1e4b7a0d3f6",
    "data_source": "MQTT_EDGE"
  },
  "timestamp": "2026-09-17T13:20:57Z"
}
```

### Example: Device OFFLINE (No Recent Data)

```json
{
  "error": false,
  "telemetry": {
    "status": "INSUFFICIENT_DATA",
    "device_id": "ESP32_NODE_01",
    "received_at": "2026-09-14T09:15:00Z",
    "device_timestamp": null,
    "age_seconds": 289200,
    "data_quality": {
      "status": "OFFLINE",
      "age_seconds": 289200,
      "threshold_exceeded": true,
      "reason": "No telemetry received for 80 hours. Device likely offline."
    },
    "telemetry": {
      "soil_moisture_pct": null,
      "air_temperature_c": null,
      "humidity_pct": null,
      "ph": null,
      "ec_ms_cm": null,
      "nitrogen_ppm": null,
      "phosphorus_ppm": null,
      "potassium_ppm": null,
      "rainfall_mm": null,
      "sunlight_detected": null,
      "vibration_detected": null,
      "vibration_rms": null
    },
    "actuator": {
      "pump_active": null,
      "mister_active": null
    },
    "edge_ai": {
      "last_scan_result": null,
      "confidence_pct": null
    },
    "data_sources": {
      "soil_moisture_pct": "NOT_AVAILABLE",
      "air_temperature_c": "NOT_AVAILABLE",
      "humidity_pct": "NOT_AVAILABLE"
    },
    "validation_errors": [],
    "warnings": [
      "Device has not sent telemetry in 80 hours. Check device power, WiFi, and MQTT connectivity."
    ],
    "packet_hash": null,
    "data_source": "UNAVAILABLE"
  },
  "timestamp": "2026-09-17T13:20:57Z"
}
```

### Example: Partial Data with Warnings

```json
{
  "error": false,
  "telemetry": {
    "status": "PARTIAL_DATA",
    "device_id": "ESP32_NODE_01",
    "received_at": "2026-09-17T13:15:00Z",
    "age_seconds": 297,
    "data_quality": {
      "status": "STALE",
      "age_seconds": 297,
      "threshold_exceeded": false,
      "reason": "Data received 5 minutes ago. Acceptable but monitor for device issues."
    },
    "telemetry": {
      "soil_moisture_pct": 42.7,
      "air_temperature_c": 29.4,
      "humidity_pct": null,
      "ph": null,
      "nitrogen_ppm": null,
      "phosphorus_ppm": null,
      "potassium_ppm": null,
      "rainfall_mm": null
    },
    "actuator": {
      "pump_active": false,
      "mister_active": null
    },
    "data_sources": {
      "soil_moisture_pct": "ESP32_MQTT",
      "air_temperature_c": "ESP32_MQTT",
      "humidity_pct": "NOT_AVAILABLE",
      "ph": "NOT_AVAILABLE"
    },
    "validation_errors": [],
    "warnings": [
      "DHT22 sensor (humidity) returned invalid reading. Device may need restart."
    ],
    "packet_hash": "b4f3e9d2c8a5f1e3a6d9c2e5b8a1d4g7",
    "data_source": "MQTT_EDGE"
  },
  "timestamp": "2026-09-17T13:20:57Z"
}
```

---

## SCHEMA 2: Vision AI Diagnosis Response (Task #4)

### Current Problem

Vision AI currently returns diagnosis even when required multimodal sensors are missing.

### Corrected Pipeline

```
IMAGE
  ↓
validate_leaf_image() [in vision_ai_model.py]
  ├─ Valid leaf image?
  │  ├─ NO → return { status: "INVALID_IMAGE", diagnosis: null }
  │  └─ YES → continue
  │
  ├─ Extract HOG features
  │
  ├─ Run SVM classifier
  │
  ├─ Check confidence threshold
  │  ├─ Confidence < 70%?
  │  │  └─ YES → return { status: "NO_RELIABLE_RESULT", diagnosis: null, confidence: X% }
  │  └─ NO → continue
  │
  ├─ Return vision-only diagnosis? (don't need multimodal)
  │  ├─ YES → return { status: "VISION_DIAGNOSIS", diagnosis: RESULT, mode: "image_only" }
  │  └─ NO → check if caller requests multimodal → continue
  │
  MULTIMODAL FUSION (only if caller explicitly requests AND sensors available)
  │
  ├─ Check: soil_moisture exists AND real (not synthetic)?
  │  ├─ NO → return { status: "INSUFFICIENT_SENSORS", required: ["soil_moisture", "temp", "ec"], missing: ["soil_moisture"], diagnosis: null }
  │  └─ YES → continue
  │
  ├─ Check: temperature exists AND real?
  │  ├─ NO → return { status: "INSUFFICIENT_SENSORS", missing: ["temperature"], diagnosis: null }
  │  └─ YES → continue
  │
  ├─ Check: EC salinity exists AND real?
  │  ├─ NO → return { status: "INSUFFICIENT_SENSORS", missing: ["ec_salinity"], diagnosis: null }
  │  └─ YES → continue
  │
  ├─ Perform multimodal fusion
  │
  └─ Return { status: "MULTIMODAL_DIAGNOSIS", diagnosis: RESULT, mode: "image+sensors" }
```

### Schema

```python
# File: mlbackend/schemas.py (ADD TO FILE)

class VisionDiagnosisRequest(BaseModel):
    """Request to vision AI for diagnosis"""
    image_bytes: bytes  # Raw image data
    include_multimodal: bool = False  # Request sensor fusion?
    sensor_data: Optional[CanonicalTelemetry] = None  # Provide sensor context
    language: str = "en"

class VisionDiagnosis(BaseModel):
    """Vision AI result"""
    status: Literal[
        "VISION_DIAGNOSIS",           # Image-only diagnosis successful
        "MULTIMODAL_DIAGNOSIS",        # Image + sensor fusion successful
        "INVALID_IMAGE",               # Not a valid crop/leaf image
        "NO_RELIABLE_RESULT",          # Image valid but confidence too low
        "INSUFFICIENT_SENSORS",        # Requested multimodal but sensors missing
        "MODEL_UNAVAILABLE",           # Model not deployed
        "ERROR"
    ]
    
    diagnosis: Optional[str] = None  # e.g., "Powdery Mildew", "Healthy Leaf"
    confidence_pct: Optional[float] = None  # 0-100, null if not computed
    
    # Sensor info
    mode: Literal["image_only", "image+sensors"] = "image_only"
    required_sensors: list[str] = []  # What multimodal needs
    missing_sensors: list[str] = []   # What was actually missing
    
    # Multimodal context (only populated if mode == "image+sensors")
    sensor_context: Optional[Dict[str, Any]] = None
    
    # Remediation
    action: Optional[str] = None  # Recommended farmer action
    warning: Optional[str] = None  # Experimental status warning
    
    # Audit
    model_version: Optional[str] = None
    image_quality: Optional[Dict[str, Any]] = None  # Resolution, variance, etc.
    timestamp: str = datetime.utcnow().isoformat()

```

### Example: Valid Image, No Sensors Requested

```json
{
  "status": "VISION_DIAGNOSIS",
  "diagnosis": "Early Blight (Alternaria)",
  "confidence_pct": 87.3,
  "mode": "image_only",
  "required_sensors": [],
  "missing_sensors": [],
  "action": "Apply Mancozeb fungicide @ 2.5 g/L every 5 days starting now.",
  "warning": "Experimental model; confirm with agronomist before field application.",
  "model_version": "agrisaathi_hog_svm_v2.1",
  "image_quality": {
    "resolution": "640x480",
    "variance": 127.3,
    "format": "JPEG"
  },
  "timestamp": "2026-09-17T13:20:15Z"
}
```

### Example: Valid Image, Multimodal Requested BUT Soil Moisture Missing

```json
{
  "status": "INSUFFICIENT_SENSORS",
  "diagnosis": null,
  "confidence_pct": null,
  "mode": "image+sensors",
  "required_sensors": ["soil_moisture", "air_temperature", "ec_salinity"],
  "missing_sensors": ["soil_moisture"],
  "action": "Provide soil moisture measurement from real sensor (not fabricated default) for accurate multimodal diagnosis.",
  "warning": "Cannot perform multimodal fusion without complete sensor data. Image-only diagnosis available instead.",
  "model_version": "agrisaathi_hog_svm_v2.1",
  "image_quality": {
    "resolution": "640x480",
    "variance": 127.3,
    "format": "JPEG"
  },
  "timestamp": "2026-09-17T13:20:15Z"
}
```

---

## SCHEMA 3: Device Lifecycle States (Task #5)

### State Diagram

```
┌──────────┐
│REGISTERED│ ← Device created via /api/device-register
└─────┬────┘
      │ First telemetry arrives
      ▼
┌──────────┐
│  ONLINE  │ ← Telemetry age ≤ 10 minutes
└─────┬────┘
      │ (if age > 10 min and ≤ 6 hours)
      ▼
┌──────────┐
│  STALE   │ ← Telemetry age > 6 hours OR sensor validation errors
└─────┬────┘
      │ (if age > 24 hours OR no heartbeat)
      ▼
┌──────────┐
│  OFFLINE │ ← No telemetry for > 24 hours
└──────────┘
```

### Schema

```python
# File: mlbackend/schemas.py (ADD TO FILE)

from enum import Enum

class DeviceState(str, Enum):
    REGISTERED = "registered"   # Device created, no telemetry yet
    ONLINE = "online"           # Telemetry age ≤ 10 min, all sensors OK
    STALE = "stale"             # Telemetry age > 10 min, still receiving data
    OFFLINE = "offline"         # Telemetry age > 24 hours, no recent activity
    ERROR = "error"             # Device sent telemetry but validation failed

class DeviceRegistrationPayload(BaseModel):
    """What frontend sends when registering a device"""
    device_id: str
    expected_sensors: list[str] = [
        "soil_moisture",
        "air_temperature",
        "humidity"
    ]
    farm_id: Optional[str] = None
    zone_id: Optional[str] = None

class DeviceStatus(BaseModel):
    """Device status response"""
    device_id: str
    state: DeviceState
    
    # Lifecycle
    registered_at: str  # When device was created in system
    first_telemetry_received_at: Optional[str] = None
    last_telemetry_received_at: Optional[str] = None
    last_telemetry_age_seconds: Optional[int] = None
    
    # Hardware Info (only populated after first telemetry)
    firmware_version: Optional[str] = None  # FROM TELEMETRY, not hardcoded
    battery_pct: Optional[float] = None     # FROM TELEMETRY, not hardcoded
    signal_rssi_dbm: Optional[int] = None   # FROM TELEMETRY, not hardcoded
    
    # Expected vs Actual
    expected_sensors: list[str]
    available_sensors: list[str]  # Sensors that have reported values
    unavailable_sensors: list[str]  # Sensors expected but never reported
    
    # Health
    telemetry_count: int = 0  # Total packets received
    validation_errors_last_24h: list[str] = []
    
    # Metadata Sources
    metadata_provenance: Dict[str, str] = {
        "firmware_version": "TELEMETRY" if firmware_version else "NOT_AVAILABLE",
        "battery_pct": "TELEMETRY" if battery_pct else "NOT_AVAILABLE",
        "signal_rssi_dbm": "TELEMETRY" if signal_rssi_dbm else "NOT_AVAILABLE",
    }

```

### Example: Newly Registered Device (No Telemetry Yet)

```json
{
  "device_id": "ESP32_NODE_01",
  "state": "registered",
  "registered_at": "2026-09-17T10:00:00Z",
  "first_telemetry_received_at": null,
  "last_telemetry_received_at": null,
  "last_telemetry_age_seconds": null,
  "firmware_version": null,
  "battery_pct": null,
  "signal_rssi_dbm": null,
  "expected_sensors": ["soil_moisture", "air_temperature", "humidity"],
  "available_sensors": [],
  "unavailable_sensors": ["soil_moisture", "air_temperature", "humidity"],
  "telemetry_count": 0,
  "validation_errors_last_24h": [],
  "metadata_provenance": {
    "firmware_version": "NOT_AVAILABLE",
    "battery_pct": "NOT_AVAILABLE",
    "signal_rssi_dbm": "NOT_AVAILABLE"
  }
}
```

### Example: Device ONLINE with Full Data

```json
{
  "device_id": "ESP32_NODE_01",
  "state": "online",
  "registered_at": "2026-09-17T10:00:00Z",
  "first_telemetry_received_at": "2026-09-17T10:15:33Z",
  "last_telemetry_received_at": "2026-09-17T13:20:15Z",
  "last_telemetry_age_seconds": 42,
  "firmware_version": "2.1.0",
  "battery_pct": 87,
  "signal_rssi_dbm": -58,
  "expected_sensors": ["soil_moisture", "air_temperature", "humidity"],
  "available_sensors": ["soil_moisture", "air_temperature", "humidity"],
  "unavailable_sensors": [],
  "telemetry_count": 197,
  "validation_errors_last_24h": [],
  "metadata_provenance": {
    "firmware_version": "TELEMETRY",
    "battery_pct": "TELEMETRY",
    "signal_rssi_dbm": "TELEMETRY"
  }
}
```

### Example: Device OFFLINE (No Data for 80 Hours)

```json
{
  "device_id": "ESP32_NODE_01",
  "state": "offline",
  "registered_at": "2026-09-10T10:00:00Z",
  "first_telemetry_received_at": "2026-09-10T10:15:33Z",
  "last_telemetry_received_at": "2026-09-14T09:15:00Z",
  "last_telemetry_age_seconds": 289200,
  "firmware_version": "2.1.0",
  "battery_pct": 45,
  "signal_rssi_dbm": -72,
  "expected_sensors": ["soil_moisture", "air_temperature", "humidity"],
  "available_sensors": ["soil_moisture", "air_temperature", "humidity"],
  "unavailable_sensors": [],
  "telemetry_count": 4817,
  "validation_errors_last_24h": [],
  "metadata_provenance": {
    "firmware_version": "TELEMETRY",
    "battery_pct": "TELEMETRY",
    "signal_rssi_dbm": "TELEMETRY"
  },
  "warning": "Device has not sent telemetry in 80 hours. Check power, WiFi, and MQTT connectivity."
}
```

---

## SCHEMA 4: AI Prediction Response (Unified Format)

Every AI module (crop recommendation, irrigation, pest, disease) should return this format:

```python
# File: mlbackend/schemas.py (ADD TO FILE)

class AIPredictionResponse(BaseModel):
    """Unified response for all AI predictions"""
    status: Literal[
        "OK",                    # Prediction made successfully
        "INSUFFICIENT_DATA",     # Not enough real sensor data
        "OUT_OF_DISTRIBUTION",   # Input is unusual vs training data
        "ERROR",                 # Model or computation error
        "MODEL_UNAVAILABLE"      # Model not deployed
    ]
    
    prediction: Optional[Any] = None  # The actual prediction (crop name, risk score, etc.)
    confidence_pct: Optional[float] = None  # 0-100, null if not computed
    
    # Data Quality Transparency
    required_features: list[str] = []  # What features the model needs
    available_features: list[str] = []  # What we actually received (real data)
    missing_features: list[str] = []    # What was not available
    
    # Sensor Context
    sensor_data_quality: Optional[TelemetryDataQuality] = None
    sensor_data_age_seconds: Optional[int] = None
    sensor_data_source: Literal["MQTT", "API", "MANUAL", "UNAVAILABLE"] = "UNAVAILABLE"
    
    # Recommendations & Warnings
    recommendation: Optional[str] = None
    warnings: list[str] = []
    caveats: list[str] = []  # Important limitations
    
    # Model Info
    model_version: Optional[str] = None
    model_status: Literal["VERIFIED", "EXPERIMENTAL", "UNVERIFIED"] = "EXPERIMENTAL"
    calibration_status: Literal["CALIBRATED", "UNCALIBRATED"] = "UNCALIBRATED"
    
    # Audit
    timestamp: str = datetime.utcnow().isoformat()
    request_id: Optional[str] = None

```

### Example: Crop Recommendation with INSUFFICIENT_DATA

```json
{
  "status": "INSUFFICIENT_DATA",
  "prediction": null,
  "confidence_pct": null,
  "required_features": ["nitrogen", "phosphorus", "potassium", "temperature", "humidity", "ph", "rainfall"],
  "available_features": ["temperature", "humidity", "rainfall"],
  "missing_features": ["nitrogen", "phosphorus", "potassium", "ph"],
  "sensor_data_quality": {
    "status": "LIVE",
    "age_seconds": 42,
    "threshold_exceeded": false
  },
  "sensor_data_age_seconds": 42,
  "sensor_data_source": "MQTT",
  "recommendation": "Conduct a soil test to determine N, P, K, and pH levels. Upload results to receive crop recommendation.",
  "warnings": [
    "Crop recommendation model requires soil nutrient analysis (NPK) and pH measurement."
  ],
  "caveats": [
    "Without soil test data, no reliable crop recommendation can be provided.",
    "Visit local agricultural extension office for soil testing service."
  ],
  "model_version": "rf_crop_recommendation_v1.0",
  "model_status": "VERIFIED",
  "calibration_status": "CALIBRATED",
  "timestamp": "2026-09-17T13:20:15Z",
  "request_id": "crop_req_a2d8c1e4"
}
```

### Example: Irrigation Recommendation with LIVE Data

```json
{
  "status": "OK",
  "prediction": {
    "irrigation_needed": true,
    "target_water_mm": 32.5
  },
  "confidence_pct": 92.1,
  "required_features": ["soil_moisture", "temperature", "humidity", "rainfall_forecast"],
  "available_features": ["soil_moisture", "temperature", "humidity", "rainfall_forecast"],
  "missing_features": [],
  "sensor_data_quality": {
    "status": "LIVE",
    "age_seconds": 42,
    "threshold_exceeded": false
  },
  "sensor_data_age_seconds": 42,
  "sensor_data_source": "MQTT",
  "recommendation": "Apply 30-35mm of irrigation water. Soil moisture is 18% (below 25% threshold). Weather forecast shows no rain expected for 48 hours. Drip irrigation recommended for efficiency.",
  "warnings": [],
  "caveats": [
    "Recommendation is based on current sensor data and weather forecast.",
    "Actual irrigation duration depends on water delivery rate and soil infiltration.",
    "Monitor soil moisture 2 hours after irrigation to confirm effectiveness."
  ],
  "model_version": "penman_monteith_et0_v2.1",
  "model_status": "VERIFIED",
  "calibration_status": "CALIBRATED",
  "timestamp": "2026-09-17T13:20:15Z",
  "request_id": "irrig_req_b3e9d2c5"
}
```

---

## Summary of Schema Changes

| Endpoint | Current | New Schema | Impact |
|----------|---------|-----------|--------|
| `/api/telemetry/latest` | Varies | CanonicalTelemetry | Single source of truth |
| `/api/sensors/[ip]` | No freshness | CanonicalTelemetry | Age tracking |
| `/api/device/{id}` | Hardcoded battery% | DeviceStatus | Real metadata only |
| `/api/vision/diagnose` | No sensor validation | VisionDiagnosis | Multimodal pipeline with guards |
| `/api/recommend/crop` | No data quality | AIPredictionResponse | Transparent insufficient data |
| `/api/irrigation/assess` | No data quality | AIPredictionResponse | Transparent confidence + caveats |
| All AI endpoints | Varies | AIPredictionResponse | Consistent format across modules |

---

**These schemas are the contract foundation. Implementation order in next document.**

