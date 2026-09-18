# AgriSaathi — Cross-File Contract Violations & Coordinated Refactoring

**Comprehensive analysis of all synthetic defaults, competing paths, and contract mismatches across the codebase**

---

## Executive Summary

The system has **7 categories of architectural violations** that must be fixed in coordinated phases:

1. **Synthetic defaults injected at multiple layers** (main.py, sensorService.ts, model_providers.py)
2. **Vision AI not trustworthy** (no image validation, allows multimodal fusion with missing sensors)
3. **No freshness tracking** (3-day-old telemetry treated as live)
4. **Device registration fabricates metadata** (battery%, signal, firmware version hardcoded)
5. **Competing telemetry paths** (MQTT, HTTP direct, /api/sensor-data, simulator)
6. **Feature contract mismatch** (model wants N/P/K/pH, hardware provides moisture/temp/humidity)
7. **Confidence scores not validated** (model probability ≠ real-world confidence)

---

## VIOLATION #1: SYNTHETIC DEFAULTS INJECTED AT MULTIPLE LAYERS

### Layer 1A: Frontend (src/lib/sensorService.ts, lines 66–69)

**Current Code:**
```typescript
const soil_moisture = Number(json.soil_moisture ?? json.z2_moisture ?? 40);
const temperature = Number(json.temperature ?? json.air_temp ?? 28);
const humidity = Number(json.humidity ?? json.z4_humidity ?? 65);
const light = Number(json.light ?? 8000);
```

**Problems:**
- ❌ If ESP32 offline → uses hardcoded defaults (40%, 28°C, 65%, 8000 lux)
- ❌ These fake values sent to backend as if they were real
- ❌ No indication to caller that values are fabricated
- ❌ If real sensor value is `0` (possible for some sensors), it gets replaced

**Impact:** Frontend sends fake sensor data to all downstream AI systems.

**Contract Violation:** `Sensor missing → no data` violated by `Sensor missing → hardcoded default`

---

### Layer 1B: Backend Weather Fallback (mlbackend/main.py, lines 675–678)

**Current Code (crop_risk_intelligence endpoint):**
```python
temp = weather.get("temp") or 25
rain = weather.get("rainfall_last_3h") or 0
humidity = weather.get("humidity") or 50
wind = weather.get("wind_speed") or 5
```

**Problems:**
- ❌ If weather API unavailable → uses defaults (25°C, 0mm, 50%, 5 km/h)
- ❌ These are presented to risk engine as if they were real weather
- ❌ Using `or` instead of checking `is None` (bad for 0-valued sensors)
- ❌ Comment says "Null-safe extraction" but it's actually unsafe

**Impact:** Risk engine receives fabricated weather data.

**Contract Violation:** `Weather unavailable → error` violated by `Weather unavailable → synthetic defaults`

---

### Layer 1C: Vision AI Multimodal Fusion (mlbackend/main.py, lines 1324–1339)

**Current Code (POST /api/vision/diagnose-multimodal):**
```python
humidity_source = "SENSOR" if payload.humidity is not None else "ESTIMATED_DEFAULT"
vision_res = local_vision_ai.diagnose(
    soil_moisture=payload.soil_moisture or 16.0,  # ← SYNTHETIC
    humidity=effective_humidity,
    image_bytes=image_bytes
)

fusion_result = evaluate_multimodal_fusion(
    vision_label=vision_res["diagnosis"],
    soil_moisture=payload.soil_moisture or 16.0,  # ← SYNTHETIC
    temp_c=payload.temp_c or 35.0,               # ← SYNTHETIC
    ec_salinity=payload.ec_salinity or 1.2       # ← SYNTHETIC
)
```

**Problems:**
- ❌ Missing soil moisture (None) → defaults to 16.0 (crisis level)
- ❌ Missing temperature (None) → defaults to 35.0 (extreme heat)
- ❌ Missing EC salinity (None) → defaults to 1.2
- ❌ Vision diagnosis receives fabricated sensor data
- ❌ Multimodal fusion runs with incomplete sensor picture
- ❌ Result looks confident but is based on synthetic data

**Impact:** Vision AI diagnosis is unreliable when sensors missing.

**Contract Violation:** `Sensors missing → insufficient data` violated by `Sensors missing → crisis scenario defaults`

---

### Layer 1D: Risk Engine (mlbackend/main.py, line 305–306)

**Current Code (compute_4zone_farm_status call site):**
```python
"alert": (
    "Irrigate now (Zone 2 critical)" if z2_moisture is not None and z2_moisture < 20 and (rain_prob or 0) < 50
```

**Problems:**
- ❌ Uses `rain_prob or 0` — if rain_prob is None, defaults to 0 (no rain expected)
- ❌ This makes the risk assessment artificially pessimistic

**Contract Violation:** `Data missing → unknown, use safe default` violated by `Data missing → numeric zero (interpret as fact)`

---

### Layer 1E: Model Providers (mlbackend/model_providers.py, lines 228–230)

**Current Code (NutrientDeficiencyModelProvider):**
```python
n_val = npk_measured.get("N", 45) if has_sensor_npk else None
p_val = npk_measured.get("P", 22) if has_sensor_npk else None
k_val = npk_measured.get("K", 38) if has_sensor_npk else None
```

**Problems:**
- ❌ If NPK sensor dict exists but is missing N → defaults to 45 (normal level)
- ❌ Diagnostic engine receives these "normal" defaults
- ❌ Diagnosis looks confident but is based on fabricated data

**Contract Violation:** `Missing NPK → wait for real data` violated by `Missing NPK → assume normal levels`

---

### Layer 1F: Android Offline Advisor (android-app/src/services/LocalOfflineAdvisor.ts, line 18)

**Current Code:**
```typescript
const temp = cachedSensors?.data?.temperature ?? cachedSensors?.data?.temperature_c ?? 28;
```

**Problems:**
- ❌ If no cached sensor → defaults to 28°C
- ❌ Mobile user sees advice based on hardcoded temperature

**Contract Violation:** `No cache → show "offline, data unavailable"` violated by `No cache → assume 28°C`

---

## VIOLATION #2: VISION AI IS NOT TRUSTWORTHY

### Current Vision AI Pipeline

**File:** `mlbackend/vision_ai_model.py`

**Current flow:**
1. Receive image bytes
2. Validate image format/size ✅
3. Check if image is structurally variance (not blank) ✅
4. Extract HOG features ✅
5. Run SVM classifier ✅
6. Return diagnosis + confidence ✅

**Problem:** This pipeline is IMAGE-ONLY. But main.py endpoint THEN does:

```python
# main.py lines 1324–1339
vision_res = local_vision_ai.diagnose(image_bytes)  # Image-only diagnosis ✅

# Then immediately:
fusion_result = evaluate_multimodal_fusion(
    vision_label=vision_res["diagnosis"],  # Use vision result
    soil_moisture=payload.soil_moisture or 16.0,  # ← Synthetic
    temp_c=payload.temp_c or 35.0,               # ← Synthetic
    ec_salinity=payload.ec_salinity or 1.2       # ← Synthetic
)
```

**Result:** System claims "multimodal vision+soil+EC diagnosis" but:
- Image diagnosis is real ✅
- Soil moisture is synthetic (16%) if missing ❌
- Temperature is synthetic (35°C) if missing ❌
- EC is synthetic (1.2) if missing ❌
- Confidence score is treated as if all inputs were real ❌

### What Should Happen Instead

**Correct Vision AI Pipeline:**

```
IMAGE
  ↓
Is this actually a crop/leaf image?
  ├─ NO → REJECT / INSUFFICIENT_IMAGE
  └─ YES
    ↓
Extract vision features + confidence
  ↓
Check confidence threshold
  ├─ NO (low confidence) → NO_RELIABLE_RESULT
  └─ YES (high confidence)
    ↓
Check if multimodal fusion is needed
  ├─ NO (vision-only diagnosis sufficient) → RETURN vision result
  └─ YES (need soil/EC/temp for context)
    ↓
Check if required REAL sensors exist
  ├─ NO → RETURN vision-only result, flag as "image_only"
  └─ YES
    ↓
Perform multimodal fusion
  ↓
RETURN fused diagnosis
```

### Current vision_ai_model.py Validation (GOOD)

The vision_ai_model.py itself is actually quite robust:

- ✅ `validate_leaf_image()` rejects non-leaf images (lines 76–94)
- ✅ Checks image size, format, variance
- ✅ Returns `NO_RELIABLE_RESULT` if confidence below threshold (lines 240–253)
- ✅ Returns `EXPERIMENTAL_PREDICTION` with warning (lines 254–265)
- ✅ Handles model unavailability gracefully

**The problem is NOT in vision_ai_model.py. It's in main.py using vision results.**

---

## VIOLATION #3: NO FRESHNESS TRACKING

### Current Issue

**File:** `mlbackend/db_layer.py`, `mlbackend/main.py`

When frontend calls `/api/telemetry/latest`:

```python
# main.py
latest = db_layer.get_latest_telemetry(device_id="ESP32_NODE_01")

if not latest:
    return {"error": True, "data_source": "UNAVAILABLE"}

return {
    "error": False,
    "data": latest,
    "data_source": "MQTT_VALIDATED",
    "timestamp": datetime.now(timezone.utc).isoformat()
}
```

**Problem:** No indication of WHEN the data was received.

**Example:**
- Telemetry received: Tuesday 9 AM
- Frontend queries: Friday 6 PM (80 hours later)
- System returns: `"data_source": "MQTT_VALIDATED"` (sounds fresh!)
- Reality: Data is 3 days old, sensor might be dead

### What's Missing

The response should include:

```json
{
  "status": "OK",
  "data": {...},
  "telemetry_age_seconds": 289200,  // 80 hours
  "data_quality": "STALE",          // not "GOOD"
  "timestamp": "2026-09-17T13:20:15Z",
  "received_at": "2026-09-14T09:15:00Z"
}
```

### Freshness Contract Needed

In `config.py`, define:

```python
TELEMETRY_FRESHNESS_THRESHOLDS = {
    "LIVE": 600,        # ≤ 10 minutes
    "STALE": 21600,     # > 10 min, ≤ 6 hours
    "OFFLINE": 86400,   # > 6 hours
    "UNKNOWN": float('inf')
}
```

---

## VIOLATION #4: DEVICE REGISTRATION FABRICATES METADATA

### Current Issue

**File:** `mlbackend/main.py` (device registration endpoint)

**Request:**
```json
{
  "device_id": "ESP32_NODE_01",
  "sensors": ["Soil Moisture", "Temperature", "Humidity"]
}
```

**Response:**
```json
{
  "device_id": "ESP32_NODE_01",
  "status": "ONLINE",
  "battery_pct": 94,
  "signal_rssi_dbm": -62,
  "firmware_version": "v2.4.1"
}
```

**Problems:**
- ❌ Status is "ONLINE" immediately after registration (device hasn't sent telemetry yet!)
- ❌ Battery % is hardcoded to 94
- ❌ Signal strength is hardcoded to -62 dBm
- ❌ Firmware version is hardcoded to v2.4.1
- ❌ All of this is fabrication

### Correct Device States

Device should have explicit lifecycle states:

```python
class DeviceState(Enum):
    REGISTERED = "registered"      # Device created in DB, awaiting first telemetry
    ONLINE = "online"              # Device sent telemetry within LIVE threshold
    STALE = "stale"                # Device sent telemetry but data is STALE
    OFFLINE = "offline"            # Device hasn't sent data for > 6 hours
    ERROR = "error"                # Device sent data but with validation errors
```

**Correct response after registration:**

```json
{
  "device_id": "ESP32_NODE_01",
  "status": "REGISTERED",
  "message": "Device registered successfully. Awaiting first telemetry packet.",
  "expected_sensors": ["soil_moisture", "temperature", "humidity"],
  "battery_pct": null,
  "signal_rssi_dbm": null,
  "firmware_version": null,
  "first_telemetry_received_at": null
}
```

### Metadata Sources

Once device comes online, metadata comes from real telemetry:

```python
# Only populate if we've received a packet
"battery_pct": packet.get("battery_pct"),        # From telemetry
"signal_rssi_dbm": packet.get("signal_rssi"),    # From telemetry
"firmware_version": packet.get("fw_version"),    # From telemetry
"first_telemetry_received_at": lifecycle["first_seen_at"]
```

---

## VIOLATION #5: COMPETING TELEMETRY PATHS

### Path A: MQTT → mqtt_service.py → db_layer → canonical_telemetry ✅

```
ESP32 → MQTT → mqtt_service.parse_and_validate() → db_layer.store_telemetry_packet()
```

**Status:** GOOD (validated, deduplicated, persisted)

---

### Path B: HTTP Direct ESP32 (sensorService.ts) ❌

```
ESP32 → HTTP /sensors endpoint → sensorService.ts → [fallback defaults] → frontend
```

**Status:** BAD (no validation, fallback defaults, inconsistent with MQTT)

---

### Path C: FastAPI Proxy (src/app/api/sensors/[esp32Ip]/route.ts) ⚠️

```
ESP32 → HTTP /sensors → [Next.js proxy] → frontend
```

**Status:** REDUNDANT (same as Path B, wrapped in Next.js)

---

### Path D: /api/sensor-data Endpoint ⚠️

**File:** `mlbackend/main.py` (search for `/api/sensor-data`)

**Status:** UNCLEAR (need to find where this is used)

---

### Path E: Simulator (ESP32 Simulator) ⚠️

**File:** `mlbackend/esp32_simulator.py`

**Status:** For testing only, but could leak into production

---

### Current State

Frontend can receive sensor data from **5 different paths**, creating:
- Inconsistent validation
- Different fallback behaviors
- Conflicting freshness tracking
- Confusion about which is "canonical"

### Desired State

```
┌──────────────────────┐
│ CANONICAL PATH ONLY  │
└──────────────────────┘

ESP32 → MQTT → mqtt_service.py → validation → canonical_telemetry (SQLite)

Frontend queries: GET /api/telemetry/latest

Backend response includes: status, data, age_seconds, data_quality

HTTP /sensors endpoint: DEVELOPMENT ONLY, explicitly marked
```

---

## VIOLATION #6: FEATURE CONTRACT MISMATCH

### Model Training Features

**File:** `mlbackend/training/train_crop_recommendation.py`

```python
X_train = df_train[['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']]
```

**Model expects 7 features:** `[N, P, K, temperature, humidity, pH, rainfall]`

### Hardware Provides

**File:** `edge_hardware/esp32_sensor_node.ino` (actual telemetry)

```json
{
  "telemetry": {
    "soil_moisture_pct": 45.3,
    "temperature_c": 28.5,
    "humidity_pct": 65.2,
    "nitrogen": null,
    "phosphorus": null,
    "potassium": null
  }
}
```

**Hardware provides 2 features:** `[temperature, humidity]`

### What's Missing

- ❌ **N (Nitrogen)** — No sensor
- ❌ **P (Phosphorus)** — No sensor
- ❌ **K (Potassium)** — No sensor
- ❌ **pH** — No sensor
- ✅ **Temperature** — DHT22
- ✅ **Humidity** — DHT22
- ✅ **Rainfall** — Available from weather API

### Current Behavior

**File:** `mlbackend/main.py` endpoint `/api/recommend/crop`

When user doesn't provide N/P/K:

```python
@app.post("/api/recommend/crop")
def recommend_crop(features: CropFeatures):
    # features.N, features.P, features.K might be missing
    # if missing: CropFeatures validation fails? Or uses defaults?
```

**Need to check:** Does CropFeatures have default values for N/P/K?

(Answer from schema earlier: Yes, they're marked as required without defaults)

### Three Possible Solutions

#### Solution A: Return INSUFFICIENT_DATA

```python
if features.N is None or features.P is None or features.K is None:
    return {
        "status": "INSUFFICIENT_DATA",
        "message": "Crop recommendation requires soil NPK test results.",
        "required_sensors": ["N", "P", "K"],
        "available_sensors": ["temperature", "humidity", "rainfall"],
        "next_steps": "Upload a soil test report or conduct a soil sample."
    }
```

**Pros:** Honest, no fabrication
**Cons:** Blocks all crop recommendations

---

#### Solution B: Train New 3-Feature Model

Train separate model on `[temperature, humidity, rainfall]` only.

```python
# Check which features are available
if features.N is None or features.P is None or features.K is None:
    # Use reduced model
    features_vec = [features.temperature, features.humidity, features.rainfall]
    prediction = reduced_model.predict([features_vec])[0]
else:
    # Use full model
    features_vec = [features.N, features.P, features.K, features.temperature, features.humidity, features.ph, features.rainfall]
    prediction = full_model.predict([features_vec])[0]
```

**Pros:** Works immediately with current hardware
**Cons:** Requires model retraining

---

#### Solution C: Require Manual NPK Upload

Offer farmers ability to upload soil test results.

```python
# Check if farmer has uploaded soil test
soil_test = db_layer.get_latest_soil_test(farm_id)

if not soil_test or soil_test["age_days"] > 30:
    return {
        "status": "INSUFFICIENT_DATA",
        "message": "Crop recommendation requires recent soil test (< 30 days old)",
        "upload_url": "/api/soil-test/upload"
    }

# Use soil test data
features_vec = [
    soil_test["nitrogen"],
    soil_test["phosphorus"],
    soil_test["potassium"],
    weather.temperature,
    weather.humidity,
    soil_test["ph"],
    weather.rainfall
]
```

**Pros:** Most accurate (real lab data)
**Cons:** Requires farmer action

---

## VIOLATION #7: CONFIDENCE SCORES NOT VALIDATED

### Current Issue

**File:** `mlbackend/main.py` crop endpoint

```python
probabilities = model.predict_proba(data)[0]
confidence_score = round(float(max(probabilities)) * 100, 2)

return RecommendationResponse(
    recommended_crop=predicted_crop,
    confidence=confidence_score,  # 99.2%
    prediction_confidence=confidence_score,
    test_accuracy=crop_model_provenance["accuracy"],
)
```

### Problem

**What confidence score means:**
- Model probability that this class (crop) has highest probability in the trained feature space

**What farmers interpret it as:**
- "99.2% chance this crop will succeed on my farm"

**Gap:**
- Model trained on historical data (different farm, different year, different conditions)
- No field validation against real outcomes
- No calibration check (is 99% really 99%, or actually 87%?)
- No consideration of out-of-distribution inputs
- No check for impossible feature combinations

### What Should Be Done

#### Calibration Check

```python
# Load calibration metadata
calibration = model_metadata.get("calibration", {})

if not calibration:
    return {
        "confidence": confidence_score,
        "calibration_status": "UNCALIBRATED",
        "warning": "This confidence score has not been validated against real farm data."
    }

# Apply calibration correction
calibrated_confidence = calibration["curve"](confidence_score)

return {
    "confidence": confidence_score,
    "calibrated_confidence": calibrated_confidence,
    "calibration_status": "CALIBRATED",
    "note": "Confidence score is based on model training data and field-validated calibration."
}
```

#### Input Validation

```python
# Check if input is out-of-distribution
ood_score = outlier_detector.score(features_vec)

if ood_score > OOD_THRESHOLD:
    return {
        "recommended_crop": None,
        "confidence": 0.0,
        "status": "OUT_OF_DISTRIBUTION",
        "message": "Your soil/climate conditions are unusual compared to training data.",
        "recommendation": "Consult a local agronomist."
    }
```

---

## SUMMARY TABLE: ALL VIOLATIONS

| # | Category | File(s) | Line(s) | Severity | Fix Impact |
|---|----------|---------|---------|----------|-----------|
| 1A | Synthetic defaults (frontend) | sensorService.ts | 66–69 | 🔴 Critical | Remove all `?? NUMBER` |
| 1B | Weather API defaults | main.py | 675–678 | 🔴 Critical | Replace `or` with `is None` checks |
| 1C | Vision multimodal synthetic | main.py | 1324–1339 | 🔴 Critical | Remove `or` operators, return INSUFFICIENT_DATA |
| 1D | Risk engine rainfall default | main.py | 305–306 | 🟠 High | Use `rain_prob if rain_prob is not None else None` |
| 1E | Model provider NPK defaults | model_providers.py | 228–230 | 🟠 High | Remove `.get()` with defaults |
| 1F | Mobile offline advisor default | LocalOfflineAdvisor.ts | 18 | 🟡 Medium | Return null instead of 28°C |
| 2 | Vision AI trusts sensor inputs | main.py | 1324–1339 | 🔴 Critical | Add sensor availability check before fusion |
| 3 | No freshness tracking | All telemetry endpoints | N/A | 🔴 Critical | Add `age_seconds` and `data_quality` to all responses |
| 4 | Device metadata fabricated | main.py | Device registration | 🟠 High | Return null for metrics not yet received |
| 5 | Competing telemetry paths | Multiple | Multiple | 🟠 High | Unify to single canonical path |
| 6 | Feature contract mismatch | Training vs Hardware | N/A | 🔴 Critical | Choose Solution A/B/C and implement consistently |
| 7 | Confidence not calibrated | main.py | Crop endpoint | 🟡 Medium | Add calibration metadata and OOD checks |

---

## CROSS-FILE DEPENDENCIES

### Group 1: Must Change Together (Highest Priority)

These files have direct data contracts:

**mqtt_service.py ↔ db_layer.py ↔ main.py**

- mqtt_service validates and parses telemetry
- Passes to db_layer.store_telemetry_packet()
- main.py calls db_layer.get_latest_telemetry()
- **Change:** All three must agree on freshness contract

**sensorService.ts ↔ main.py telemetry endpoint**

- Frontend calls sensorService.fetchSensorData()
- Backend exposes /api/telemetry/latest
- **Change:** sensorService must call backend, not ESP32 directly

---

### Group 2: Vision AI Stack

**vision_ai_model.py ↔ main.py ↔ model_providers.py**

- vision_ai_model.diagnose() returns image diagnosis
- main.py endpoint calls it, then calls model_providers multimodal_fusion()
- **Change:** Add sensor availability checks between vision and fusion

---

### Group 3: Device Lifecycle

**pump_controller.py ↔ db_layer.py ↔ mqtt_service.py**

- mqtt_service marks device online/offline
- pump_controller queries device status
- db_layer tracks lifecycle
- **Change:** All three must use same state enum

---

### Group 4: Model Training

**training/train_crop_recommendation.py ↔ main.py**

- Training defines feature expectations
- main.py uses model in CropFeatures schema
- **Change:** Feature contract must be explicit

---

## NEXT STEPS

This document completes **Tasks #1 & #2** of the remediation plan.

**Next: Create the canonical schema designs (Task #3)**

