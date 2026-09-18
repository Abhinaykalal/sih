# AgriSaathi Architecture Remediation Plan

## Overview

This document outlines the concrete, actionable steps to fix the critical architectural misalignments identified in the audit.

---

## PHASE 1: ELIMINATE SYNTHETIC DEFAULTS (🔴 CRITICAL)

### Task 1.1: Fix risk_engine.py Synthetic Defaults

**File:** `mlbackend/risk_engine.py`

**Current Code (BROKEN):**
```python
def compute_4zone_farm_status(sensor_data: Dict[str, Any]) -> Dict[str, Any]:
    z1_moisture_raw = sensor_data.get("z1_moisture")
    z2_moisture_raw = sensor_data.get("z2_moisture")
    
    z1_moisture = float(z1_moisture_raw) if z1_moisture_raw is not None else None
    z2_moisture = float(z2_moisture_raw) if z2_moisture_raw is not None else None
```

✅ Already correct — preserves None.

**BUT PROBLEM FOUND ELSEWHERE:**

The issue is in how the function is **called** from main.py. Need to verify the calling code doesn't pass defaults.

**Action Items:**
1. Search all calls to `compute_4zone_farm_status()` in `main.py` and other files.
2. Ensure no defaults are passed in `sensor_data` dict before calling.
3. If function receives a None sensor, it should return a result with that sensor marked as `DATA_UNAVAILABLE`.

**Files to audit:**
- `mlbackend/main.py` (look for POST endpoints that call risk engine)
- `mlbackend/agent_orchestrator.py`
- Any other service calling risk_engine functions

---

### Task 1.2: Fix model_providers.py Sensor Defaults

**File:** `mlbackend/model_providers.py`

**Current Code (GOOD):**
```python
def assess_irrigation_needs(
    self,
    soil_moisture: Optional[float],
    ...
):
    # Check required inputs
    if soil_moisture is None:
        inputs_missing.append("soil_moisture")
        return IrrigationAssessmentResult(
            irrigation_needed=False,
            recommendation_text="Decision unavailable — required inputs are missing",
            ...
        )
```

✅ **Already correct** — returns UNAVAILABLE when soil moisture is None.

**BUT verify:**
1. All callers of `assess_irrigation_needs()` pass real sensor values or None (not synthetic defaults).
2. Same pattern applied to all other model providers (nutrient, pest, yield, etc.).

---

### Task 1.3: Remove HTTP Direct Sensor Path from Frontend

**File:** `src/lib/sensorService.ts`

**Current Code (BROKEN):**
```typescript
export async function fetchSensorData(ip: string, retries = 2): Promise<SensorReadingResult> {
  const url = `http://${cleanIp}/sensors`;  // ← DIRECT HTTP TO ESP32
  
  // Fallback defaults:
  const soil_moisture = Number(json.soil_moisture ?? json.z2_moisture ?? 40);
  const temperature = Number(json.temperature ?? json.air_temp ?? 28);
  const humidity = Number(json.humidity ?? json.z4_humidity ?? 65);
  const light = Number(json.light ?? 8000);
```

**Issues:**
1. ❌ Direct HTTP to ESP32 (bypasses MQTT validation).
2. ❌ Fallback defaults (40%, 28°C, 65%, 8000 lux).
3. ❌ No input validation (accepts 999% humidity, etc.).

**Action Items:**

1. **Delete the HTTP direct path** entirely.
2. **Replace with FastAPI call:**
   ```typescript
   const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
   
   export async function fetchSensorData(): Promise<SensorReadingResult> {
     try {
       const res = await fetch(`${BACKEND_URL}/api/telemetry/latest`, {
         signal: AbortSignal.timeout(3000)
       });
       
       if (!res.ok) throw new Error(`HTTP ${res.status}`);
       
       const telemetry = await res.json();
       
       // No defaults. If missing, return error.
       if (telemetry.error || telemetry.data_source === "UNAVAILABLE") {
         return {
           success: false,
           error: {
             code: "SENSOR_UNAVAILABLE",
             message: telemetry.message || "Live sensor data not available"
           }
         };
       }
       
       return { success: true, data: telemetry };
     } catch (err) {
       return {
         success: false,
         error: { code: "NETWORK_ERROR", message: err.message }
       };
     }
   }
   ```

3. **Create FastAPI endpoint** `/api/telemetry/latest`:
   ```python
   @app.get("/api/telemetry/latest")
   def get_latest_telemetry():
       """Returns the latest validated telemetry or UNAVAILABLE."""
       latest = db_layer.get_latest_telemetry(device_id="ESP32_NODE_01")
       
       if not latest:
           return {
               "error": True,
               "data_source": "UNAVAILABLE",
               "message": "No telemetry received from device yet"
           }
       
       return {
           "error": False,
           "data": latest,
           "data_source": "MQTT_VALIDATED",
           "timestamp": datetime.now(timezone.utc).isoformat()
       }
   ```

4. **Update all frontend components** that use `sensorService.ts`:
   - Find all imports: `grep -r "fetchSensorData" src/`
   - Audit each call site to ensure no fallback defaults are applied client-side.

5. **Remove HTTP `/sensors` endpoint from ESP32** (if it exists):
   - Search `esp32_sensor_node.ino` for `server.on("/sensors"...)` handler.
   - If present, delete it (to prevent accidental use).

**Files to modify:**
- `src/lib/sensorService.ts` (delete HTTP direct, add FastAPI call)
- `mlbackend/main.py` (add `/api/telemetry/latest` endpoint)
- All files importing sensorService.ts (audit for defaults)
- `esp32_sensor_node.ino` (remove HTTP endpoint if present)

---

## PHASE 2: DEFINE FEATURE CONTRACT FOR CROP MODEL (🟠 HIGH)

### Task 2.1: Document Current Crop Model Feature Requirements

**File:** `mlbackend/training/train_crop_recommendation.py` (or wherever training is)

**Action Items:**
1. Verify exact feature names and order expected by the trained model.
2. Create a schema document:
   ```python
   # FEATURE SPECIFICATION FOR CROP RECOMMENDATION MODEL
   # Model file: mlbackend/model.joblib
   # Features (in order):
   # [0] N - Nitrogen (mg/kg), range 0-300
   # [1] P - Phosphorus (mg/kg), range 0-300
   # [2] K - Potassium (mg/kg), range 0-300
   # [3] temperature - Air temperature (°C), range -10 to 60
   # [4] humidity - Relative humidity (%), range 0-100
   # [5] ph - Soil pH, range 0-14
   # [6] rainfall - Annual rainfall (mm), range 0-5000
   ```

3. Document data sources:
   - **N, P, K:** Soil sensor (NOT CONNECTED) or soil test lab (manual upload)
   - **temperature:** DHT22 (CONNECTED, from ESP32)
   - **humidity:** DHT22 (CONNECTED, from ESP32)
   - **pH:** Sensor (NOT CONNECTED) or soil test lab (manual upload)
   - **rainfall:** Weather API (OpenWeatherMap, not from sensor)

---

### Task 2.2: Decide on Fallback Strategy

**Three Options:**

#### Option A: Train a Reduced Model (Recommended for Speed)

**Scope:** Train a new crop recommendation model using only available features:
- temperature (from ESP32 ✅)
- humidity (from ESP32 ✅)
- rainfall (from weather API ✅)

**Pros:**
- Works with current hardware.
- Still produces meaningful recommendations.
- Can ship immediately.

**Cons:**
- Requires retraining on new feature set.
- Lower accuracy than 7-feature model.
- Need to evaluate on new feature space.

**Effort:** ~2–4 hours (if dataset is available and labeled).

---

#### Option B: Return INSUFFICIENT_DATA

**Scope:** Keep existing 7-feature model; require all features for inference.

**Logic:**
```python
@app.post("/api/recommend/crop")
def recommend_crop(features: CropFeatures):
    # Check: do we have N, P, K?
    if features.N is None or features.P is None or features.K is None:
        return {
            "recommended_crop": None,
            "status": "INSUFFICIENT_DATA",
            "message": "NPK soil nutrients required. Conduct a soil test or connect NPK sensor hardware.",
            "alternative": "Use weather-based crop advisory instead."
        }
    
    # Proceed with inference
    prediction = model.predict(...)
```

**Pros:**
- No retraining needed.
- Honest — doesn't guess.

**Cons:**
- Blocks crop recommendations until manual soil test uploaded.
- Poor UX.

**Effort:** ~1 hour.

---

#### Option C: Hybrid Approach (Recommended for Robustness)

**Scope:** Train lightweight model on [temperature, humidity, rainfall]; keep existing model for advanced use.

**Logic:**
```python
# If N, P, K available: use full 7-feature model
# Else: use reduced 3-feature model

@app.post("/api/recommend/crop")
def recommend_crop(features: CropFeatures):
    npk_available = all([features.N is not None, features.P is not None, features.K is not None])
    
    if npk_available:
        # Full model
        prediction = full_model.predict([features.N, features.P, features.K, features.temperature, features.humidity, features.ph, features.rainfall])
        model_used = "full_7_feature"
    else:
        # Fallback model
        prediction = reduced_model.predict([features.temperature, features.humidity, features.rainfall])
        model_used = "reduced_3_feature_fallback"
    
    return {
        "recommended_crop": prediction,
        "model_used": model_used,
        "confidence": ...
    }
```

**Pros:**
- Works with current hardware immediately.
- Upgrades gracefully when NPK added.
- Better UX than INSUFFICIENT_DATA.

**Cons:**
- Requires training/maintaining 2 models.
- More complex logic.

**Effort:** ~3–5 hours.

---

**Recommendation:** **Option A (new 3-feature model)** because:
1. Fastest to implement.
2. Honest about data sources.
3. Works with current hardware.
4. Can always upgrade later.

---

### Task 2.3: Implement Chosen Strategy

**If Option A (new model):**

1. Create training script: `mlbackend/training/train_crop_recommendation_reduced.py`
   ```python
   # Features: temperature, humidity, rainfall
   # Dataset: filter existing data or synthetic data
   # Output: reduced_crop_model.joblib
   ```

2. Train and evaluate on test set.

3. Update `/api/recommend/crop` endpoint:
   ```python
   # Load reduced model instead of full model
   if ML_AVAILABLE:
       try:
           reduced_model = joblib.load("reduced_crop_model.joblib")
       except:
           pass
   ```

4. Document in `models/crop_recommendation/metadata.json`:
   ```json
   {
     "model_type": "crop_recommendation",
     "version": "3_feature_temperature_humidity_rainfall",
     "features": ["temperature_c", "humidity_pct", "rainfall_mm"],
     "training_date": "2026-09-17",
     "accuracy": 0.87,
     "note": "Reduced model for hardware with only DHT22 + weather API"
   }
   ```

5. Update model loading in `main.py` to point to new model.

**Files to create/modify:**
- `mlbackend/training/train_crop_recommendation_reduced.py` (new)
- `mlbackend/reduced_crop_model.joblib` (new artifact)
- `mlbackend/main.py` (update model path)
- `models/crop_recommendation/metadata.json` (update spec)

**Effort:** ~3–4 hours.

---

## PHASE 3: UNIFY SENSOR DATA PATH (🟠 HIGH)

### Task 3.1: Create Unified Telemetry API Endpoint

**File:** `mlbackend/main.py`

**Endpoint to create:** `GET /api/telemetry/latest`

```python
@app.get("/api/telemetry/latest")
def get_latest_telemetry(device_id: str = "ESP32_NODE_01"):
    """
    Returns the latest canonical telemetry from SQLite.
    Single source of truth for all frontend/mobile consumers.
    """
    latest = db_layer.get_latest_telemetry(device_id=device_id)
    
    if not latest or latest.get("data_source") == "UNAVAILABLE":
        raise HTTPException(
            status_code=503,
            detail={
                "error": "SENSOR_UNAVAILABLE",
                "message": f"No recent telemetry from {device_id}",
                "last_data_age_seconds": 3600  # if we track this
            }
        )
    
    # Add metadata
    return {
        "device_id": device_id,
        "telemetry": latest,
        "data_source": "MQTT_VALIDATED",
        "received_at": latest.get("received_at"),
        "received_age_seconds": calculate_age(latest.get("received_at")),
        "is_stale": calculate_age(latest.get("received_at")) > 600  # > 10 min
    }
```

**Also create:** `GET /api/telemetry/history`

```python
@app.get("/api/telemetry/history")
def get_telemetry_history(device_id: str = "ESP32_NODE_01", limit: int = 50):
    """Returns recent telemetry readings in descending timestamp order."""
    history = db_layer.get_telemetry_history(device_id=device_id, limit=limit)
    return {
        "device_id": device_id,
        "records": history,
        "count": len(history),
        "data_source": "MQTT_VALIDATED"
    }
```

**Files to modify:**
- `mlbackend/main.py` (add endpoints)

**Effort:** ~1 hour.

---

### Task 3.2: Update Frontend to Use Unified Endpoint

**Files to modify:**
- `src/lib/sensorService.ts` (already covered in Task 1.3)
- `src/components/IoTDashboardModule.tsx` (update to call `/api/telemetry/latest`)
- `src/components/CropRecommendationModule.tsx` (update to use centralized API)
- `src/app/page.tsx` (audit all sensor references)

**Pattern:**
```typescript
// OLD (BROKEN):
const result = await fetchSensorData(esp32Ip);

// NEW (CORRECT):
const result = await fetch(`/api/telemetry/latest`).then(r => r.json());
if (result.is_stale) {
    showWarning("Sensor data is older than 10 minutes");
}
```

**Effort:** ~2–3 hours.

---

### Task 3.3: Remove ESP32 HTTP /sensors Endpoint (If Exists)

**File:** `edge_hardware/esp32_sensor_node.ino`

**Search for:**
```cpp
server.on("/sensors", HTTP_GET, [](AsyncWebServerRequest *request){
```

**If found:** Delete the entire handler.

**Rationale:** Prevent accidental use of unvalidated HTTP path.

**Effort:** ~30 minutes.

---

## PHASE 4: IMPLEMENT CLOUD SYNC WORKER (🟡 MEDIUM)

### Task 4.1: Design Background Worker

**File:** `mlbackend/cloud_sync_worker.py` (new)

**Scope:**
- Reads from `canonical_sync_queue` (SQLite).
- Pushes to Supabase (cloud).
- Idempotency: uses `client_action_id` to prevent duplicates.
- Retry logic: exponential backoff.
- Status: marks `sync_status = "SYNCED"` when successful.

**Pseudocode:**
```python
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List

class CloudSyncWorker:
    def __init__(self, supabase_client, db_layer, max_retries=5):
        self.supabase = supabase_client
        self.db = db_layer
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)

    async def sync_pending_events(self):
        """Main loop: fetches pending events and pushes to cloud."""
        while True:
            try:
                pending = self.db.get_pending_sync_events()
                
                for event in pending:
                    await self.sync_single_event(event)
                
                # Sleep before next poll
                await asyncio.sleep(30)
            
            except Exception as e:
                self.logger.error(f"Sync worker error: {e}")
                await asyncio.sleep(60)

    async def sync_single_event(self, event):
        """Push a single event to Supabase with retry."""
        sync_id = event["sync_id"]
        payload = event["payload"]
        
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # Push to Supabase
                self.supabase.table("canonical_telemetry").insert(payload).execute()
                
                # Mark as synced
                self.db.mark_events_synced([sync_id])
                self.logger.info(f"Synced event {sync_id}")
                return
            
            except Exception as e:
                retry_count += 1
                wait_time = min(60, 2 ** retry_count)  # Exponential backoff
                self.logger.warning(f"Sync failed for {sync_id}, retry {retry_count}/{self.max_retries} in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

# Start worker as background task
worker = CloudSyncWorker(supabase_client, db_layer)

@app.on_event("startup")
async def start_sync_worker():
    asyncio.create_task(worker.sync_pending_events())
```

**Effort:** ~3–4 hours.

---

### Task 4.2: Add Supabase Schema Migration

**File:** `supabase/migrations/20260917_cloud_sync_schema.sql` (new)

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS cloud_telemetry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    soil_moisture_pct FLOAT,
    temperature_c FLOAT,
    humidity_pct FLOAT,
    nitrogen FLOAT,
    phosphorus FLOAT,
    potassium FLOAT,
    pump_active BOOLEAN,
    raw_payload JSONB,
    data_source TEXT,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(device_id, received_at)
);

CREATE INDEX IF NOT EXISTS idx_cloud_telemetry_device_time
    ON cloud_telemetry(device_id, received_at DESC);
```

**Effort:** ~1 hour.

---

## PHASE 5: ADD INPUT VALIDATION TO MODEL ENDPOINTS (🟡 MEDIUM)

### Task 5.1: Create Model Feature Validator

**File:** `mlbackend/model_validation.py` (new)

```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class CropRecommendationFeatures(BaseModel):
    """Enforces exact feature contract for crop recommendation model."""
    
    # For 3-feature reduced model:
    temperature: float = Field(..., ge=-10.0, le=60.0)
    humidity: float = Field(..., ge=0.0, le=100.0)
    rainfall: float = Field(..., ge=0.0, le=5000.0)
    
    # Optional: for future 7-feature model
    nitrogen: Optional[float] = Field(None, ge=0.0, le=300.0)
    phosphorus: Optional[float] = Field(None, ge=0.0, le=300.0)
    potassium: Optional[float] = Field(None, ge=0.0, le=300.0)
    ph: Optional[float] = Field(None, ge=0.0, le=14.0)
    
    @validator('temperature', 'humidity', 'rainfall', pre=True)
    def validate_required_features(cls, v):
        if v is None:
            raise ValueError("Required feature is missing")
        return v

class ModelInputContract:
    """Registry of model feature requirements."""
    
    @staticmethod
    def validate_for_model(model_name: str, features: dict) -> bool:
        """Ensures features match model's expected schema."""
        if model_name == "crop_recommendation_3feature":
            required = ["temperature", "humidity", "rainfall"]
            return all(k in features and features[k] is not None for k in required)
        
        elif model_name == "crop_recommendation_7feature":
            required = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
            return all(k in features and features[k] is not None for k in required)
        
        else:
            raise ValueError(f"Unknown model: {model_name}")
```

**Effort:** ~1.5 hours.

---

### Task 5.2: Update Crop Recommendation Endpoint

**File:** `mlbackend/main.py`

**Current code:**
```python
@app.post("/api/recommend/crop")
def recommend_crop(features: CropFeatures):
    # ... load model ...
    data = np.array([[features.N, features.P, features.K, ...]])
    prediction = model.predict(data)
```

**Updated code:**
```python
from model_validation import CropRecommendationFeatures, ModelInputContract

@app.post("/api/recommend/crop")
def recommend_crop(features: CropRecommendationFeatures):
    """
    Recommends best crop based on validated soil & climate features.
    Enforces exact feature contract; rejects requests with missing data.
    """
    
    # Validate features match model requirements
    if not ModelInputContract.validate_for_model("crop_recommendation_3feature", features.dict()):
        return RecommendationResponse(
            recommended_crop="Unavailable",
            confidence=0.0,
            prediction_confidence=0.0,
            provenance="VALIDATION_FAILED",
            explanation="Required features missing (temperature, humidity, rainfall)",
            warnings=["Cannot generate prediction with incomplete feature vector"]
        )
    
    # Proceed with inference
    data = np.array([[features.temperature, features.humidity, features.rainfall]])
    prediction = model.predict(data)
    
    return RecommendationResponse(...)
```

**Effort:** ~1 hour.

---

## IMPLEMENTATION PRIORITY & TIMELINE

### Suggested Order:

1. **PHASE 1 (Immediate):** Eliminate synthetic defaults
   - Task 1.1, 1.2: ~1 hour (audit + fix)
   - Task 1.3: ~2–3 hours (delete HTTP direct, create FastAPI endpoint)
   - **Subtotal:** ~4 hours

2. **PHASE 2 (Critical path):** Define crop model feature contract
   - Task 2.1, 2.2: ~1 hour (analysis)
   - Task 2.3: ~3–4 hours (train or fallback)
   - **Subtotal:** ~4–5 hours

3. **PHASE 3 (Execution):** Unify sensor data path
   - Task 3.1, 3.2, 3.3: ~3–4 hours (endpoints + frontend updates)
   - **Subtotal:** ~3–4 hours

4. **PHASE 4 (Optional):** Cloud sync worker
   - Task 4.1, 4.2: ~4–5 hours
   - **Subtotal:** ~4–5 hours

5. **PHASE 5 (Polish):** Input validation
   - Task 5.1, 5.2: ~2.5 hours
   - **Subtotal:** ~2.5 hours

**Total Estimated Effort:**
- **Must-have (Phases 1–3):** ~12–15 hours
- **Nice-to-have (Phases 4–5):** ~7–10 hours
- **Grand Total:** ~19–25 hours

---

## TESTING STRATEGY

### Unit Tests to Add:

1. **Test: Synthetic defaults are never applied**
   ```python
   def test_risk_engine_no_synthetic_defaults():
       """Ensure risk engine returns DATA_UNAVAILABLE when sensor is missing."""
       result = compute_4zone_farm_status({"z2_moisture": None})
       assert result["zones"]["zone_2"]["status"] == "DATA_UNAVAILABLE"
   ```

2. **Test: Model validation rejects incomplete features**
   ```python
   def test_crop_model_rejects_incomplete_features():
       features = CropRecommendationFeatures(temperature=28, humidity=65, rainfall=None)
       with pytest.raises(ValueError):
           # Should fail validation
           pass
   ```

3. **Test: Frontend only uses API endpoint, never HTTP direct**
   ```typescript
   test("fetchSensorData calls /api/telemetry/latest, never direct HTTP", async () => {
     const mockFetch = jest.fn(() => Promise.resolve({
       ok: true,
       json: () => Promise.resolve({ telemetry: {...} })
     }));
     
     await fetchSensorData();
     
     expect(mockFetch).toHaveBeenCalledWith("/api/telemetry/latest");
     expect(mockFetch).not.toHaveBeenCalledWith(expect.stringMatching(/http:\/\/.*\/sensors/));
   });
   ```

---

## ROLLOUT CHECKLIST

- [ ] Phase 1 implemented & tested
- [ ] Phase 2 model decision finalized & artifact deployed
- [ ] Phase 3 unified endpoint live, frontend updated
- [ ] Phase 4 cloud sync worker running (or deferred)
- [ ] Phase 5 validation in place
- [ ] All integration tests passing
- [ ] Staging deployment successful
- [ ] Farmer UAT on real device
- [ ] Production rollout

---

**Document Owner:** Kiro  
**Last Updated:** 2026-09-17  
**Status:** Ready for Implementation

