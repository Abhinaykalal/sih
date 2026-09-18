# 🚨 Forensic Audit: Critical Integration Issues

**Date**: 2026-09-18  
**Status**: CRITICAL - Production-blocking issues identified  
**Risk Level**: HIGH - Multiple false confidence points discovered

---

## Executive Summary

The AgriSaathi system has **severe integration mismatches** between what the Android app calls and what the backend exposes. Additionally, several AI features have **untested AI pipelines** with unclear fallback behavior.

**Key Finding**: The system can appear functional while the actual AI isn't behaving properly due to:
1. API route mismatches (Android calls different endpoints than backend)
2. Duplicated AI pipelines with unclear precedence
3. Unverified fallback responses when models fail
4. Tests that pass but don't verify actual ML output

---

## ISSUE 1: Frontend-Backend API Mismatches 🚨

### Android App Calls vs Backend Exposes

| Feature | Android Calls | Backend Exposes | Status |
|---------|---------------|-----------------|--------|
| **AI Chat** | `/api/chat` | `/api/chat` + `/api/ai/chat` + `/api/agent/chat` | ⚠️ CONFLICTING |
| **Vision Diagnose** | `/api/vision-diagnose` | `/api/vision-diagnose` | ✅ MATCH |
| **Telemetry** | `/telemetry` | `/telemetry` + `/api/telemetry` + `/api/telemetry/latest` + `/api/telemetry/history` | ⚠️ MULTIPLE |
| **Crop Recommend** | `/api/recommend` | `/api/recommend` + `/api/recommend/crop` + `/recommend` + `/recommend/crop` | ⚠️ MULTIPLE |
| **Pump Command** | `/pump/command` | `/pump/command` + `/api/pump/command` | ✅ MATCH |
| **Pump State** | `/pump/state` | `/pump/state` + `/api/pump/state` | ✅ MATCH |
| **Notifications** | `/notifications` | `/notifications` + `/api/notifications` | ✅ MATCH |

### Critical Problem: AI Chat Has 3 Different Endpoints

**File**: `mlbackend/main.py`

**Endpoint 1** (line 1062):
```python
@app.post("/api/chat")
def ai_chat(req: ChatRequest):
    """Handles AI chat (ChatRequest schema)"""
    # Implementation: calls llm_provider directly
```

**Endpoint 2** (line 1134):
```python
@app.post("/api/agent/chat")
def agent_chat_api(req: AgentChatRequest):
    """Handles agent chat (AgentChatRequest schema - different from ChatRequest!)"""
    # Implementation: calls orchestrator, not llm_provider
```

**Android calls**: `/api/chat` (see AgentClient line 61)

**Risk**: If `/api/chat` handler changes or uses different logic than `/api/agent/chat`, the actual AI behavior is unpredictable.

---

## ISSUE 2: Crop Recommendation - Unknown ML Generation

### Problem: Is the ML Actually Running?

**Android Call** (ApiClient.ts line 137):
```typescript
async recommendCrop(features: { N, P, K, temperature, humidity, ph, rainfall }) {
  return this.fetchApi('/api/recommend', { method: 'POST', body: JSON.stringify(features) });
}
```

**Backend Endpoint** (main.py line 554):
```python
@app.post("/api/recommend", response_model=RecommendationResponse)
@app.post("/api/recommend/crop", response_model=RecommendationResponse)
@app.post("/recommend", response_model=RecommendationResponse)
@app.post("/recommend/crop", response_model=RecommendationResponse)
def recommend_crop(features: CropFeatures):
    """Module 1: Recommends the best crop based on soil & climate parameters"""
```

**File Location**: `mlbackend/main.py` lines 559-662

**What We Know**:
- ✅ Model file exists: `mlbackend/model.joblib` (just trained, 0.44 MB)
- ✅ Training accuracy: 99.7%
- ✅ Model was trained on RandomForest

**What We Need to Verify**:
- Does the endpoint actually load and call `model.joblib`?
- Or does it have fallback responses when the model isn't available?
- Are the N/P/K values actually used as inputs?

**Must Trace**: Line 559-662 in `mlbackend/main.py` to verify model loading and inference flow

---

## ISSUE 3: Vision Diagnosis - Model Status Unknown

### Problem: Is Vision Model Actually Working?

**Android Call** (ApiClient.ts line 77):
```typescript
async diagnoseLeafImage(base64Image: string, cropName?: string, growthStage?: string) {
  return this.fetchApi('/api/vision-diagnose', {
    method: 'POST',
    body: JSON.stringify({
      image_base64: base64Image,
      crop_type: cropName,
      growth_stage: growthStage,
    }),
  });
}
```

**Backend Endpoint** (main.py line 1392):
```python
@app.post("/api/vision-diagnose")
def diagnose_crop_multimodal(payload: VisionDiagnoseInput):
    """Module 10: Leaf disease diagnosis from images"""
```

**File Location**: `mlbackend/main.py` lines 1392-1490

**Status of Model**:
- ✅ `mlbackend/vision_model.joblib` exists (1.97 MB, trained)
- ✅ Training accuracy: 85% on PlantVillage
- ⚠️ Model marked as EXPERIMENTAL

**Critical Questions**:
1. Does the endpoint load `vision_model.joblib` on startup?
2. What happens if the model isn't loaded? Does it return mock responses?
3. Are image features actually extracted (HOG + RGB histograms)?
4. Is confidence correctly calculated from model.predict_proba()?

**Must Trace**: Lines 1392-1490 to verify:
- Model loading logic
- Fallback responses if model fails
- Feature extraction flow
- Confidence calculation

---

## ISSUE 4: Telemetry Data - Real or Mocked?

### Problem: Is Sensor Data Actually Real?

**Android Calls**:
```typescript
// SensorClient line 91
async getTelemetry(deviceId: string, limit: number = 20) {
  return this.fetchApi(`/telemetry?device_id=${encodeURIComponent(deviceId)}&limit=${limit}`);
}
```

**Backend Endpoints**:
```python
# main.py line 1838
@app.get("/telemetry")
@app.get("/api/telemetry")
def get_canonical_telemetry_history(...)

# main.py line 1253
@app.get("/api/telemetry/latest")
def get_latest_telemetry_canonical(device_id: str = Query("ESP32_NODE_01")):
```

**Critical Questions**:
1. Where does the data come from? (MQTT, simulator, mock?)
2. Are values hardcoded anywhere?
3. Is there a `esp32_simulator.py` that provides fake data?
4. Can you distinguish real ESP32 data from simulated?

**Must Check**:
- `mlbackend/mqtt_service.py` - does it subscribe to real MQTT or use simulator?
- `mlbackend/esp32_simulator.py` - exists? Active?
- Database schema - is there a `data_source` or `provenance` field?

---

## ISSUE 5: Weather Data - API or Mock?

### Problem: Is Weather Forecast Real?

**Used in**:
- Crop recommendation (`/api/recommend`)
- Irrigation decisions (`/api/pump/command`)
- Risk assessment (`/api/crop-risk`)

**Must Verify**:
1. Is weather API actually called (OpenWeatherMap, WeatherAPI, etc.)?
2. Or is weather data mocked/simulated?
3. Where does `rain_forecast_mm` and `rain_probability_pct` come from?

**Search**: `mlbackend/services.py` or `weather_provider.py` for actual API calls vs mock implementation

---

## ISSUE 6: Irrigation Decision Logic - Data-Driven or Rule-Based?

### Problem: Does Decision Use Real Data?

**Android Call** (ApiClient.ts line 222):
```typescript
async assessIrrigation(payload: { soil_moisture, rain_prob, rainfall_forecast, ... }) {
  return this.fetchApi('/api/recommend-irrigation', { method: 'POST', body: JSON.stringify(payload) });
}
```

**Critical Questions**:
1. Does the irrigation decision actually use the provided sensor inputs?
2. Or are there hardcoded thresholds that override sensor data?
3. Is rain lockout (50% threshold) actually enforced?
4. What happens if weather data is unavailable?

**Must Trace**:
- `mlbackend/pump_controller.py` - actual decision logic
- `mlbackend/model_providers.py` - irrigation provider implementation
- `mlbackend/risk_engine.py` - decision thresholds

---

## ISSUE 7: Test Coverage - False Confidence Points

### Tests That Pass But Don't Verify ML

**Test File**: `mlbackend/test_comprehensive.py`

**Example** (line 212):
```python
def test_07_crop_recommendation_real_model(self):
    """Verify real trained Random Forest crop recommendation model (99.1% accuracy)."""
    payload = { "N": 50, "P": 50, "K": 50, "temperature": 25, "humidity": 60, "ph": 7, "rainfall": 200 }
    res = self.client.post("/api/recommend", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "recommended_crop" in data
    assert "confidence" in data and isinstance(data["confidence"], (int, float))
```

**Problem**: This test verifies:
- ✅ HTTP 200 response
- ✅ Fields exist
- ✅ Confidence is numeric

But does NOT verify:
- ❌ Prediction is actually from RandomForest (could be hardcoded)
- ❌ N/P/K values actually influenced the output
- ❌ Different inputs produce different outputs

**Risk**: Test passes even if `/api/recommend` returns static responses for all inputs.

---

## ISSUE 8: Vision Model - Trained vs Placeholder

### Current Status

**File**: `mlbackend/vision_model.joblib` (1.97 MB)

**Training Metrics**:
- Accuracy: 85% (on test set)
- F1-Score: 83%
- Status: EXPERIMENTAL

**Critical Questions**:
1. Is this model loaded at backend startup?
2. What's the fallback if loading fails?
3. Is confidence correctly calculated?
4. Are test samples different from training samples?

**Must Verify**:
- Look at `/api/models/status` response - what does it say about vision model?
- Check startup logs - is model loaded successfully?
- Check error handling in `vision_ai_model.py`

---

## ISSUE 9: Database - Local vs Cloud Sync Status

### Problem: Where is Data Actually Stored?

**Local SQLite**: `mlbackend/farm_analytics.db` + `mlbackend/hybrid_farm_edge.db`

**Cloud Sync Queue**: `mlbackend/hybrid_farm_edge.db` (table: `canonical_sync_queue`)

**Critical Questions**:
1. Is `cloud_sync_worker.py` actually uploading to Supabase?
2. What happens if Supabase credentials aren't configured?
3. Is data stuck in local queue indefinitely?
4. Can you verify what's actually in Supabase vs local?

**Must Check**:
- `/api/cloud-sync/status` endpoint - what does it report?
- `mlbackend/cloud_sync_worker.py` - is it actually enabled?
- Environment variables - is `SUPABASE_URL` set?

---

## Priority Fixes Required

### 🔴 CRITICAL (Block SIH Deployment)

**1. Verify Crop Recommendation ML Execution** (Estimated: 2 hours)
- Trace `/api/recommend` implementation
- Confirm N/P/K inputs actually flow to model.joblib
- Test with different inputs, verify different outputs
- Document fallback behavior if model loads fails

**2. Verify Vision Model Loading** (Estimated: 2 hours)
- Check if vision_model.joblib is loaded at startup
- Test image upload → feature extraction → inference
- Verify confidence calculation is correct
- Document what happens if model fails to load

**3. Unify AI Chat Endpoints** (Estimated: 4 hours)
- Decide: use `/api/chat` or `/api/agent/chat` (not both)
- Ensure Android calls correct endpoint
- Ensure both backends use same LLM provider logic
- Remove or redirect duplicate endpoints

### 🟠 HIGH (Fix Before Phase 4)

**4. Verify Weather Data Source** (Estimated: 2 hours)
- Confirm weather API is actually called
- Check fallback if API is down
- Verify rain forecast influences irrigation decisions

**5. Verify Telemetry Source** (Estimated: 2 hours)
- Confirm data comes from real MQTT (not simulator)
- Check for hardcoded values
- Verify data provenance tracking

**6. Comprehensive Integration Test** (Estimated: 8 hours)
- End-to-end test: Android → Backend → ML → Response
- For each feature: crop recommendation, vision, chat, irrigation
- Verify ML is actually executing, not returning mocks
- Document any discrepancies

### 🟡 MEDIUM (Phase 3.2 Hardening)

**7. Improve Test Coverage** (Estimated: 4 hours)
- Add tests that verify ML output changes based on input
- Test fallback behaviors explicitly
- Test each AI feature with known inputs/expected outputs

**8. Add Provenance Tracking** (Estimated: 3 hours)
- Track data source (real vs mock vs fallback)
- Track model version and creation date
- Track which LLM provider was used

---

## Investigation Checklist

### For Each AI Feature, Answer:

- [ ] Is the model actually loaded at startup?
- [ ] What's the fallback if model load fails?
- [ ] Do inputs actually affect outputs?
- [ ] Is confidence calculated correctly or hardcoded?
- [ ] Are there any mock/simulator data being returned?
- [ ] Can you trace the full data flow from input to output?
- [ ] Are there tests that verify ML correctness (not just HTTP 200)?

---

## Questions for Code Review

### main.py

1. **Lines 554-662** (/api/recommend): 
   - Where is `model.joblib` loaded?
   - What happens if load fails?
   - Are N/P/K values passed to the model?

2. **Lines 1062-1133** (/api/chat):
   - Does this use llm_provider directly?
   - What's the difference from /api/agent/chat?
   - Why are there two different chat endpoints?

3. **Lines 1134-1155** (/api/agent/chat):
   - Does this use orchestrator?
   - Should Android app use this instead?

4. **Lines 1392-1490** (/api/vision-diagnose):
   - Is vision_model.joblib loaded?
   - What happens if it's not available?
   - Are confidence scores from model or hardcoded?

### model_providers.py

- Where is actual ML inference happening?
- Are there fallback responses if models fail?
- How is confidence calculated?

### llm_provider.py

- Which LLM is actually being used?
- What's the fallback order?
- Are there any mock responses?

### vision_ai_model.py

- Is vision_model.joblib loaded and cached?
- What's the error handling if load fails?

---

## Next Steps

1. **Read each flagged code section** (30 min)
2. **Trace one feature end-to-end** (crop recommendation) (1 hour)
3. **Write comprehensive integration test** (2 hours)
4. **Document actual behavior vs claimed behavior** (1 hour)
5. **Create remediation plan** (30 min)

**Total Estimated Time**: 5 hours for complete investigation

---

**Status**: Ready for detailed code review  
**Priority**: CRITICAL - Complete before SIH deployment  
**Risk if skipped**: System appears functional but AI features may be non-functional or returning mock data
