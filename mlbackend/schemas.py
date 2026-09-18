"""
AgriSaathi Canonical Response Schemas

This module defines unified Pydantic models for all API responses, ensuring:
1. No synthetic defaults (null preservation)
2. Explicit freshness tracking (age_seconds, data_quality status)
3. Consistent data quality metadata across all endpoints
4. Device lifecycle state management
5. Vision AI trustworthiness validation

Key principle: REAL DATA OR DATA_UNAVAILABLE, never fabricated values.

Created: Phase 0 of architecture remediation
References: CANONICAL_SCHEMAS.md, CROSS_FILE_CONTRACT_VIOLATIONS.md
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# DATA QUALITY TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

class DataQualityStatus(str, Enum):
    """Freshness and reliability status of telemetry data."""
    LIVE = "LIVE"  # ≤10 minutes old (real-time)
    STALE = "STALE"  # >10 min but ≤60 min old (caution: may not reflect current state)
    OFFLINE = "OFFLINE"  # >60 min old (device unreachable)
    UNAVAILABLE = "UNAVAILABLE"  # No data received yet


class TelemetryDataQuality(BaseModel):
    """Metadata about the freshness and reliability of telemetry data."""
    status: DataQualityStatus = Field(
        description="LIVE (≤10m) | STALE (>10m, ≤6h) | OFFLINE (>6h) | UNAVAILABLE"
    )
    age_seconds: Optional[float] = Field(
        None, 
        description="Seconds since telemetry was received at backend. None if never received."
    )
    received_at: Optional[datetime] = Field(
        None,
        description="ISO 8601 timestamp when backend received the packet. None if never received."
    )
    reason: Optional[str] = Field(
        None,
        description="Human-readable reason for status (e.g., 'Device offline for 14 hours')"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL TELEMETRY (Schema 1)
# ═══════════════════════════════════════════════════════════════════════════════

class SensorReading(BaseModel):
    """Single sensor reading with preservation of null values."""
    value: Optional[float] = Field(None, description="Measured value or None if unavailable")
    unit: str = Field(description="Physical unit (%, °C, lux, etc.)")
    data_source: str = Field(description="Origin (MQTT_VALIDATED, SIMULATOR, etc.)")
    confidence: Optional[float] = Field(
        None, 
        description="Reading confidence (0-1) or None if unavailable"
    )


class CanonicalTelemetry(BaseModel):
    """
    Unified telemetry response with explicit freshness, no synthetic defaults.
    
    Key principles:
    - Null values preserved (not replaced with defaults)
    - All fields optional (may be None if sensor unavailable)
    - age_seconds included (caller can compute staleness)
    - data_quality explicit (LIVE/STALE/OFFLINE/UNAVAILABLE)
    - data_sources tracked (where each value came from)
    """
    device_id: str = Field(description="Hardware identifier")
    
    # ─ Timestamps ─
    received_at: Optional[datetime] = Field(None, description="Backend reception time (ISO 8601)")
    device_timestamp: Optional[datetime] = Field(None, description="Device-reported timestamp")
    age_seconds: Optional[float] = Field(None, description="Seconds since received_at")
    
    # ─ Telemetry Readings (all optional, no synthetic defaults) ─
    soil_moisture_pct: Optional[float] = Field(None, description="Soil moisture (0-100%)")
    soil_raw_adc: Optional[int] = Field(None, description="Raw ADC value from sensor")
    temperature_c: Optional[float] = Field(None, description="Air temperature (Celsius)")
    humidity_pct: Optional[float] = Field(None, description="Relative humidity (0-100%)")
    sunlight_detected: Optional[bool] = Field(None, description="Whether sunlight present")
    vibration_rms: Optional[float] = Field(None, description="Vibration RMS value")
    
    # ─ Soil Properties (from optional soil sensor) ─
    nitrogen: Optional[float] = Field(None, description="Soil nitrogen (mg/kg)")
    phosphorus: Optional[float] = Field(None, description="Soil phosphorus (mg/kg)")
    potassium: Optional[float] = Field(None, description="Soil potassium (mg/kg)")
    soil_ec_salinity: Optional[float] = Field(None, description="Soil EC/salinity (dS/m)")
    soil_ph: Optional[float] = Field(None, description="Soil pH")
    
    # ─ Actuation State ─
    pump_active: Optional[bool] = Field(
        None, 
        description="Pump state (True/False/None if unknown)"
    )
    
    # ─ Edge AI Results ─
    edge_ai_result: Optional[str] = Field(None, description="Vision/ML edge model output")
    edge_ai_confidence_pct: Optional[float] = Field(
        None, 
        description="Edge AI confidence (0-100)"
    )
    
    # ─ Data Quality ─
    data_quality: TelemetryDataQuality = Field(
        description="Freshness and reliability metadata"
    )
    data_sources: Dict[str, str] = Field(
        default_factory=dict,
        description="Traceability: {field_name: source_system}"
    )
    
    # ─ Validation & Warnings ─
    validation_errors: List[str] = Field(
        default_factory=list,
        description="Warnings (e.g., 'Soil sensor not connected', 'ADC reading out of range')"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "ESP32_NODE_01",
                "received_at": "2026-09-17T14:30:00Z",
                "device_timestamp": "2026-09-17T14:29:55Z",
                "age_seconds": 5.2,
                "soil_moisture_pct": 42.5,
                "temperature_c": 28.3,
                "humidity_pct": 65.0,
                "nitrogen": 120.5,
                "phosphorus": 35.0,
                "potassium": 180.0,
                "pump_active": True,
                "data_quality": {
                    "status": "LIVE",
                    "age_seconds": 5.2,
                    "received_at": "2026-09-17T14:30:00Z",
                    "reason": "Data fresh (≤10 minutes)"
                },
                "data_sources": {
                    "soil_moisture_pct": "MQTT_VALIDATED",
                    "temperature_c": "MQTT_VALIDATED",
                    "humidity_pct": "MQTT_VALIDATED",
                    "nitrogen": "MQTT_VALIDATED"
                },
                "validation_errors": []
            }
        }


class TelemetryResponse(BaseModel):
    """Wrapper for API responses."""
    success: bool
    data: Optional[CanonicalTelemetry] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE LIFECYCLE STATES (Schema 3)
# ═══════════════════════════════════════════════════════════════════════════════

class DeviceState(str, Enum):
    """Device lifecycle states computed from telemetry age."""
    REGISTERED = "REGISTERED"  # Device created in system, no telemetry received yet
    ONLINE = "ONLINE"  # Telemetry ≤10 minutes old (actively communicating)
    STALE = "STALE"  # Telemetry >10 min, ≤60 min old (may have disconnected)
    OFFLINE = "OFFLINE"  # Telemetry >60 min old (device unreachable)
    ERROR = "ERROR"  # Device error state (reported by device)


class DeviceStatus(BaseModel):
    """
    Device registration and state.
    
    Key principle: Metadata sourced from REAL TELEMETRY, not fabricated.
    - battery_pct, signal_rssi_dbm, firmware_version = null until first telemetry
    - state auto-computed from telemetry age
    """
    device_id: str = Field(description="Hardware identifier")
    state: DeviceState = Field(description="Device lifecycle state")
    registered_at: datetime = Field(description="Registration timestamp (ISO 8601)")
    last_telemetry_at: Optional[datetime] = Field(
        None, 
        description="Last telemetry receipt time (None if never received)"
    )
    age_seconds: Optional[float] = Field(
        None, 
        description="Seconds since last telemetry (None if never received)"
    )
    
    # ─ Device Metadata (from real telemetry only) ─
    battery_pct: Optional[float] = Field(
        None,
        description="Battery percentage (None if not reported by device)"
    )
    signal_rssi_dbm: Optional[int] = Field(
        None,
        description="Signal strength in dBm (None if not reported)"
    )
    firmware_version: Optional[str] = Field(
        None,
        description="Firmware version (None if not reported)"
    )
    
    # ─ Error Handling ─
    error_state: Optional[str] = Field(
        None,
        description="Error message if device in ERROR state"
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "example_name": "Newly Registered (No Telemetry)",
                    "value": {
                        "device_id": "ESP32_NODE_01",
                        "state": "REGISTERED",
                        "registered_at": "2026-09-17T10:00:00Z",
                        "last_telemetry_at": None,
                        "age_seconds": None,
                        "battery_pct": None,
                        "signal_rssi_dbm": None,
                        "firmware_version": None
                    }
                },
                {
                    "example_name": "Device Online with Telemetry",
                    "value": {
                        "device_id": "ESP32_NODE_01",
                        "state": "ONLINE",
                        "registered_at": "2026-09-01T00:00:00Z",
                        "last_telemetry_at": "2026-09-17T14:30:00Z",
                        "age_seconds": 5.2,
                        "battery_pct": 87.0,
                        "signal_rssi_dbm": -62,
                        "firmware_version": "v2.4.1"
                    }
                },
                {
                    "example_name": "Device Offline (80 hours)",
                    "value": {
                        "device_id": "ESP32_NODE_01",
                        "state": "OFFLINE",
                        "registered_at": "2026-09-01T00:00:00Z",
                        "last_telemetry_at": "2026-09-14T10:00:00Z",
                        "age_seconds": 288000,
                        "battery_pct": 12.0,
                        "signal_rssi_dbm": None,
                        "firmware_version": "v2.4.1"
                    }
                }
            ]
        }


# ═══════════════════════════════════════════════════════════════════════════════
# VISION AI DIAGNOSIS (Schema 2)
# ═══════════════════════════════════════════════════════════════════════════════

class VisionDiagnosisType(str, Enum):
    """Vision diagnosis confidence level."""
    IMAGE_ONLY = "IMAGE_ONLY"  # Image analysis alone (high confidence)
    MULTIMODAL = "MULTIMODAL"  # Image + sensor fusion (highest confidence)
    INSUFFICIENT_SENSORS = "INSUFFICIENT_SENSORS"  # Cannot do multimodal (low confidence)
    ERROR = "ERROR"  # Model error or invalid input


class VisionDiagnosis(BaseModel):
    """
    Vision AI diagnostic result with validation pipeline.
    
    Pipeline (REQUIRED ORDER):
    1. Image validation (format, size, content)
    2. SVM confidence check
    3. Sensor availability check (if multimodal requested)
    4. Multimodal fusion (only if step 3 passes)
    
    Key principle: Multimodal fusion only with REAL sensors, never synthetic defaults.
    """
    diagnosis_type: VisionDiagnosisType = Field(
        description="Image-only vs multimodal vs insufficient"
    )
    
    # ─ Image Analysis (always attempted) ─
    image_valid: bool = Field(description="Image format/size valid")
    svm_prediction: Optional[str] = Field(
        None, 
        description="SVM model output (e.g., 'Powdery Mildew', 'Healthy')"
    )
    svm_confidence: Optional[float] = Field(
        None,
        description="SVM confidence (0-1)"
    )
    
    # ─ Sensor Validation (before multimodal) ─
    sensors_required_for_multimodal: List[str] = Field(
        default_factory=list,
        description="Required sensors (e.g., ['soil_moisture', 'temperature', 'ec_salinity'])"
    )
    sensors_available: List[str] = Field(
        default_factory=list,
        description="Actually available and real (not synthetic)"
    )
    sensors_missing: List[str] = Field(
        default_factory=list,
        description="Required but unavailable"
    )
    
    # ─ Multimodal Results (only if all sensors real) ─
    multimodal_prediction: Optional[str] = Field(
        None,
        description="Combined image+sensor prediction"
    )
    multimodal_confidence: Optional[float] = Field(
        None,
        description="Combined confidence (0-1)"
    )
    
    # ─ Calibration & Confidence ─
    calibration_status: Optional[str] = Field(
        None,
        description="Model calibration info (e.g., 'calibrated_on_indian_crops')"
    )
    ood_detected: Optional[bool] = Field(
        None,
        description="Out-of-distribution sample detected (model may be unreliable)"
    )
    
    # ─ Metadata ─
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    device_id: Optional[str] = Field(None, description="Hardware identifier")
    telemetry_data_quality: Optional[TelemetryDataQuality] = Field(
        None,
        description="Quality of sensor data (if used in fusion)"
    )
    
    # ─ Audit Trail ─
    validation_errors: List[str] = Field(
        default_factory=list,
        description="Warnings (e.g., 'Image blurry', 'Soil sensor disconnected')"
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "example_name": "Valid Image, No Sensors",
                    "value": {
                        "diagnosis_type": "IMAGE_ONLY",
                        "image_valid": True,
                        "svm_prediction": "Powdery Mildew",
                        "svm_confidence": 0.87,
                        "sensors_required_for_multimodal": [],
                        "sensors_available": [],
                        "sensors_missing": [],
                        "multimodal_prediction": None,
                        "multimodal_confidence": None,
                        "calibration_status": "calibrated_on_indian_crops_v2",
                        "ood_detected": False,
                        "timestamp": "2026-09-17T14:30:00Z",
                        "device_id": "ESP32_NODE_01",
                        "validation_errors": []
                    }
                },
                {
                    "example_name": "Image + Multimodal Requested, Soil Sensor Missing",
                    "value": {
                        "diagnosis_type": "INSUFFICIENT_SENSORS",
                        "image_valid": True,
                        "svm_prediction": "Powdery Mildew",
                        "svm_confidence": 0.87,
                        "sensors_required_for_multimodal": ["soil_moisture", "temperature", "ec_salinity"],
                        "sensors_available": ["temperature"],
                        "sensors_missing": ["soil_moisture", "ec_salinity"],
                        "multimodal_prediction": None,
                        "multimodal_confidence": None,
                        "calibration_status": "calibrated_on_indian_crops_v2",
                        "ood_detected": False,
                        "timestamp": "2026-09-17T14:30:00Z",
                        "device_id": "ESP32_NODE_01",
                        "telemetry_data_quality": {
                            "status": "LIVE",
                            "age_seconds": 5.2,
                            "received_at": "2026-09-17T14:30:00Z",
                            "reason": "Data fresh (≤10 minutes)"
                        },
                        "validation_errors": ["Soil sensor not connected; cannot perform multimodal fusion"]
                    }
                }
            ]
        }


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED AI PREDICTION RESPONSE (Schema 4)
# ═══════════════════════════════════════════════════════════════════════════════

class AIPredictionStatus(str, Enum):
    """Status of AI prediction."""
    SUCCESS = "SUCCESS"  # Prediction successful
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"  # Not enough real sensor data
    MODEL_ERROR = "MODEL_ERROR"  # Model failed to predict
    OUT_OF_DISTRIBUTION = "OUT_OF_DISTRIBUTION"  # Input outside training distribution
    CALIBRATION_REQUIRED = "CALIBRATION_REQUIRED"  # Model needs field validation


class AIPredictionResponse(BaseModel):
    """
    Unified response for ALL AI modules (crop, irrigation, pest, yield, advisory).
    
    Key principle: Transparency about data quality and model reliability.
    - Include required vs available features
    - Track which sensors were REAL vs unavailable
    - Report confidence with calibration context
    - Explain why predictions may be unreliable
    """
    model_name: str = Field(description="AI model identifier (e.g., 'crop_recommendation_v2')")
    status: AIPredictionStatus = Field(description="Prediction success/failure reason")
    
    # ─ Prediction Result ─
    prediction: Optional[str] = Field(
        None,
        description="Model output (e.g., 'Recommend N: 120, P: 35, K: 180')"
    )
    confidence: Optional[float] = Field(
        None,
        description="Prediction confidence (0-1), None if unavailable"
    )
    
    # ─ Feature Requirements ─
    required_features: List[str] = Field(
        default_factory=list,
        description="Features model needs (e.g., ['nitrogen', 'phosphorus', 'potassium', 'temperature', 'humidity', 'ph', 'rainfall'])"
    )
    available_features: List[str] = Field(
        default_factory=list,
        description="Features with real data"
    )
    missing_features: List[str] = Field(
        default_factory=list,
        description="Features not available (model falls back or reports INSUFFICIENT_DATA)"
    )
    
    # ─ Data Quality ─
    sensor_data_quality: Optional[TelemetryDataQuality] = Field(
        None,
        description="Quality of underlying sensor data"
    )
    features_synthetic: bool = Field(
        False,
        description="True if ANY required feature was fabricated (indicates unreliable prediction)"
    )
    
    # ─ Model Calibration ─
    model_status: Optional[str] = Field(
        None,
        description="Model status (e.g., 'production_calibrated', 'field_validation_pending')"
    )
    calibration_status: Optional[str] = Field(
        None,
        description="Calibration info (e.g., 'Trained on Indian crops only')"
    )
    ood_detected: Optional[bool] = Field(
        None,
        description="Out-of-distribution sample detected"
    )
    
    # ─ Metadata ─
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    device_id: Optional[str] = Field(None, description="Hardware identifier")
    
    # ─ Audit Trail ─
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-critical warnings (e.g., 'Humidity sensor stale')"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Critical errors preventing reliable prediction"
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "example_name": "Crop Recommendation with INSUFFICIENT_DATA",
                    "value": {
                        "model_name": "crop_recommendation_hybrid_v2",
                        "status": "INSUFFICIENT_DATA",
                        "prediction": None,
                        "confidence": None,
                        "required_features": ["nitrogen", "phosphorus", "potassium", "temperature", "humidity", "ph", "rainfall"],
                        "available_features": ["temperature", "humidity"],
                        "missing_features": ["nitrogen", "phosphorus", "potassium", "ph", "rainfall"],
                        "sensor_data_quality": {
                            "status": "STALE",
                            "age_seconds": 14400,
                            "received_at": "2026-09-17T10:30:00Z",
                            "reason": "Last telemetry 4 hours ago"
                        },
                        "features_synthetic": False,
                        "model_status": "production",
                        "calibration_status": "Hybrid model: full model for N/P/K farms, 3-feature model otherwise",
                        "ood_detected": False,
                        "timestamp": "2026-09-17T14:30:00Z",
                        "device_id": "ESP32_NODE_01",
                        "warnings": ["Nitrogen/Phosphorus/Potassium sensors not connected"],
                        "errors": ["Cannot recommend NPK without soil test data. Require real N/P/K readings or conduct soil test."]
                    }
                },
                {
                    "example_name": "Irrigation Recommendation with LIVE Data",
                    "value": {
                        "model_name": "irrigation_scheduling_v1",
                        "status": "SUCCESS",
                        "prediction": "Irrigate in 18 hours; apply 35mm to field",
                        "confidence": 0.78,
                        "required_features": ["temperature", "humidity", "rainfall"],
                        "available_features": ["temperature", "humidity", "rainfall"],
                        "missing_features": [],
                        "sensor_data_quality": {
                            "status": "LIVE",
                            "age_seconds": 3.5,
                            "received_at": "2026-09-17T14:30:00Z",
                            "reason": "Data fresh (≤10 minutes)"
                        },
                        "features_synthetic": False,
                        "model_status": "production_field_validated",
                        "calibration_status": "Trained and validated on Indian agricultural regions",
                        "ood_detected": False,
                        "timestamp": "2026-09-17T14:30:00Z",
                        "device_id": "ESP32_NODE_01",
                        "warnings": [],
                        "errors": []
                    }
                }
            ]
        }
