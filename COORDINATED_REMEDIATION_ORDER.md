# AgriSaathi — Coordinated Remediation Implementation Order

**Critical:** These phases must be executed in this exact order. Parallel work on unrelated phases is safe, but all phases in the same dependency chain must be sequential.

---

## Dependency Chain Analysis

```
Config ──→ MQTT ──→ DB ──→ Main.py ──→ Vision ──→ Frontend
Service     Service   Layer  API         AI       Components
(Tier 0)    (Tier 1)  (Tier 2) (Tier 3)  (Tier 4) (Tier 5)
```

Each tier depends on all previous tiers being complete.

---

## PHASE 0: Configuration & Schemas (Foundation)

**Duration:** 2 hours  
**Dependencies:** None (can start immediately)  
**Blocks:** All other phases

### Task 0.1: Create Canonical Schemas (2 hours)

**File:** `mlbackend/schemas.py` (NEW)

Create the Pydantic schema definitions:
- ✅ `TelemetryDataQuality` enum + class
- ✅ `SensorReading` class
- ✅ `CanonicalTelemetry` class
- ✅ `TelemetryResponse` wrapper
- ✅ `VisionDiagnosisRequest` class
- ✅ `VisionDiagnosis` class
- ✅ `DeviceState` enum
- ✅ `DeviceStatus` class
- ✅ `AIPredictionResponse` class

**No code changes yet—just schema definitions.**

**Checklist:**
- [ ] All classes have docstrings
- [ ] All Literal types are defined
- [ ] All optional fields marked with Optional
- [ ] No default values that hide missing data

**Exit Criteria:** All schemas compile, pass type checking

---

### Task 0.2: Update config.py with Freshness Thresholds (30 min)

**File:** `mlbackend/config.py`

Add to `Settings` class:

```python
# Telemetry Freshness Classification Thresholds (in seconds)
TELEMETRY_FRESHNESS = {
    "LIVE_THRESHOLD": 600,           # ≤ 10 minutes = LIVE
    "STALE_THRESHOLD": 21600,        # > 10 min, ≤ 6 hours = STALE
    "OFFLINE_THRESHOLD": 86400,      # > 6 hours = OFFLINE
}

# Device State Transitions
DEVICE_STATE = {
    "FIRST_TELEMETRY_RECEIVED": "online",      # On first packet
    "HEARTBEAT_REQUIRED_SECONDS": 600,         # Expect packet every 10 min
    "STALE_AFTER_SECONDS": 21600,              # 6 hours
    "OFFLINE_AFTER_SECONDS": 86400,            # 24 hours
}

# AI/Model Configuration
MODEL_CONFIDENCE = {
    "MINIMUM_VISION_CONFIDENCE_PCT": 70.0,
    "MINIMUM_CROP_MODEL_CONFIDENCE_PCT": 60.0,
}

# Synthetic Default Prevention
ALLOW_FALLBACK_DEFAULTS = False  # Set to False in production
```

**Exit Criteria:** Settings load without errors

---

## PHASE 1: MQTT Service & Freshness Tracking (Tier 1)

**Duration:** 3 hours  
**Dependencies:** Phase 0  
**Blocks:** Phase 2 (DB Layer)

### Task 1.1: Add Freshness Tracking to mqtt_service.py (1.5 hours)

**File:** `mlbackend/mqtt_service.py`

Update the `on_message` callback to track received_at timestamp:

```python
def handle_telemetry_message(self, raw_payload_str: str, topic_device_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Ingests telemetry with explicit timestamp tracking.
    """
    ok, record, errors = parse_and_validate_telemetry_payload(raw_payload_str)
    
    if not ok or not record:
        return {"status": "error", "errors": errors}
    
    device_id = record["device_id"]
    
    # Anti-spoofing check (existing code, keep)
    if topic_device_id and topic_device_id != "unknown" and topic_device_id != device_id:
        return {"status": "error", "errors": ["SPOOFING_DETECTED_TOPIC_MISMATCH"]}
    
    # ADD: Explicitly set server received timestamp (this is the authority)
    record["received_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record["received_at_unix"] = time.time()
    
    # Store in DB (existing code, keep)
    db_layer.store_telemetry_packet(record)
    
    # Mark device online with timestamp (UPDATE this)
    db_layer.update_device_lifecycle(
        device_id=device_id,
        status="online",
        last_seen_at=record["received_at"],
        is_online=True,
        capabilities_json=json.dumps(record.get("capabilities", {}))
    )
    
    return {"status": "success", "device_id": device_id, "errors": errors}
```

**Exit Criteria:** 
- [ ] received_at timestamp is set server-side
- [ ] Device marked as "online" on packet arrival
- [ ] MQTT tests pass

---

### Task 1.2: Update db_layer Lifecycle Tracking (1.5 hours)

**File:** `mlbackend/db_layer.py`

The `update_device_lifecycle()` method exists but needs refinement:

```python
def update_device_lifecycle(
    self,
    device_id: str,
    status: str,
    last_seen_at: str,
    is_online: bool = False,
    capabilities_json: str = "{}"
):
    """
    Updates device lifecycle state.
    status: "online", "stale", "offline", "error", "registered"
    """
    conn = sqlite3.connect(HYBRID_DB_PATH)
    c = conn.cursor()
    
    # Compute lifecycle state from freshness
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_unix = time.time()
    
    try:
        last_seen = datetime.fromisoformat(last_seen_at.replace("Z", "+00:00"))
        age_seconds = (datetime.now(timezone.utc) - last_seen).total_seconds()
    except:
        age_seconds = 0
    
    # Determine state based on age
    if age_seconds <= 600:  # 10 minutes
        computed_state = "online"
    elif age_seconds <= 21600:  # 6 hours
        computed_state = "stale"
    else:  # > 6 hours
        computed_state = "offline"
    
    # Only override if provided state conflicts with age
    if status == "online" and age_seconds > 21600:
        computed_state = "offline"  # Ignore claim, use age
    
    c.execute("""
        INSERT INTO device_lifecycle (
            device_id, status, last_seen_at, last_online_at, last_offline_at, 
            capabilities_json, age_seconds
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(device_id) DO UPDATE SET
            status = excluded.status,
            last_seen_at = excluded.last_seen_at,
            last_online_at = excluded.last_online_at,
            last_offline_at = excluded.last_offline_at,
            capabilities_json = CASE WHEN excluded.capabilities_json != '{}' THEN excluded.capabilities_json ELSE device_lifecycle.capabilities_json END,
            age_seconds = excluded.age_seconds
    """, (
        device_id,
        computed_state,  # Use computed state, not provided status
        last_seen_at,
        last_seen_at if is_online else None,
        last_seen_at if not is_online else None,
        capabilities_json,
        age_seconds
    ))
    
    conn.commit()
    conn.close()
```

**Exit Criteria:**
- [ ] Device state computed from age, not claimed
- [ ] Tests verify state transitions
- [ ] DB records age_seconds for all devices

---

## PHASE 2: Database Layer Response Schema (Tier 2)

**Duration:** 2 hours  
**Dependencies:** Phase 1  
**Blocks:** Phase 3 (main.py)

### Task 2.1: Update get_latest_telemetry() Return Format (1 hour)

**File:** `mlbackend/db_layer.py`

Add new method that returns canonical schema:

```python
def get_latest_telemetry_canonical(
    self,
    device_id: str = "ESP32_NODE_01"
) -> Dict[str, Any]:
    """
    Returns latest telemetry with freshness metadata.
    MUST NOT include synthetic defaults.
    """
    import time
    from mlbackend.config import settings
    
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT * FROM canonical_telemetry
        WHERE device_id = ?
        ORDER BY id DESC LIMIT 1
    """, (device_id,))
    
    row = c.fetchone()
    conn.close()
    
    if not row:
        return {
            "status": "INSUFFICIENT_DATA",
            "device_id": device_id,
            "data_quality": {
                "status": "UNAVAILABLE",
                "age_seconds": None,
                "reason": "No telemetry received yet."
            },
            "telemetry": {},
            "data_sources": {}
        }
    
    # Compute age
    received_dt = datetime.fromisoformat(row["received_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    age_seconds = int((now - received_dt).total_seconds())
    
    # Determine quality status
    thresholds = settings.TELEMETRY_FRESHNESS
    if age_seconds <= thresholds["LIVE_THRESHOLD"]:
        quality_status = "LIVE"
    elif age_seconds <= thresholds["STALE_THRESHOLD"]:
        quality_status = "STALE"
    else:
        quality_status = "OFFLINE"
    
    # Build canonical response
    return {
        "status": "OK" if quality_status in ("LIVE", "STALE") else "INSUFFICIENT_DATA",
        "device_id": device_id,
        "received_at": row["received_at"],
        "age_seconds": age_seconds,
        "data_quality": {
            "status": quality_status,
            "age_seconds": age_seconds,
            "threshold_exceeded": quality_status == "OFFLINE"
        },
        "telemetry": {
            "soil_moisture_pct": row["soil_moisture_pct"],
            "soil_temperature_c": row["soil_temperature_c"] if hasattr(row, "soil_temperature_c") else None,
            "air_temperature_c": row["temperature_c"],
            "humidity_pct": row["humidity_pct"],
            "ph": row["ph"] if hasattr(row, "ph") else None,
            "ec_ms_cm": row["ec"] if hasattr(row, "ec") else None,
            "nitrogen_ppm": row["nitrogen"],
            "phosphorus_ppm": row["phosphorus"],
            "potassium_ppm": row["potassium"],
            "rainfall_mm": None,  # Not from sensor, from API
        },
        "actuator": {
            "pump_active": bool(row["pump_active"]) if row["pump_active"] is not None else None,
        },
        "data_sources": {
            "soil_moisture_pct": "ESP32_MQTT" if row["soil_moisture_pct"] is not None else "NOT_AVAILABLE",
            "air_temperature_c": "ESP32_MQTT" if row["temperature_c"] is not None else "NOT_AVAILABLE",
            "humidity_pct": "ESP32_MQTT" if row["humidity_pct"] is not None else "NOT_AVAILABLE",
            "nitrogen_ppm": "NOT_AVAILABLE",
            "phosphorus_ppm": "NOT_AVAILABLE",
            "potassium_ppm": "NOT_AVAILABLE",
            "ph": "NOT_AVAILABLE",
            "rainfall_mm": "NOT_AVAILABLE",
        },
        "data_source": "MQTT_EDGE",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

**Exit Criteria:**
- [ ] Method returns CanonicalTelemetry schema structure
- [ ] No synthetic defaults are injected
- [ ] age_seconds is correctly computed
- [ ] data_quality status is set correctly

---

### Task 2.2: Add helper method to compute freshness (1 hour)

**File:** `mlbackend/db_layer.py`

```python
@staticmethod
def get_data_quality(age_seconds: int, thresholds: Dict[str, int]) -> Dict[str, Any]:
    """
    Classifies data quality based on age.
    
    thresholds should be from settings.TELEMETRY_FRESHNESS:
    {
        "LIVE_THRESHOLD": 600,
        "STALE_THRESHOLD": 21600,
        "OFFLINE_THRESHOLD": 86400
    }
    """
    if age_seconds <= thresholds.get("LIVE_THRESHOLD", 600):
        return {
            "status": "LIVE",
            "age_seconds": age_seconds,
            "threshold_exceeded": False,
            "reason": f"Data received {age_seconds}s ago (< 10 min threshold)"
        }
    elif age_seconds <= thresholds.get("STALE_THRESHOLD", 21600):
        return {
            "status": "STALE",
            "age_seconds": age_seconds,
            "threshold_exceeded": False,
            "reason": f"Data received {age_seconds // 60} minutes ago (> 10 min, < 6 hour threshold)"
        }
    else:
        return {
            "status": "OFFLINE",
            "age_seconds": age_seconds,
            "threshold_exceeded": True,
            "reason": f"Data received {age_seconds // 3600} hours ago (> 6 hour threshold). Device likely offline."
        }
```

**Exit Criteria:**
- [ ] Helper method exists and is tested
- [ ] Used by get_latest_telemetry_canonical()

---

## PHASE 3: Main.py API Endpoints (Tier 3)

**Duration:** 4 hours  
**Dependencies:** Phase 2  
**Blocks:** Phase 4 (Vision AI)

### Task 3.1: Create /api/telemetry/latest endpoint (1 hour)

**File:** `mlbackend/main.py`

Remove all HTTP direct sensor paths. Create unified endpoint:

```python
@app.get("/api/telemetry/latest")
def get_latest_telemetry(device_id: str = "ESP32_NODE_01"):
    """
    Returns latest canonical telemetry.
    Single source of truth for all consumers.
    No synthetic defaults.
    """
    from mlbackend.schemas import TelemetryResponse
    
    canonical_data = db_layer.get_latest_telemetry_canonical(device_id=device_id)
    
    return TelemetryResponse(
        error=False,
        telemetry=canonical_data,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
```

**Exit Criteria:**
- [ ] Endpoint returns CanonicalTelemetry schema
- [ ] No fallback defaults
- [ ] age_seconds is computed server-side
- [ ] Tests verify null preservation

---

### Task 3.2: Fix /api/crop-risk endpoint (1 hour)

**File:** `mlbackend/main.py`

Remove synthetic defaults from weather extraction:

```python
# BEFORE (WRONG):
temp = weather.get("temp") or 25
rain = weather.get("rainfall_last_3h") or 0

# AFTER (CORRECT):
temp = weather.get("temp")
rain = weather.get("rainfall_last_3h")

if temp is None or rain is None:
    return {
        "risk_score": None,
        "risk_level": "DATA_UNAVAILABLE",
        "weather_status": "INCOMPLETE",
        "reason": "Weather data incomplete. Cannot compute risk score.",
        "provenance": "UNAVAILABLE"
    }
```

**Exit Criteria:**
- [ ] No `or` operators for sensor/weather data
- [ ] Returns INSUFFICIENT_DATA when needed
- [ ] Tests verify correct behavior

---

### Task 3.3: Fix vision diagnosis endpoint (1 hour)

**File:** `mlbackend/main.py`

Remove synthetic defaults before multimodal fusion:

```python
# BEFORE (WRONG):
fusion_result = evaluate_multimodal_fusion(
    soil_moisture=payload.soil_moisture or 16.0,  # SYNTHETIC
    temp_c=payload.temp_c or 35.0,               # SYNTHETIC
    ec_salinity=payload.ec_salinity or 1.2       # SYNTHETIC
)

# AFTER (CORRECT):
if payload.soil_moisture is None:
    return {
        "status": "INSUFFICIENT_SENSORS",
        "diagnosis": None,
        "required_sensors": ["soil_moisture", "temperature", "ec_salinity"],
        "missing_sensors": ["soil_moisture"],
        "message": "Cannot perform multimodal diagnosis without soil moisture measurement."
    }

if payload.temp_c is None:
    return {
        "status": "INSUFFICIENT_SENSORS",
        "diagnosis": None,
        "required_sensors": ["soil_moisture", "temperature", "ec_salinity"],
        "missing_sensors": ["temperature"],
        "message": "Cannot perform multimodal diagnosis without temperature measurement."
    }

# All checks passed, perform fusion
fusion_result = evaluate_multimodal_fusion(
    soil_moisture=payload.soil_moisture,  # REAL
    temp_c=payload.temp_c,                # REAL
    ec_salinity=payload.ec_salinity       # REAL (or None if not available)
)
```

**Exit Criteria:**
- [ ] No synthetic defaults for sensor data
- [ ] Multimodal fusion only with real data
- [ ] Returns INSUFFICIENT_SENSORS when needed

---

### Task 3.4: Update all AI endpoint responses to AIPredictionResponse schema (1 hour)

**Files:** All endpoints calling:
- `recommend_crop()`
- `assess_irrigation_needs()`
- `analyze_soil_health()`
- `predict_yield()`
- `analyze_pest_risk()`
- `recommend_rotation()`

Pattern:

```python
# BEFORE:
return {
    "recommended_crop": prediction,
    "confidence": 95.2
}

# AFTER:
return AIPredictionResponse(
    status="OK",
    prediction=prediction,
    confidence_pct=95.2,
    required_features=["N", "P", "K", "temperature", "humidity", "ph", "rainfall"],
    available_features=["temperature", "humidity", "rainfall"],
    missing_features=["N", "P", "K", "ph"],
    sensor_data_quality=data_quality,
    recommendation="...",
    warnings=["Crop model requires NPK soil test for full accuracy"],
    caveats=["Without soil NPK data, recommendation is based on weather only"],
    model_version="rf_crop_v1.0",
    model_status="VERIFIED",
    calibration_status="CALIBRATED"
)
```

**Exit Criteria:**
- [ ] All AI endpoints return AIPredictionResponse
- [ ] Schema is consistent across all modules
- [ ] Tests verify schema compliance

---

## PHASE 4: Vision AI Trustworthiness (Tier 4)

**Duration:** 2 hours  
**Dependencies:** Phase 3  
**Blocks:** Phase 5

### Task 4.1: Implement sensor availability check in vision endpoint (2 hours)

**File:** `mlbackend/main.py` (POST /api/vision/diagnose-multimodal)

Add the validation pipeline:

```python
@app.post("/api/vision/diagnose-multimodal")
def diagnose_multimodal(
    image_bytes: bytes,
    include_multimodal: bool = False,
    crop_type: Optional[str] = None,
    language: str = "en"
):
    """
    Vision diagnosis with explicit sensor validation.
    """
    from mlbackend.schemas import VisionDiagnosis
    
    # Step 1: Image validation (vision_ai_model handles this)
    vision_result = local_vision_ai.diagnose(image_bytes)
    
    if vision_result["status"] in ("INVALID_IMAGE", "MODEL_UNAVAILABLE"):
        return VisionDiagnosis(
            status=vision_result["status"],
            diagnosis=None,
            warning=vision_result.get("action", "")
        )
    
    # Step 2: Check confidence threshold
    if vision_result["status"] == "NO_RELIABLE_RESULT":
        return VisionDiagnosis(
            status="NO_RELIABLE_RESULT",
            diagnosis=None,
            confidence_pct=vision_result["confidence_pct"],
            warning="Image valid but confidence below threshold."
        )
    
    # Step 3: Return image-only if not requesting multimodal
    if not include_multimodal:
        return VisionDiagnosis(
            status="VISION_DIAGNOSIS",
            diagnosis=vision_result["diagnosis"],
            confidence_pct=vision_result.get("confidence_pct"),
            mode="image_only",
            action=vision_result.get("action")
        )
    
    # Step 4: If requesting multimodal, check sensor availability
    telemetry = db_layer.get_latest_telemetry_canonical()
    
    required_sensors = ["soil_moisture_pct", "air_temperature_c", "ec_ms_cm"]
    missing_sensors = []
    
    for sensor in required_sensors:
        if telemetry["telemetry"].get(sensor) is None:
            missing_sensors.append(sensor)
    
    if missing_sensors:
        return VisionDiagnosis(
            status="INSUFFICIENT_SENSORS",
            diagnosis=vision_result["diagnosis"],  # Vision part is valid
            confidence_pct=vision_result.get("confidence_pct"),
            mode="image_only",  # Can't do multimodal
            required_sensors=required_sensors,
            missing_sensors=missing_sensors,
            warning=f"Cannot perform multimodal fusion. Missing sensors: {', '.join(missing_sensors)}. Image-only diagnosis provided.",
            action=vision_result.get("action")
        )
    
    # Step 5: All checks passed, perform multimodal fusion
    fusion_result = evaluate_multimodal_fusion(
        vision_label=vision_result["diagnosis"],
        soil_moisture=telemetry["telemetry"]["soil_moisture_pct"],
        temp_c=telemetry["telemetry"]["air_temperature_c"],
        ec_salinity=telemetry["telemetry"].get("ec_ms_cm", None)
    )
    
    return VisionDiagnosis(
        status="MULTIMODAL_DIAGNOSIS",
        diagnosis=fusion_result.get("fused_diagnosis"),
        confidence_pct=fusion_result.get("confidence_score_pct"),
        mode="image+sensors",
        action=fusion_result.get("recommended_action"),
        sensor_context={
            "soil_moisture_pct": telemetry["telemetry"]["soil_moisture_pct"],
            "air_temperature_c": telemetry["telemetry"]["air_temperature_c"],
            "ec_ms_cm": telemetry["telemetry"].get("ec_ms_cm")
        }
    )
```

**Exit Criteria:**
- [ ] Sensor availability checked before multimodal fusion
- [ ] Returns INSUFFICIENT_SENSORS when needed
- [ ] Falls back to image-only if sensors missing
- [ ] Tests verify correct behavior

---

## PHASE 5: Frontend (Tier 5)

**Duration:** 2 hours  
**Dependencies:** Phase 3  
**Blocks:** None (parallel with other phases)

### Task 5.1: Remove HTTP direct sensor path (1 hour)

**File:** `src/lib/sensorService.ts`

REPLACE entire file with:

```typescript
/**
 * Sensor data gateway — CANONICAL PATH ONLY
 * All telemetry queries go through backend API
 * No direct HTTP to ESP32
 * No fallback defaults
 */

export async function fetchSensorData(): Promise<SensorReadingResult> {
  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);
    
    const res = await fetch(`${BACKEND_URL}/api/telemetry/latest`, {
      signal: controller.signal,
      headers: { "Accept": "application/json" }
    });
    
    clearTimeout(timeoutId);
    
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    
    const json = await res.json();
    
    // No fallback defaults—return exactly what backend provided
    if (json.error || !json.telemetry) {
      return {
        success: false,
        error: {
          code: "SENSOR_UNAVAILABLE",
          message: json.message || "Sensor data unavailable. Device may be offline."
        }
      };
    }
    
    const tel = json.telemetry;
    
    // Check freshness
    if (tel.data_quality.status === "OFFLINE") {
      return {
        success: false,
        error: {
          code: "SENSOR_STALE",
          message: `Sensor offline for ${tel.age_seconds / 3600} hours`
        }
      };
    }
    
    const reading: SensorReading = {
      dht_ok: tel.air_temperature_c !== null && tel.humidity_pct !== null,
      soil_moisture: tel.telemetry.soil_moisture_pct ?? null,
      temperature: tel.telemetry.air_temperature_c ?? null,
      humidity: tel.telemetry.humidity_pct ?? null,
      light: null,  // Not provided by current hardware
      hasNpkSensor: tel.telemetry.nitrogen_ppm !== null,
      hasRainSensor: false,  // Not from hardware sensor
      timestamp: new Date(tel.received_at).getTime(),
      pump_relay: tel.actuator.pump_active ?? false,
      data_quality: tel.data_quality.status,
      age_seconds: tel.age_seconds
    };
    
    return { success: true, data: reading };
  } catch (err: any) {
    return {
      success: false,
      error: {
        code: err.name === "AbortError" ? "TIMEOUT" : "NETWORK_ERROR",
        message: err.message || "Failed to fetch sensor data"
      }
    };
  }
}
```

**Exit Criteria:**
- [ ] No `?? FALLBACK_VALUE` patterns
- [ ] All calls go to /api/telemetry/latest
- [ ] HTTP direct ESP32 path removed
- [ ] Tests verify no fallback defaults

---

### Task 5.2: Update frontend components (1 hour)

**Files:**
- `src/components/IoTDashboardModule.tsx`
- `src/components/CropRecommendationModule.tsx`
- `src/app/page.tsx`

Pattern for all components:

```typescript
// BEFORE:
const result = await fetchSensorData(esp32Ip);
if (!result.success) {
  showDefault();  // ← BAD
  return;
}

// AFTER:
const result = await fetchSensorData();
if (!result.success) {
  showUnavailable(result.error.message);  // ← GOOD
  return;
}

if (result.data.data_quality === "STALE") {
  showWarning("Sensor data is stale. Consider checking device.");
}

if (result.data.data_quality === "OFFLINE") {
  showError("Device appears offline. No live data available.");
  return;
}

// Use real data
displayTelemetry(result.data);
```

**Exit Criteria:**
- [ ] No fallback UI states showing fake data
- [ ] "Data unavailable" explicitly shown when offline
- [ ] Data freshness displayed to user
- [ ] Tests verify correct behavior

---

### Task 5.3: Delete HTTP sensor proxy route (30 min)

**File:** `src/app/api/sensors/[esp32Ip]/route.ts`

DELETE this file entirely. It's redundant with /api/telemetry/latest.

If you need to keep a development fallback, rename and mark it clearly:

```typescript
// ONLY FOR DEVELOPMENT/TESTING
// This route is NOT for production use
// Use /api/telemetry/latest instead

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ esp32Ip: string }> }
) {
  if (process.env.NODE_ENV === "production") {
    return NextResponse.json(
      { error: "This route is disabled in production. Use /api/telemetry/latest" },
      { status: 403 }
    );
  }
  // ... rest of development logic
}
```

**Exit Criteria:**
- [ ] Route deleted or marked development-only
- [ ] No calls to this route from frontend code
- [ ] All traffic goes to /api/telemetry/latest

---

## PHASE 6: Android App (Optional, Parallel with Phase 5)

**Duration:** 1 hour  
**Dependencies:** None (can start anytime after Phase 0)

### Task 6.1: Update LocalOfflineAdvisor.ts (1 hour)

**File:** `android-app/src/services/LocalOfflineAdvisor.ts`

Remove hardcoded defaults:

```typescript
// BEFORE (WRONG):
const temp = cachedSensors?.data?.temperature ?? 28;

// AFTER (CORRECT):
const temp = cachedSensors?.data?.temperature ?? null;

if (temp === null) {
  return "Device offline and no cached data. Please connect to restore recommendations.";
}
```

**Exit Criteria:**
- [ ] No hardcoded temperature/humidity defaults
- [ ] Offline message explicit when no cache
- [ ] Tests verify no fake advice generation

---

## Summary: Implementation Sequence

```
Phase 0 (2.5 hours): Schemas + Config
  ├─ Task 0.1: Create schemas.py (2 hours)
  └─ Task 0.2: Update config.py (30 min)
            ↓
Phase 1 (3 hours): MQTT Service
  ├─ Task 1.1: Add freshness tracking (1.5 hours)
  └─ Task 1.2: Update lifecycle tracking (1.5 hours)
            ↓
Phase 2 (2 hours): Database Layer
  ├─ Task 2.1: Create get_latest_telemetry_canonical() (1 hour)
  └─ Task 2.2: Add freshness helper (1 hour)
            ↓
Phase 3 (4 hours): Main.py API Endpoints
  ├─ Task 3.1: Create /api/telemetry/latest (1 hour)
  ├─ Task 3.2: Fix /api/crop-risk endpoint (1 hour)
  ├─ Task 3.3: Fix vision endpoint (1 hour)
  └─ Task 3.4: Update all AI responses (1 hour)
            ↓
Phase 4 (2 hours): Vision AI
  └─ Task 4.1: Sensor validation (2 hours)

Phase 5 (2 hours): Frontend [PARALLEL with 4]
  ├─ Task 5.1: Remove HTTP direct path (1 hour)
  ├─ Task 5.2: Update components (1 hour)
  └─ Task 5.3: Delete proxy route (30 min)

Phase 6 (1 hour): Android [PARALLEL with 5]
  └─ Task 6.1: Update offline advisor (1 hour)
```

**Total Estimated Time:**
- Sequential critical path (0→1→2→3→4): **13.5 hours**
- Parallel (5+6 while 3 running): **+2 hours** = **~15.5 hours**

---

## Testing & Rollout

### Pre-Deployment Checklist

- [ ] All schemas defined and type-checked
- [ ] No `or` operators with numeric defaults remain in Python
- [ ] No `??` operators with numeric defaults remain in TypeScript
- [ ] All telemetry endpoints return CanonicalTelemetry
- [ ] All AI endpoints return AIPredictionResponse
- [ ] Vision AI checks sensors before multimodal fusion
- [ ] Frontend shows explicit "data unavailable" messages
- [ ] MQTT service sets server timestamps
- [ ] Device state auto-computed from age
- [ ] Battery/signal/firmware metadata comes from telemetry, not hardcoded
- [ ] Integration tests pass
- [ ] Load tests pass

### Deployment Strategy

1. **Development:** Implement all phases in order
2. **Staging:** Deploy to staging, run full integration tests
3. **Canary:** Deploy to 5-10% production traffic
4. **Monitor:** Watch for errors, fallback handling, API response times
5. **Full Rollout:** 100% production traffic

### Monitoring Post-Deployment

- [ ] MQTT message count (should match telemetry count)
- [ ] Synthetic default injection count (should be zero)
- [ ] API error rates (should be ≤ 1%)
- [ ] Device state distribution (how many ONLINE vs OFFLINE)
- [ ] Frontend "data unavailable" frequency
- [ ] User complaints about fake data

---

**This plan ensures all cross-file contracts are fixed in the correct order. DO NOT skip phases or reorder them.**

