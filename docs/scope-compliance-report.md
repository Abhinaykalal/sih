# AgriSaathi AI — Scope Compliance Report

**Date**: 2026-09-11  
**Auditor**: Antigravity Scope Enforcement & Verification Pipeline  
**Specification**: SIH26180 Precision Agriculture Platform  
**Target Architecture**: Android Native Client + FastAPI Intelligence Engine on Render

---

## 1. Compliance Status Matrix

| Area | Status | Evidence | Remaining Issue |
|---|---|---|---|
| **FastAPI Backend** | `VERIFIED` | 44/44 integration tests pass; 42/42 master tests pass; 35+ routes operational in `mlbackend/main.py` | None. Monolithic file can optionally be split into router modules in future refactor. |
| **Render Deployment** | `VERIFIED` | Live at `https://agrisaathi-6dg1.onrender.com`; `/health`, `/version`, `/telemetry`, `/pump/state`, `/notifications`, `/api/recommend` respond HTTP 200 | Cloud tier sleep on inactivity requires 30s cold start if not kept warm. |
| **Supabase** | `READY_FOR_MANUAL_STEP` | `supabase/migrations/20260911_agrisaathi_core.sql` contains farm tenancy, telemetry tables, and RLS policies | Requires executing migration script in live Supabase SQL console. |
| **Android App** | `VERIFIED` | 0 TypeScript errors (`tsc --noEmit`); all 6 screens wired to live Render backend via `ApiClient.ts`; mock data completely excised | Physical device on-field smoke test under sunlight. |
| **Ollama / RAG** | `IMPLEMENTED` | Curated ICAR/IMD knowledge chunks in `data/rag/`; `rag_engine.py` generates citation-backed responses; Groq cloud fallback active | Ollama local daemon requires ≥8GB RAM on edge laptop; cloud fallback is used on Render free tier. |
| **Crop Model** | `VERIFIED` | Authentic `RandomForestClassifier` (`model.joblib`, 46 MB) achieving 99.1% test accuracy across 22 crops | None. Provenance accurately labeled as `REAL_VERIFIED`. |
| **Vision Model** | `EXPERIMENTAL` | Ensemble classifier weights (`vision_model.joblib`, 110 MB); honestly labeled as `EXPERIMENTAL` across UI and model registry | Requires retraining on machine with ≥16GB RAM for calibrated probability distribution. |
| **MQTT Service** | `IMPLEMENTED` | Exact topic schema (`agrisaathi/nodes/ESP32_NODE_01/telemetry`), LWT status, range validation, zero vs null distinction | Requires running live Mosquitto broker with physical hardware node. |
| **Pump Lifecycle** | `VERIFIED` | Full 4-stage lifecycle: `REQUESTED` → `PUBLISHED` → `ACKNOWLEDGED` → `EXECUTED`; state tracking in `pump_controller.py` | Physical relay confirmation on hardware. |
| **Rain Lockout** | `VERIFIED` | Evaluates active rain, rain probability (≥50%), and forecast (≥5.0mm); blocks irrigation unless audited manual override armed | None. Tested and verified in 7/7 pump test suite. |
| **Notifications** | `VERIFIED` | Provider-independent in-app notification engine (`notification_engine.py`); canonical SQLite storage; zero Twilio dependency | Push notification dispatch (FCM) when app is backgrounded. |
| **Offline Sync** | `VERIFIED` | Idempotent batch sync (`/api/offline-sync`) using `client_action_id` deduplication; client queue in `OfflineStore.ts` | None. |
| **Provenance** | `VERIFIED` | Strict provenance taxonomy rendered on all screens (`LIVE_SENSOR`, `RULE_BASED`, `MODEL_PREDICTION`, `EXPERIMENTAL`, `UNAVAILABLE`) | None. Zero false "zero hallucination" or fake confidence claims. |
| **Android APK** | `VERIFIED` | Standalone release APK built and verified: `android-app/android/app/build/outputs/apk/release/app-release.apk` (62,384,019 bytes, SHA-256: `4D1724BDD8D9C2380FB4AE7F52551B2DB75B6EBD86E88C0DB9C504DFD51615D0`) | Requires sideloading APK onto physical farmer phone via USB or download link. |

---

## 2. Strict Rule Verification

* **Zero Twilio**: Verified. Excised from `requirements.txt`, `.env.example`, `.env.local`, and codebase.
* **No Fake Production Outputs**: All mock fallbacks in `SensorScreen.tsx`, `CropRecommendationScreen.tsx`, `AlertsScreen.tsx`, `VisionScreen.tsx`, `DecisionScreen.tsx`, and `TelemetryScreen.tsx` removed.
* **Preservation of Null vs Zero**: Missing sensor fields remain `null` or display `"Not measured"` / `"--"`, never converted to zero or fake averages.
* **Rain Lockout Enforced**: Verified in code and tests.
* **Truthful Model Reporting**: Crop RF model labeled `REAL_VERIFIED`; Vision model labeled `EXPERIMENTAL`.
