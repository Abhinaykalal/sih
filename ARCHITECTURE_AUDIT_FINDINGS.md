# AgriSaathi Architecture Audit — Critical Findings
**Date:** September 17, 2026  
**Scope:** Sensor hardware → MQTT ingestion → Database → ML inference → Frontend  
**Status:** ⚠️ **CRITICAL ARCHITECTURAL MISALIGNMENTS IDENTIFIED**

---

## Executive Summary

The system currently exhibits **two competing data sources** (MQTT-to-SQLite vs HTTP direct-ESP32), **synthetic default values** being fabricated into predictions, and a **fundamental mismatch** between what sensors physically exist and what the crop recommendation model requires. The AI output is unreliable because the input pipeline does not enforce a "no sensor data = no prediction" contract.

**Golden Rule (Target Architecture):**
```
VALID LIVE DATA + VERIFIED SENSOR → AI PREDICTION
        OR
MISSING / STALE / INVALID DATA → INSUFFICIENT_DATA (no fabricated output)
```

---

## 🔴 TIER 1: HARDWARE → MQTT INGESTION

### Current ESP32 Telemetry Payload

**File:** `edge_hardware/esp32_sensor_node.ino`  
**Sensors Actually Connected:**
- ✅ Soil Moisture (ADC pin 34, mapped to 0-100%)
- ✅ Temperature (DHT22 pin 4)
- ✅ Humidity (DHT22 pin 4)
- ✅ Light (commented out / not in payload)
- ✅ Actuator State (pump relay pin 26)
- ❌ **NPK (N, P, K)** — NOT connected. No sensor hardware.
- ❌ **pH** — NOT connected.
- ❌ **EC (Salinity)** — NOT connected.
- ❌ **Rainfall** — NOT connected.
- ❌ **Pest Counts** — NOT connected.

### Actual Telemetry Published to MQTT

```json
{
  "device_id": "ESP32_NODE_01",
  "timestamp": 1234567890,
  "telemetry": {
    "soil_moisture_pct": 45.3,
    "soil_raw_adc": 1850,
    "temperature_c": 28.5,
    "humidity_pct": 65.2,
    "nitrogen": null,
    "phosphorus": null,
    "potassium": null
  },
  "actuator": {
    "pump_active": false
  },
  "edge_ai": {
    "last_scan_result": "NORMAL",
    "confidence_pct": null
  }
}
```

### MQTT Service Validation

**File:** `mlbackend/mqtt_service.py`

✅ **Strengths:**
- Parses JSON correctly; preserves `null` as Python `None` (does NOT coerce to 0).
- Validates numeric ranges (soil moisture 0-100%, ADC 0-4095, temperature -10 to 60°C).
- Enforces device identity: cross-validates MQTT topic vs payload `device_id` (anti-spoofing).
- Stores raw payload + cleaned record with validation errors in SQLite.
- Marks device lifecycle (online/offline) on packet arrival.

❌ **Issues:**
- None identified. MQTT service is robust.

**Finding:** ✅ Tier 1 is **correct and secure**. The MQTT layer preserves sensor reality.

---

## 🔴 TIER 2: AI MODEL MISMATCH

### Crop Recommendation Model Training Specification

**File:** `mlbackend/training/train_crop_recommendation.py` (examined during cross-check)

**Model Feature Vector (at training time):**
```
[N, P, K, temperature, humidity, pH, rainfall]
```
7 features required for inference.

### What the Model Requires at Runtime

For the crop model to generate a prediction, it needs:
1. **N** (Nitrogen) — mg/kg
2. **P** (Phosphorus) — mg/kg
3. **K** (Potassium) — mg/kg
4. **temperature** — °C ✅ HAVE (from DHT22)
5. **humidity** — % ✅ HAVE (from DHT22)
6. **pH** — soil pH ❌ DON'T HAVE
7. **rainfall** — mm/year ❌ DON'T HAVE (must come from weather API, not sensor)

### What the ESP32 Can Provide

- ✅ Temperature
- ✅ Humidity
- ❌ N, P, K (no sensor hardware)
- ❌ pH (no sensor hardware)
- ❌ Rainfall (no sensor hardware — must use weather forecast)

### The Critical Mismatch

```
┌─────────────────────────────────────────────────────────────┐
│ PROBLEM: Cannot connect live ESP32 telemetry to crop model │
├─────────────────────────────────────────────────────────────┤
│ Model was trained on: N, P, K, temp, humidity, pH, rainfall│
│ ESP32 provides only: temp, humidity (+ synthetic defaults?)│
│                                                              │
│ If we push synthetic values for missing features:           │
│   "N=45, P=22, K=38 (fabricated)"                           │
│   → Prediction becomes unreliable fiction.                  │
│                                                              │
│ If we leave them as None:                                   │
│   → Model cannot compute (array dimension mismatch).        │
└─────────────────────────────────────────────────────────────┘
```

### Current Risk Engine Behavior (main.py, risk_engine.py)

**File:** `mlbackend/risk_engine.py` (line excerpt shown in your audit):

```python
z1_moisture = float(sensor_data.get("z1_moisture", 45.0) or 45.0)
z2_moisture = float(sensor_data.get("z2_moisture", 16.0) or 16.0)
z4_humidity = float(sensor_data.get("z4_humidity", 90.0) or 90.0)
air_temp = float(sensor_data.get("air_temp", 35.0) or 35.0)
rain_prob = float(sensor_data.get("rain_prob", 20.0) or 20.0)
```

**This is dangerous:**
- **No sensor data?** → Defaults are applied.
- **Defaults:** `16% moisture, 35°C, 90% humidity, 20% rain` = **CRISIS CONDITIONS**.
- **Result:** A completely offline farm gets flagged as critical risk.

**Issue Type:** 🔴 **Synthetic Default Injection**

### Finding: ⚠️ Tier 2 is **BROKEN**

The crop recommendation model cannot honestly receive live ESP32 telemetry because:
1. The hardware doesn't measure N, P, K, pH.
2. There is no fallback model that works with only temperature + humidity.
3. The risk engine applies synthetic crisis defaults when sensors are missing.

**Consequence:** AI output is **not trustworthy**. It mixes real sensor data with fabricated guesses.

---

## 🟠 TIER 3: FRONTEND DATA SOURCE CONFLICT

### Competing Sensor Data Sources

**Problem:** The Next.js application can fetch sensor data from **two independent systems**:

#### Source A: HTTP Direct to ESP32

**File:** `src/lib/sensorService.ts`

```typescript
export async function fetchSensorData(ip: string, retries = 2): Promise<SensorReadingResult> {
  const url = `http://${cleanIp}/sensors`;  // ← Direct HTTP request to ESP32
  
  const json = await res.json();
  
  // Fallback defaults if values missing:
  const soil_moisture = Number(json.soil_moisture ?? json.z2_moisture ?? 40);
  const temperature = Number(json.temperature ?? json.air_temp ?? 28);
  const humidity = Number(json.humidity ?? json.z4_humidity ?? 65);
  const light = Number(json.light ?? 8000);
```

**Issues:**
- ❌ Fallback defaults (40%, 28°C, 65%, 8000 lux) fabricate sensor values.
- ❌ No validation of numeric ranges (could receive 999% humidity and accept it).
- ❌ No anti-spoofing; direct trust in payload.
- ❌ No deduplication; same reading fetched repeatedly = duplicate records.

#### Source B: MQTT → FastAPI → SQLite

**File:** `mlbackend/main.py` → `/api/sensors/[esp32Ip]` route

```
ESP32 → MQTT → mqtt_service.py → canonical_telemetry (SQLite) → FastAPI /api/sensors → Next.js
```

**Strengths:**
- ✅ Validated through mqtt_service.py (ranges, nulls preserved).
- ✅ Centralized source of truth in SQLite.
- ✅ Deduplication via packet hash.
- ✅ Device lifecycle tracking.

### The Architecture Collision

```
                    ┌──────────────────────┐
                    │      ESP32 NODE      │
                    │                      │
                    │ Soil Moisture        │
                    │ Temperature         │
                    │ Humidity             │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
              ┌─────────────┐      ┌─────────────┐
              │ HTTP /sensors │     │ MQTT        │
              │ (Direct)      │     │ (Validated) │
              └─────────────┘      └──────┬──────┘
                    │                     │
                    │                 SQLite
                    │                     │
                    ▼                     ▼
              Next.js App ◄──── FastAPI (duplicate path)
```

**Finding:** 🟠 **Tier 3 is BROKEN**

- Frontend has two competing data paths.
- HTTP direct path lacks validation and uses synthetic defaults.
- This creates confusion about which values are real.
- **Your stated requirement:** "The current Next.js sensorService.ts directly requests http://ESP32_IP/sensors… That's something I specifically want removed from the production/live-data path."

---

## 🟠 TIER 4: DATABASE & CLOUD SYNC

### Current State

**File:** `mlbackend/db_layer.py` (header):

```python
"""
NOTE ON CLOUD SYNC:
Cloud sync (Supabase) is not yet implemented. The `synced_to_cloud` flag exists 
in schema but no Supabase upload worker is wired. `canonical_sync_queue` stores 
records locally for audit but does NOT guarantee cloud delivery. Any Supabase 
integration requires a background worker with its own idempotency key and 
exponential backoff.
"""
```

**Database Schema:**
- ✅ `canonical_telemetry` (local SQLite) — stores validated MQTT packets.
- ✅ `canonical_sync_queue` — audit trail for cloud delivery (but never executed).
- ⚠️ `synced_to_cloud` flag — exists but not used.

### Issue

**🔴 No Canonical Source of Truth in Cloud:**
- Telemetry lives **only locally** on the edge SQLite database.
- If the edge device fails, **all historical telemetry is lost**.
- Supabase integration is declared but not implemented.
- No background worker exists to push data to cloud.

### Finding: 🟠 **Tier 4 is INCOMPLETE**

**Consequence:** 
- No cloud-based audit trail.
- No cross-device historical analysis.
- No federated farm-network view (if multiple edge nodes existed).

---

## 🟡 TIER 5: AI/RISK/ADVISORY PIPELINE

### Current Architecture

**Files:**
- `mlbackend/agent_orchestrator.py`
- `mlbackend/fertilizer_service.py`
- `mlbackend/soil_service.py`
- `mlbackend/pest_service.py`
- `mlbackend/yield_service.py`
- `mlbackend/rotation_service.py`

### Problem: Input Assumptions

These services accept sensor readings but **do not validate** that the readings are real:

**Example from `model_providers.py`:**

```python
def assess_irrigation_needs(
    self,
    soil_moisture: Optional[float],
    air_temp: Optional[float] = None,
    humidity: Optional[float] = None,
    rain_forecast_mm: Optional[float] = None,
    crop: str = "Rice",
    growth_stage: str = "Vegetative",
    last_updated_seconds_ago: int = 0,
    is_simulated: bool = False
) -> IrrigationAssessmentResult:
```

✅ **Good:**
- Accepts `None` for missing sensors.
- Returns `DATA_UNAVAILABLE` when soil moisture is missing.

❌ **Bad:**
- Callers might still pass synthetic defaults instead of None.
- No enforcement at the endpoint level.

### Finding: 🟡 **Tier 5 is CONDITIONAL**

**Verdict:** Once Tier 1 and 2 are fixed, Tier 5 will be reliable.

---

## 🚨 VISIBLE PROBLEMS ALREADY IN CURRENT CODE

### 1. Synthetic Defaults in Risk Engine (risk_engine.py)

```python
# CURRENT CODE (DANGEROUS):
z1_moisture = float(sensor_data.get("z1_moisture", 45.0) or 45.0)
```

**Problem:**
- If sensor is offline, `45.0` is treated as real data.
- The `or` clause means even `0.0` gets replaced with the default (wrong for numeric sensor data).

**Fix Required:**
```python
# CORRECT:
z1_moisture = sensor_data.get("z1_moisture")  # Preserve None / 0 / missing distinction
if z1_moisture is None:
    # Handle missing data — maybe return NO_DATA status, not a crisis prediction
    return {"status": "INSUFFICIENT_DATA"}
```

### 2. Or-Operator Danger for Sensor Telemetry (mqtt_service.py, model_providers.py)

**Current bad pattern:**
```python
value = data.get("temperature", 28) or 28
```

**Problem:** `0` is a legitimate reading. Using `or` coerces it to the default.

**Correct pattern:**
```python
value = data.get("temperature")
if value is None:
    # Handle missing
    return INSUFFICIENT_DATA
```

**Status in Code:** ✅ **MQTT service already does this correctly**. ✅ **Model providers already do this correctly**.

### 3. Two Competing Sensor Paths (sensorService.ts)

**Problem:** Frontend can fetch from HTTP direct OR from MQTT-backed FastAPI.

**Your stated requirement:** Remove HTTP direct path.

**Finding:** ✅ **Identified. Ready for remediation.**

### 4. Model Integrity Verified, But Data Contract Not

**File:** `main.py` (crop recommendation endpoint)

```python
if meta_hash == artifact_hash:
    model = joblib.load(model_path)
    crop_model_provenance["status"] = "VERIFIED"
```

✅ **Good:** Model artifact hash is verified.
❌ **Bad:** But the **input feature vector** is never validated to match the model's training features.

**Current Issue:**
- If someone calls the endpoint with only 2 features (temp, humidity), the model silently fails.
- No error is raised about the feature mismatch.

---

## 🎯 TARGET ARCHITECTURE

Based on your stated requirements:

```
┌──────────────────────────────────────────────────────────────────┐
│                     CANONICAL TELEMETRY SOURCE                   │
└──────────────────────────────────────────────────────────────────┘

    ┌────────────┐
    │   ESP32    │
    │  (Real)    │
    └─────┬──────┘
          │
      MQTT │ TLS
          │
    ┌─────▼──────────────────────────────┐
    │ MQTT Service Validation             │
    │ - Parse JSON                        │
    │ - Validate ranges                   │
    │ - Preserve None / zeros             │
    │ - Anti-spoofing (topic vs payload)  │
    └─────┬──────────────────────────────┘
          │
    ┌─────▼──────────────────────────────┐
    │ Canonical SQLite (canonical_telemetry) │
    │ - One source of truth               │
    │ - Deduplication by hash             │
    │ - Device lifecycle tracking         │
    └─────┬──────────────────────────────┘
          │
    ┌─────┴────────────────────┬─────────────────────────┐
    │                          │                         │
  ▼ ▼                        ▼ ▼                       ▼ ▼
Risk Engine          ML Inference              Analytics
├─ Real sensor       ├─ N, P, K from API       ├─ Yield trending
│  data only         │  (if available)         ├─ Long-term patterns
├─ Return:           ├─ temperature, humidity  ├─ Device health
│  PREDICTION        │  from ESP32             │  metrics
│  or                ├─ pH, rainfall from API  │
│  INSUFFICIENT_DATA │  (if available)         │
│                    ├─ Return: PREDICTION     │
│                    │  or INSUFFICIENT_DATA   │
│                    │  (never fabricated)     │
└────────────────────┴────────────────────────┴─────────────────────

    ┌─────────────────────────────────────────┐
    │ FastAPI Unified Endpoint                │
    │ (Single source of truth for frontend)   │
    │ /api/telemetry/latest                   │
    │ /api/telemetry/history                  │
    │ /api/predictions/crop-recommend         │
    │ /api/predictions/irrigation             │
    └─────────────────────────────────────────┘
          │
    ┌─────▼──────────────────┐
    │  Next.js Frontend       │
    │  (Mobile / Web)         │
    │                         │
    │ ✅ No HTTP /sensors     │
    │ ✅ Trust single API     │
    └─────────────────────────┘

CLOUD SYNC (Future):
    ┌─────────────────────────────────────────┐
    │ Cloud Sync Worker (Background)          │
    │ Reads: canonical_sync_queue (SQLite)    │
    │ Writes: Supabase (cloud audit trail)    │
    │ Idempotency: client_action_id + hash    │
    └─────────────────────────────────────────┘
```

---

## 📋 REMEDIATION ROADMAP

### Phase 1: Eliminate Synthetic Defaults (🔴 CRITICAL)

**Priority:** Highest  
**Files to modify:**
1. `mlbackend/risk_engine.py` — Remove synthetic defaults; return DATA_UNAVAILABLE instead
2. `mlbackend/model_providers.py` — Audit all `or` operators on sensor data
3. `src/lib/sensorService.ts` — Remove HTTP direct path; consolidate to FastAPI

**Principle:**
```
NO SENSOR → NO PREDICTION
            only INSUFFICIENT_DATA
```

### Phase 2: Define Feature Contract for Crop Model (🟠 HIGH)

**Priority:** High  
**Decision:**
- **Option A:** Train a new model on only [temperature, humidity, rainfall] (feasible).
- **Option B:** Mandate N, P, K sensors in hardware; keep existing model (requires hardware redesign).
- **Option C:** Return "SENSORS_INSUFFICIENT" for crop recommendation if N/P/K missing.

**Recommendation:** **Option A or C** (do not force hardware redesign mid-sprint).

### Phase 3: Unify Sensor Data Path (🟠 HIGH)

**Priority:** High  
**Action:** Remove HTTP `/sensors` endpoint from ESP32; make sensorService.ts only call FastAPI.

**Result:** Single source of truth.

### Phase 4: Implement Cloud Sync Worker (🟡 MEDIUM)

**Priority:** Medium  
**Timeline:** After Phases 1–3 are stable.

### Phase 5: Add Input Validation to Model Endpoints (🟡 MEDIUM)

**Priority:** Medium  
**Action:** Endpoints validate that feature vectors match model training schema before inference.

---

## 📊 CURRENT STATE vs. TARGET STATE

| Component | Current | Target | Status |
|-----------|---------|--------|--------|
| MQTT validation | ✅ Robust | ✅ Robust | ✓ Good |
| Synthetic defaults in risk engine | ❌ Yes | ❌ None | 🔴 Fix |
| Crop model feature contract | ⚠️ Undefined | ✅ Documented | 🟠 Define |
| Competing sensor sources | ❌ Yes (HTTP + MQTT) | ❌ One (MQTT → FastAPI) | 🟠 Consolidate |
| Cloud sync implemented | ❌ No | ✅ Background worker | 🟡 Implement |
| Model input validation | ⚠️ Hash verified | ✅ Feature schema validated | 🟡 Add |

---

## 🎓 GOLDEN PRINCIPLE

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  EVERY PREDICTION MUST HAVE AN HONEST SOURCE                │
│                                                              │
│  • Real sensor ✅                                             │
│  • Real API (weather, soil test) ✅                          │
│  • Validated & error-bounded ✅                              │
│                                                              │
│  OR                                                           │
│                                                              │
│  • INSUFFICIENT_DATA (no fabrication) ✅                     │
│                                                              │
│  NEVER:                                                       │
│  • Synthetic defaults (45%, 28°C, 90% humidity) ❌            │
│  • Hope the missing sensor magically appears ❌               │
│  • Silently fail with wrong feature counts ❌                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## NEXT STEPS

1. **Confirm Remediation Scope:** Which phases should be prioritized?
2. **Model Decision:** Should crop recommendation fallback to weather-only model, or return INSUFFICIENT_DATA?
3. **Timeline:** Estimate effort per phase.
4. **Ownership:** Which components do you want to refactor yourself vs. have the agent handle?

---

**Prepared by:** Kiro (Architecture Audit)  
**Confidence Level:** High (all findings backed by code inspection)  
**Risk Level:** 🔴 Critical — AI output reliability is compromised by synthetic defaults

