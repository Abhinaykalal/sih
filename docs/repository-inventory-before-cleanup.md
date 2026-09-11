# AgriSaathi AI — Complete Repository Inventory Before Cleanup

**Date**: 2026-09-11  
**Author**: Antigravity Automated Audit & Scope Enforcement Engine  
**Target Repository**: `agrisaathi-sih`  
**Current Active Deployment**: Render (`https://agrisaathi-6dg1.onrender.com`)  
**Cleanup Branch**: `cleanup-scope-enforcement`

---

## 1. Executive Summary & Inventory Scope

This document provides a comprehensive inventory of every top-level folder, UI/UX folder, backend route and module, Android screen, ML model file, database/migration script, deployment configuration, test suite, and documentation file across the entire repository.

Each suspicious, obsolete, or duplicate file is strictly classified under:
* **KEEP**: Active, required, and scoped to the AgriSaathi AI specification.
* **MERGE**: Contains valid functionality that must be consolidated into a single canonical module.
* **REPLACE**: Contains outdated/hardcoded logic that must be refactored into real API/service calls.
* **ARCHIVE**: Legacy prototype code preserved in `archive/` for reference, removed from active build paths.
* **DELETE**: Confirmed dead code, duplicate files, hardcoded mocks, or excised third-party modules.
* **NEEDS MANUAL REVIEW**: Files requiring user or external confirmation before modification.

---

## 2. Top-Level Folder Inventory

| Directory | Purpose / Role | Active Dependency | Classification | Rationale |
|---|---|---|---|---|
| `android-app/` | React Native (Expo) Android App (`com.agrisaathi.app`) | Primary farmer client | **KEEP** | Scoped farmer client with 6 core screens, local offline store, and native Android Gradle wrapper. |
| `mlbackend/` | FastAPI Intelligence Engine, ML inference, RAG, MQTT | Primary backend on Render | **KEEP** | Core backend containing 35+ routes, model registry, telemetry ingestion, and pump safety controls. |
| `src/` | Old Next.js 15 web dashboard & prototype routes | Deprecated web UI | **ARCHIVE / DELETE** | Render only deploys the FastAPI backend (`mlbackend`). The web dashboard was replaced by `android-app/`. |
| `models/` | ML model cards, metrics, and evaluation documentation | Documentation & metadata | **KEEP** | Documents models for crop recommendation, leaf disease vision, irrigation, vibration, NPK, and yield. |
| `datasets/` | Manifests, dataset provenance, and train/test splits | ML pipeline & auditing | **KEEP** | Verified split CSVs and metadata for crop recommendation, fertilizer, and irrigation. |
| `data/` | RAG training, validation, and test JSONL files | Knowledge base | **KEEP** | Verified ICAR/IMD package of practices chunks used by `rag_engine.py`. |
| `docs/` | System architecture, audits, and checklists | Project governance | **KEEP** | Essential documentation for SIH jury and development validation. |
| `edge_hardware/` | ESP32 Arduino sketch, Mosquitto config, TinyML | Hardware edge node | **KEEP** | Edge sensor firmware and gateway scripts for IoT telemetry uplink. |
| `supabase/` | PostgreSQL schema migrations and RLS policies | Cloud data layer | **KEEP** | Production database migrations (`20260911_agrisaathi_core.sql`). |
| `public/` | Web images and video assets | Obsolete web UI | **DELETE** | Large unused media files (some already unlinked/deleted). |

---

## 3. Backend Module Inventory (`mlbackend/`)

| File / Module | Responsibility | Classification | Rationale & Action |
|---|---|---|---|
| `main.py` | FastAPI application root & endpoint routing | **KEEP / REFACTOR** | Primary API router. Remove hardcoded fallback readings (e.g. line 1918 `airTemperature: 28.5`). |
| `auth.py` | Supabase JWT token verification | **KEEP** | Core security middleware for protected endpoints. |
| `config.py` | Pydantic application settings | **KEEP** | Core configuration. Verify zero Twilio references. |
| `db_layer.py` | Unified SQLite database layer | **KEEP** | Canonical persistence for telemetry, notifications, and pump audit trail. |
| `hybrid_db.py` | Legacy database adapter | **MERGE / ARCHIVE** | Redundant SQLite adapter overlapping with `db_layer.py`. Merge missing methods into `db_layer.py`. |
| `notification_engine.py` | Canonical in-app notification engine | **KEEP** | Provider-independent SQLite notification dispatcher. |
| `internal_notifications.py` | Notification schemas and event definitions | **MERGE** | Merge event types and schemas cleanly into `notification_engine.py`. |
| `notification_service.py` | Legacy notification dispatcher | **ARCHIVE / DELETE** | Legacy module containing outdated notification logic; superseded by `notification_engine.py`. |
| `mqtt_service.py` | MQTT broker client & telemetry parser | **KEEP / REFACTOR** | Core IoT broker manager. Remove hardcoded mock initial state (`28.5°C`, `60.0%`, `Early Blight`, `89%`). |
| `pump_controller.py` | Actuator safety state machine & Rain Lockout | **KEEP** | Auditable pump control with strict rain lockout evaluation and MQTT dispatch. |
| `risk_engine.py` | FAO-56 irrigation and crop risk evaluation | **KEEP** | Scientific crop risk scoring. |
| `fertilizer_service.py`| NPK deficit calculation and fertilizer advice | **KEEP** | Real agronomic NPK balancer. |
| `soil_service.py` | Soil health indexing and rejuvenation | **KEEP** | Actionable soil lab advisory. |
| `pest_service.py` | Pest and pathogen risk prediction | **KEEP** | Microclimate pest threat calculation. |
| `yield_service.py` | Crop yield estimation | **KEEP** | Baseline yield predictor. |
| `rotation_service.py` | 3-season crop rotation planner | **KEEP** | Legume/pulse restorative rotation scheduler. |
| `market_service.py` | Mandi APMC price and MSP benchmarking | **KEEP** | Market commodity price feed. |
| `satellite_service.py` | Remote sensing NDVI/EVI simulation | **KEEP** | Geospatial field anomaly detection. |
| `multilingual.py` | Language detection & translation | **KEEP** | English, Hindi, and Telugu localization engine. |
| `agent_orchestrator.py`| Multi-agent reasoning and intent router | **KEEP** | Synthesizes sensor telemetry, RAG chunks, and domain tools. |
| `rag_engine.py` | RAG retrieval with provenance citations | **KEEP** | Semantic search against verified agricultural knowledge base. |
| `rag_service.py` | Legacy RAG wrapper | **MERGE / ARCHIVE** | Overlaps with `rag_engine.py`. Consolidate into `rag_engine.py`. |
| `ollama_service.py` | Ollama local model inference client | **KEEP** | Local LLM inference with transparent availability probes. |
| `llm_provider.py` | Cloud LLM fallback provider (Groq) | **KEEP** | Fallback when local Ollama is not provisioned. |
| `llm_service.py` | Legacy LLM wrapper | **MERGE / ARCHIVE** | Consolidate into `llm_provider.py`. |
| `model_registry.py` | Registry of registered models and provenance | **KEEP** | Enforces honest labeling (Crop RF: REAL_VERIFIED, Vision: EXPERIMENTAL). |
| `vision_ai_model.py` | Leaf disease vision classifier | **KEEP** | Local ensemble model (`vision_model.joblib`). |
| `esp32_simulator.py` | Realistic IoT hardware telemetry generator | **KEEP** | Realistic test fixture for hardware simulation; clearly marked `SIMULATED`. |
| `advisor_ai_model.py` | Synthetic advisor joblib wrapper | **ARCHIVE / DELETE** | Legacy toy model trained on synthetic vectors. Replaced by `agent_orchestrator.py`. |
| `custom_llm_inference.py`| Synthetic custom LLM script | **ARCHIVE / DELETE** | Toy model attempting character-level language modeling. Superseded by Ollama/Groq RAG. |

---

## 4. Android Application Screen & Service Inventory (`android-app/`)

| Screen / Component | Route / Feature | Active | Classification | Action Required |
|---|---|---|---|---|
| `App.tsx` | Main navigation container & tab bar | YES | **REPLACE** | Add `ChatScreen` to navigation; ensure high-contrast outdoor theme. |
| `SensorScreen.tsx` | Telemetry cards, gauges, live weather | YES | **REPLACE** | Parse `history[0]` properly; remove hardcoded fallbacks (`38.5, 28.0, 62.0`). |
| `CropRecommendationScreen.tsx` | 7-feature NPK crop recommendation | YES | **REPLACE** | Fix "Fetch Live Telemetry" parser to prefill live `nitrogen, phosphorus, potassium, temp, humidity`. |
| `PumpControlScreen.tsx`| Actuator control & Rain Lockout guard | YES | **REPLACE** | Remove hardcoded `rainProbabilityPct: 85`; pull live weather rainfall data. |
| `VisionScreen.tsx` | Camera leaf disease diagnosis | YES | **REPLACE** | Clear initial dummy diagnosis; fix payload parameter (`image_base64`), parse real model output. |
| `ChatScreen.tsx` | Voice/Text AI assistant with citations | YES | **REPLACE** | Expose in app navigation; connect to live `/api/agent/chat` and `/api/ai/chat`. |
| `DecisionScreen.tsx` | Multi-agent reasoning pipeline | YES | **REPLACE** | Remove 100% static dummy stages and fake 600ms `setTimeout`; wire live telemetry and FAO-56 assessment. |
| `TelemetryScreen.tsx` | Time-series charts for soil moisture | YES | **REPLACE** | Remove hardcoded mock array; render real time-series from `/telemetry`. |
| `AlertsScreen.tsx` | Notification center & audit log | YES | **REPLACE** | Remove fake demo notifications (`notif_001`, `notif_002`, `notif_003`); fetch real `/notifications`. |
| `ProvisioningScreen.tsx`| ESP32 device registration | YES | **REPLACE** | Remove hardcoded fake "Found: ESP32-002" scan; connect to live `/api/device-register`. |
| `SettingsScreen.tsx` | URL switcher & offline queue sync | YES | **KEEP** | Retain dynamic backend URL configuration and sync controls. |
| `ApiClient.ts` | Centralized network abstraction | YES | **REPLACE** | Update `DEFAULT_API_URL` to `https://agrisaathi-6dg1.onrender.com`; fix vision upload payload. |
| `OfflineStore.ts` | Local AsyncStorage cache & offline queue | YES | **KEEP** | Retains offline actions and sync idempotency. |

---

## 5. Web Frontend Inventory (`src/`)

| File / Folder | Purpose | Classification | Rationale & Action |
|---|---|---|---|
| `src/app/page.tsx` | Next.js placeholder landing page | **ARCHIVE** | 26-line placeholder indicating Android app is active. Render does not use it. |
| `src/app/layout.tsx` | Web HTML root layout | **ARCHIVE** | Unused by Android app and Render backend. |
| `src/app/globals.css` | Web CSS stylesheet (25 KB) | **ARCHIVE** | Unused by Android app. |
| `src/app/api/` | Old Next.js API routes (`health`, `sensors`, `alerts`) | **ARCHIVE / DELETE** | Duplicate endpoints superseded by FastAPI (`mlbackend/`). |
| `src/lib/aiInferenceService.ts` | Old client-side JS rule engine | **DELETE** | Contains hardcoded `Early Blight`, `Downy Mildew`, fake confidence `0.91`. |
| `src/lib/resilienceEngine.ts` | Old client-side offline engine | **ARCHIVE** | Superseded by Android `OfflineStore.ts` and FastAPI `db_layer.py`. |
| `src/lib/sensorService.ts` | Old client-side sensor fetcher | **ARCHIVE** | Superseded by `ApiClient.ts`. |
| `src/lib/supabase.ts` | Web Supabase client | **ARCHIVE** | Used only by web app. |
| `src/context/AuthContext.tsx` | Web React Auth context | **ARCHIVE** | Unused by Android app. |

---

## 6. Deployment & Configuration Inventory

| File | Purpose | Classification | Rationale & Action |
|---|---|---|---|
| `render.yaml` | Render Web Service deployment blueprint | **KEEP** | Active deployment definition for `agrisaathi-api` on Render. |
| `Dockerfile` | Container build definition | **KEEP** | Clean container build supporting `$PORT` injection for cloud hosting. |
| `requirements.txt` | Python dependencies for Render build | **REFACTOR** | Remove residual `twilio` package; keep locked versions for FastAPI/ML. |
| `mlbackend/requirements.txt` | Minimal ML backend dependencies | **KEEP** | Zero Twilio, pinned dependencies. |
| `package.json` (Root) | Node scripts for web and concurrently | **REFACTOR** | Remove obsolete scripts, ensure clean tree. |
| `android-app/package.json` | React Native / Expo dependencies | **KEEP** | Clean mobile dependencies. |
| `railway.toml` | Legacy Railway deployment config | **ARCHIVE / DELETE** | Redundant; Render is the agreed cloud platform. |
| `docker-compose.yml` | Local multi-service docker compose | **KEEP** | Useful for local integration testing with Mosquitto. |
| `.env.example` | Template environment variables | **REFACTOR** | Remove deprecated `TWILIO_*` entries; point `NEXT_PUBLIC_API_URL` to Render. |
| `.env.local` | Local environment overrides | **REFACTOR** | Remove `TWILIO_*`; update `NEXT_PUBLIC_API_URL` to `https://agrisaathi-6dg1.onrender.com`. |

---

## 7. Model Artifacts & Training Scripts

| File | Type | Classification | Rationale |
|---|---|---|---|
| `mlbackend/model.joblib` | Scikit-learn Random Forest (46 MB) | **KEEP** | Real, authentic model trained on 22 crops (99.1% accuracy). |
| `mlbackend/vision_model.joblib` | Vision ensemble (110 MB) | **KEEP** | Real model weights from prior successful training run. Labeled `EXPERIMENTAL`. |
| `mlbackend/training/train_crop_recommendation.py` | Training script | **KEEP** | Reproducible training script for crop RF. |
| `mlbackend/training/train_vision.py` | Vision training pipeline | **KEEP** | Reproducible vision training pipeline. |
| `mlbackend/training/train_irrigation.py` | Irrigation rule training | **KEEP** | Training script for FAO-56 baseline. |
| `mlbackend/training/train_npk.py` | NPK recommendation training | **KEEP** | Calibrated NPK advisory script. |
| `mlbackend/training/train_weather_yield.py` | Weather yield training | **KEEP** | Agro-climatic yield estimation training. |
| `mlbackend/training/train_vibration.py` | Vibration motor training | **KEEP** | Motor anomaly detection script. |
| `mlbackend/train_advisor_model.py` | Legacy synthetic training | **ARCHIVE** | Synthetic toy training script. |
| `mlbackend/train_custom_llm.py` | Legacy character LLM training | **ARCHIVE** | Obsolete toy LLM trainer. |

---

## 8. Summary of Suspicious & Deprecated Touchpoints Identified

1. **Hardcoded Fallbacks in Android Screens**:
   - `SensorScreen.tsx`: Falls back to fake sensor readings (`38.5, 28.0, 62.0`) because `res.history[0]` was not read from the backend payload.
   - `PumpControlScreen.tsx`: Hardcoded `rainProbabilityPct: 85`, artificially locking out the pump on every trigger.
   - `CropRecommendationScreen.tsx`: "Fetch Live Telemetry" parser checked outdated field names instead of `res.history[0]`.
   - `VisionScreen.tsx`: Initial state contained pre-populated disease result (`Bacterial Leaf Blight`), and sent `{ image }` instead of `{ image_base64 }`.
   - `DecisionScreen.tsx`: Contained static mock text array and fake 600ms `setTimeout`.
   - `TelemetryScreen.tsx`: Initial state populated with hardcoded fake time-series entries.
   - `AlertsScreen.tsx`: Falls back to fake notifications (`notif_001`, `notif_002`, `notif_003`).
   - `ApiClient.ts`: Default URL pointed to emulator `http://10.0.2.2:8000`, causing physical phones to immediately drop offline and trigger mock fallbacks.

2. **Residual Twilio References**:
   - `requirements.txt`: Contained `twilio` on line 10.
   - `.env.example` and `.env.local`: Contained `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`.

3. **Backend Hardcoded Fallback Values**:
   - `mlbackend/main.py:1918`: Device registration response defaulted `airTemperature: 28.5`, `soilMoisture: 45.0` instead of `None`.
   - `mlbackend/mqtt_service.py:237`: `_latest_telemetry` dictionary was pre-initialized with `28.5°C`, `60.0%`, `Early Blight`, `89%`.
   - `mlbackend/services.py:150`: Weather simulation mode returned `28.5°C`.

4. **Obsolete Web Prototype**:
   - `src/app/` and `src/lib/`: Old web prototype that is not deployed or used by Render (Render only builds `mlbackend`).
