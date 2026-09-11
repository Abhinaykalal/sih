# AgriSaathi AI — Repository Cleanup Report

**Date**: 2026-09-11  
**Branch**: `cleanup-scope-enforcement`  
**Auditor**: Antigravity Scope Enforcement & Automated Verification  
**Target**: Full Repository (`agrisaathi-sih`)  
**Deployment Target**: Render (`https://agrisaathi-6dg1.onrender.com`)

---

## 1. Summary of Actions Taken

This cleanup eliminated all demo fallbacks, hardcoded sensor simulations, obsolete web prototypes, residual Twilio references, and duplicate/mock endpoints. The repository is now strictly aligned with the canonical AgriSaathi AI scope.

### Action Totals
* **Files Retained**: 142
* **Files Modified & Refactored**: 14
* **Files Archived**: 2 (`archive/aiInferenceService.ts`, `archive/railway.toml`)
* **Files Deleted**: 11 (Unused media/video files in `public/`, `vercel.json`)
* **Test Suites Run**: 4 suites (93/93 tests passing: 44 Integration, 42 Comprehensive Master, 7 Phase-4)
* **TypeScript Errors in Android App**: **0 Errors** (`npx tsc --noEmit`)

---

## 2. Inventory of Changes by Category

### A. Old UI/UX & Obsolete Web Files
* **Archived**:
  - `src/lib/aiInferenceService.ts` → Moved to `archive/aiInferenceService.ts`. Unused legacy rule engine containing hardcoded disease labels (`Tomato Early Blight Fungal Spot`, fake confidence `0.91`, `Downy Mildew`, `0.88`).
* **Deleted**:
  - `public/VIDEO1.mp4`, `public/VIDEO2.mp4`, `public/animation.mp4`: Massive unlinked video assets.
  - `public/farmer-hero.png`, `public/farmer-tablet.png`, `public/farmers-meeting.png`, `public/logo.png`, `public/realistic-farm.png`, `public/realistic-farm-mobile.png`: Unused legacy promotional graphics.
  - `vercel.json`: Removed; Render is the dedicated cloud deployment platform.

### B. Twilio Excision & Dependency Sanitization
* **Root `requirements.txt`**: Removed residual `twilio` package entry on line 10.
* **`.env.example`**: Removed `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`.
* **`.env.local`**: Excised all `TWILIO_*` variables; updated `NEXT_PUBLIC_API_URL=https://agrisaathi-6dg1.onrender.com`.

### C. Removal of Hardcoded & Misleading Outputs
* **`mlbackend/main.py`**:
  - Excised hardcoded initial registration readings (`airTemperature: 28.5`, `soilMoisture: 45.0`, `pH: 6.8`, `battery: 95`). Newly registered nodes now return honest `None` values and `sensorHealth: PENDING_FIRST_READING` until actual telemetry is transmitted.
* **`mlbackend/mqtt_service.py`**:
  - Removed pre-seeded fake telemetry in `_latest_telemetry["ESP32_NODE_01"]` (`28.5°C`, `60.0%`, `Early Blight`, `89%`). Now initializes with `None` values and `data_source: UNAVAILABLE` until live MQTT packets arrive.
* **`android-app/src/services/ApiClient.ts`**:
  - Updated `DEFAULT_API_URL` from emulator `http://10.0.2.2:8000` to `https://agrisaathi-6dg1.onrender.com`.
  - Fixed `diagnoseLeafImage` payload key from `image` to `image_base64`, matching FastAPI `VisionDiagnoseInput`.
  - Added `IrrigationClient` with `assessIrrigation` method.
* **`android-app/src/screens/SensorScreen.tsx`**:
  - Fixed parser to correctly read `telRes.history[0]`.
  - Removed all hardcoded fallback values (`38.5`, `28.0`, `62.0`).
  - Unequipped or null sensor channels are honestly displayed as `"Not measured"` or `"--"`.
  - Integrated live weather from `/api/weather-advice` and live pump state from `/pump/state`.
* **`android-app/src/screens/CropRecommendationScreen.tsx`**:
  - Fixed "Fetch Live Telemetry" parser to extract `nitrogen`, `phosphorus`, `potassium`, `temperature_c`, and `humidity_pct` from `res.history[0]`.
  - Removed silent console warnings.
* **`android-app/src/screens/PumpControlScreen.tsx`**:
  - Removed hardcoded `rainProbabilityPct: 85` and `rainForecastMm: 12.0`.
  - Added live weather query to determine real-time precipitation risk dynamically before pump dispatch.
* **`android-app/src/screens/VisionScreen.tsx`**:
  - Removed pre-populated fake disease result (`Bacterial Leaf Blight`, `0.874`). Screen initializes with `null` result and prompts user to scan.
  - Correctly maps live model diagnostic fields (`diagnosis`, `confidence_pct`, `action`, `category`, `engine`).
* **`android-app/src/screens/DecisionScreen.tsx`**:
  - Replaced 100% static dummy stages and fake 600ms `setTimeout` with live multi-agent pipeline querying `/telemetry`, `/api/weather-advice`, and `/api/irrigation/assess`.
  - Grounded determinations dynamically evaluate whether Rain Lockout is engaged or irrigation is required.
* **`android-app/src/screens/TelemetryScreen.tsx`**:
  - Removed 6 hardcoded initial mock data points (`06:00`, `08:00`...).
  - Dynamically loads real time-series history from `/telemetry` and displays honest empty state if no packets exist.
* **`android-app/src/screens/AlertsScreen.tsx`**:
  - Removed fake fallback notifications (`notif_001`, `notif_002`, `notif_003`).
  - Displays genuine empty state when no alerts are active.
* **`android-app/src/screens/ProvisioningScreen.tsx`**:
  - Removed fake scan string `"Found: ESP32-002 (Signal -62 dBm)"`.
* **`android-app/App.tsx`**:
  - Added `ChatScreen` to navigation so farmers can access the multi-agent AI assistant.

---

## 3. Automated Verification Results

| Suite / Check | Command | Result | Notes |
|---|---|---|---|
| **Android TypeScript** | `.\node_modules\.bin\tsc.cmd --noEmit` | **0 ERRORS (PASS)** | Full compile check |
| **Backend Integration Suite** | `python mlbackend/test_integration.py` | **44/44 PASS** | All core endpoints verified |
| **42-Point Master Verification** | `python mlbackend/test_comprehensive.py` | **42/42 PASS** | MQTT, null-safety, rain lockout, security |
| **Phase-4 Integration Suite** | `python mlbackend/test_phase4_integration.py` | **7/7 PASS** | Twilio excision & schema checks |
| **Render Cloud Live Smoke Test**| Direct HTTPS requests | **6/6 PASS (HTTP 200)** | Verified live on Render |

---

## 4. Remaining Manual-Review Items & Non-Blockers

1. **Physical Hardware Uplink**:
   - Simulated telemetry works end-to-end. Physical ESP32 hardware flashing with capacitive sensors requires on-site testing with Mosquitto broker.
2. **Supabase Cloud Schema Deployment**:
   - `supabase/migrations/20260911_agrisaathi_core.sql` is ready for one-click execution in the Supabase SQL editor.
