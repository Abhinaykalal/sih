# AgriSaathi AI — Complete Repository Audit Report
**Date**: September 2026 | **Version**: 1.0.0 | **Audit Scope**: Full Stack (IoT, AI/ML, Backend, Frontend, Android, DevOps, Security, QA)

---

## Executive Summary

This audit report provides an objective, rigorous, and unsparing examination of the AgriSaathi AI repository (`agrisaathi-sih`). Every component—from hardware edge contracts and MQTT broker topologies to ML model weights, dataset provenance, and Android build scripts—has been inspected directly from code.

**Key Findings**:
1. **Core Crop Recommendation Model is Real**: `mlbackend/model.joblib` (45.9 MB) is an authentic, trained scikit-learn `RandomForestClassifier` supporting 22 crop classes across 7 agronomic input features (`N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`).
2. **Vision Model is a 20-Sample Toy with Clamped Metrics**: `mlbackend/vision_model.joblib` was trained on only 20 hardcoded feature vectors. The 99.9% precision metric is hardcoded, and inference artificially clamps confidence to `max(98.5, confidence)`. No actual PlantVillage images reside in `datasets/`.
3. **MQTT Telemetry Contract Discrepancies**: The backend (`mqtt_service.py`) currently subscribes to `agrisaathi/sensors/+/telemetry` instead of the mandated uplink `agrisaathi/nodes/ESP32_NODE_01/telemetry`. It lacks downlink command handlers (`agrisaathi/nodes/ESP32_NODE_01/commands`) and lifecycle status handlers (`agrisaathi/nodes/ESP32_NODE_01/status`).
4. **Missing Sensor Value Handling Violates Contract**: `main.py` currently falls back to non-zero defaults (`data.z2_moisture or 20.0`) when sensor fields are missing, violating the rule: *"Missing sensor values are JSON null. Null must never be converted to zero or invented."*
5. **Backend Lacks Authentication Middleware**: While the Next.js frontend integrates Supabase Auth, the FastAPI backend does not validate JWT tokens or enforce authorization headers on any endpoints.
6. **Android App Exists as Expo/React Native**: The mobile codebase exists in `android-app/` with 6 core screens, local offline storage, and an Android Gradle wrapper (`android-app/android/`). However, building the APK requires JDK 17 and Android SDK command-line tools to be locally available.

---

## Comprehensive 30-Point Audit

### 1. Repository Structure
The repository is divided into 5 primary subsystems:
- `mlbackend/`: FastAPI application containing AI/ML models, background tasks, RAG engine, SQLite databases, and integration tests.
- `src/`: Next.js 15 web application with React 19, Tailwind CSS, Lenis smooth scrolling, Three.js backgrounds, and Supabase client.
- `android-app/`: React Native (Expo 51) mobile application containing screens for Chat, Sensors, Vision, Alerts, Provisioning, and Settings.
- `edge_hardware/`: ESP32 Arduino sketch (`esp32_sensor_node.ino`), TinyML C++ header (`tinyml_crop_guard.h`), and edge gateway script.
- `datasets/`: Directory structure created by `dataset_pipeline.py` with `metadata/dataset_provenance.json`, but currently empty of raw images or training CSVs.

### 2. Backend (FastAPI)
- **File**: `mlbackend/main.py` (1,541 lines, 35+ endpoints).
- **Architecture**: Single monolithic script importing auxiliary service modules (`pest_service.py`, `fertilizer_service.py`, `yield_service.py`, `risk_engine.py`, `agent_orchestrator.py`, `multilingual.py`).
- **Issues**: Monolithic file structure makes route management difficult. Endpoints lack unified exception handlers and request validation middleware.

### 3. Frontend (Web UI)
- **Framework**: Next.js 15.1.0 with App Router, React 19, Lucide React icons.
- **Role**: Development, testing, and debugging interface (per product requirement, Android APK is the final farmer-facing app).
- **Status**: Operational, running on `http://localhost:3000` via `npm run dev`.

### 4. Android Application
- **Directory**: `android-app/`
- **Stack**: Expo SDK 51, React Native 0.74.5, TypeScript, Async Storage.
- **Screens**:
  - `ChatScreen.tsx`: Conversational AI with audio toggle and RAG citations.
  - `SensorScreen.tsx`: Real-time telemetry cards, gauge indicators, and refresh controls.
  - `VisionScreen.tsx`: Camera capture and disease diagnostic interface.
  - `AlertsScreen.tsx`: Push and offline alert center with priority filters.
  - `ProvisioningScreen.tsx`: Bluetooth / Wi-Fi provisioning interface for ESP32.
  - `SettingsScreen.tsx`: Language picker, server URL configuration, offline cache clearing.
- **Native Android**: `android-app/android/` contains `build.gradle`, `settings.gradle`, and `app/`. Build instructions documented in `docs/android-build.md`.

### 5. Database Architecture
- **Local SQLite DB 1**: `mlbackend/farm_analytics.db` (stores `telemetry`, `zone_states`, `offline_sync_queue`).
- **Local SQLite DB 2**: `mlbackend/hybrid_farm_edge.db` (stores `farmer_profiles`, `telemetry_logs`, `sync_queue`).
- **Local SQLite DB 3**: `mlbackend/conversation_memory.db` (stores conversation sessions and message history).
- **Cloud Database**: Supabase PostgreSQL configured for user authentication and cloud profiles.
- **Issue**: Three separate SQLite database files exist in `mlbackend/` with duplicate tables (`telemetry` vs `telemetry_logs`). They should be unified into a single schema.

### 6. Authentication
- **Frontend**: Fully wired to Supabase (`src/context/AuthContext.tsx`) with login, signup, OTP, and session tracking.
- **Backend**: Completely unauthenticated. None of the FastAPI endpoints inspect `Authorization: Bearer <token>` or validate JWT signatures.
- **Risk**: Any client or script can invoke destructive or administrative endpoints without credentials.

### 7. MQTT Integration
- **Current File**: `mlbackend/mqtt_service.py`
- **Broker**: `broker.hivemq.com` on port 1883 (anonymous public broker).
- **Topic Discrepancy**:
  - *Current*: `agrisaathi/sensors/+/telemetry`
  - *Required*:
    - Uplink: `agrisaathi/nodes/ESP32_NODE_01/telemetry`
    - Downlink: `agrisaathi/nodes/ESP32_NODE_01/commands`
    - Lifecycle: `agrisaathi/nodes/ESP32_NODE_01/status`
- **Security**: Current setup uses anonymous plaintext MQTT on port 1883. Production requires TLS (port 8883) with client certificates or token authentication.

### 8. Telemetry Validation
- **Hardware Contract**:
  - `soil_moisture_pct`: 0–100% (Primary decision metric).
  - `soil_raw_adc`: 0–4095 (Diagnostic data).
  - `temperature_c`: -10°C to 60°C.
  - `humidity_pct`: 0–100%.
  - `sunlight_detected`: boolean.
- **Defect in Current Ingestion**:
  In `main.py:938`:
  ```python
  soil_moisture=data.z2_moisture or 20.0  # VIOLATION: converts null to 20.0
  humidity=data.z4_humidity or 80.0       # VIOLATION: converts null to 80.0
  ```
  Missing values MUST be preserved as `None`/`null` and never coerced to arbitrary numbers.

### 9. Actuator & Pump Commands
- **Current State**: `esp32_sensor_node.ino` contains local relay triggers for `PUMP_RELAY_PIN` (GPIO 26) and `MISTER_RELAY_PIN` (GPIO 27).
- **Missing**: Backend has no MQTT downlink command publisher (`agrisaathi/nodes/ESP32_NODE_01/commands`) to dispatch `{"command": "PUMP_ON", "duration_sec": 300}` or `{"command": "PUMP_OFF"}`.

### 10. Rain Lockout Protection
- **Rule**: If rain is forecasted (>50% probability or >5mm expected) or active, irrigation pumps must be locked out to prevent waterlogging and fertilizer runoff.
- **Current State**: Logic exists in `risk_engine.py:evaluate_smart_irrigation` and `model_providers.py:assess_irrigation_needs`, returning `"HOLD_PUMP"`.
- **Gap**: No hardware-level enforcement exists to block manual override commands during rain lockout.

### 11. Vibration Sensor Support
- **Purpose**: Detect physical tampering with sensor nodes or monitor pump motor mechanical vibration for early cavitation/bearing failure.
- **Current State**: Absent from `mqtt_service.py` and `SensorInput` schemas.
- **Requirement**: Must be added as an optional, backward-compatible field (`vibration_detected: Optional[bool] = None`, `vibration_rms: Optional[float] = None`), defaulting to `null`.

### 12. NPK Sensor Support
- **Current State**: Simulated in `esp32_simulator.py` as `{"N": 45, "P": 22, "K": 38}`.
- **Requirement**: Must remain optional in the hardware payload. If the node lacks an optical/RS485 NPK probe, the field must be `null` and never converted to 0.

### 13. AI/ML Models Overview
- Real trained ML models: 1 (`model.joblib` for crop recommendation).
- Rule-based agronomic expert systems: 4 (`pest_service.py`, `fertilizer_service.py`, `yield_service.py`, `risk_engine.py`).
- Synthetic/toy models: 3 (`vision_model.joblib`, `advisor_model.joblib`, `custom_agri_llm.joblib`).
- TinyML on-device engine: 1 (`tinyml_crop_guard.h`, hardcoded C++ threshold heuristics).

### 14. Dataset Usage
- `datasets/raw/`: Empty.
- `datasets/cleaned/`: Empty.
- `datasets/train/`: Empty.
- `datasets/validation/`: Empty.
- `datasets/test/`: Empty.
- `datasets/metadata/dataset_provenance.json`: Metadata catalog claiming 15,000 images, but image files are not committed.

### 15. Training Scripts
- `mlbackend/train_model.py`: Valid script for crop recommendation using `RandomForestClassifier`.
- `mlbackend/train_vision_model.py`: Script using 20 synthetic feature rows, claiming 99.9% precision.
- `mlbackend/train_advisor_model.py`: Script training TF-IDF on 6 Q&A pairs.
- `mlbackend/train_custom_llm.py`: Script training TF-IDF on 5 Q&A pairs.
- `mlbackend/train_edge_model.py`: Script generating mock weights.

### 16. Model Files
- `mlbackend/model.joblib`: 45.9 MB, valid scikit-learn model.
- `mlbackend/vision_model.joblib`: 1.56 MB, valid scikit-learn pipeline on 20 synthetic samples.
- `mlbackend/advisor_model.joblib`: 7.9 KB, TF-IDF nearest-neighbor dictionary.
- `mlbackend/custom_agri_llm.joblib`: 284 KB, TF-IDF + LogisticRegression pipeline.

### 17. Model Registry
- **File**: `mlbackend/model_registry.py`
- **Exposed Endpoint**: `GET /api/model-registry`
- **Discrepancy**: Claims models are trained on 15,000 PlantVillage images and FAO datasets with 94.2% accuracy, whereas actual model files in the repository use 20 synthetic rows. The registry must be updated to honestly reflect model states (real vs rule-based vs experimental).

### 18. LLM Service & Fallbacks
- **Implementation**: Tiered LLM cascade in `mlbackend/services.py` and `model_providers.py`:
  1. Groq / OpenAI / Anthropic cloud API (if API keys configured).
  2. Local Custom Agri LLM (`custom_agri_llm.joblib`).
  3. Grounded rule-based fallback responses.
- **Status**: Resilient to missing cloud keys; operates standalone.

### 19. Retrieval-Augmented Generation (RAG)
- **File**: `mlbackend/rag_engine.py`
- **Knowledge Base**: 4 seeded documents from ICAR, IMD, and FAO.
- **Mechanism**: In-memory keyword overlap and tag matching.
- **Limitation**: No vector database (FAISS, Chroma, Milvus) or dense semantic embeddings. Sufficient for prototype, but needs scaling for production agronomic manuals.

### 20. Multi-Agent Orchestrator
- **File**: `mlbackend/agent_orchestrator.py` (18 KB)
- **Role**: Coordinates intent detection, language processing, sensor grounding, RAG retrieval, and response synthesis.
- **Anti-Hallucination**: Implements strict grounded evidence checks—verifies that sensor readings cited in AI responses match actual live or simulated readings.

### 21. Weather Service
- **Provider**: OpenWeatherMap API via `mlbackend/services.py`.
- **Fallback**: Physics-based simulated weather when API key is unconfigured or rate-limited.
- **Safety**: 3-day forecast rainfall integrated into irrigation recommendations.

### 22. Alerting Engine
- **Files**: `mlbackend/notification_service.py`, `notification_engine.py`, `risk_engine.py`.
- **Channels**: In-app push notifications, local SQLite offline queue, optional Twilio SMS, Telegram bot.
- **Cooldown**: 30-minute cooldown timer prevents alert spamming for continuous sensor threshold breaches.

### 23. Offline-First Architecture
- **Edge Storage**: SQLite databases on local disk.
- **Sync Protocol**: `/api/offline-sync` accepts batch action arrays from Android when network connectivity returns.
- **Simulator**: `esp32_simulator.py` tags all non-field telemetry with `"data_source": "SIMULATED"`.

### 24. Multilingual Engine
- **File**: `mlbackend/multilingual.py`
- **Detection**: Powered by `langdetect` library with script regex fallbacks.
- **Supported Languages**: English, Hindi, Punjabi, Telugu, Tamil, Marathi, Bengali, Gujarati, Kannada, Malayalam.
- **Translation**: Dictionary and pattern-based translation with English reasoning backbone.

### 25. Security & Secrets Management
- **Vulnerabilities**:
  1. `.env.local` contains Supabase URL and OpenWeatherMap key in plaintext.
  2. No rate-limiting middleware on FastAPI routes.
  3. CORS allows all origins (`allow_origins=["*"]`).
  4. Backend has no JWT validation middleware.
- **Recommendation**: Restrict CORS, configure FastAPI security dependency, and migrate secrets to environment vaults.

### 26. Automated Test Suite
- **File**: `mlbackend/test_integration.py`
- **Current Passing Count**: 45 / 45 tests passing.
- **Coverage**: Covers recommendation, fertilizer, disease classification, agent chat, multilingual detection, sensor telemetry, RAG, and memory clear.
- **Missing Tests**: MQTT topic routing, pump command dispatch, rain lockout enforcement, vibration schema backward-compatibility.

### 27. Deployment Configuration
- `Procfile`: Configured for `uvicorn mlbackend.main:app`.
- `railway.toml`: Configured for Railway deployment.
- `vercel.json`: Configured for Next.js frontend deployment.

### 28. Environment Variables Audit
- `.env.local`: Contains `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_API_URL`, `OPENWEATHER_API_KEY`.
- `.env` in `mlbackend/`: Uses fallback defaults if unpopulated.
- Missing: Standardized `.env.example` documenting all required and optional keys.

### 29. Hardcoded Responses Inventory
1. `mlbackend/vision_ai_model.py:139`: `calibrated_confidence = max(98.5, confidence)`.
2. `mlbackend/model_providers.py:85-100`: Hardcoded disease labels based strictly on crop name string matching.
3. `mlbackend/custom_llm_dataset.json`: 5 hardcoded Q&A samples.
4. `mlbackend/agri_training_data.json`: 6 hardcoded Q&A samples.
5. `mlbackend/dataset_pipeline.py:38-58`: Hardcoded dictionary claiming 15,000 images validated.

### 30. Simulated Data Inventory
1. `mlbackend/esp32_simulator.py`: Generates realistic diurnal curves, ET0 evapotranspiration loss, and rainfall events. Properly tagged with `"data_source": "SIMULATED"`.
2. `mlbackend/services.py:get_weather`: Returns deterministic mock weather if OpenWeatherMap key is missing.
3. `mlbackend/main.py:1365`: Mock default telemetry for newly registered devices.

---

## Conclusion

The repository has an exceptionally strong architectural foundation, a functional 45-test integration suite, and working end-to-end pipelines. However, to transition from a prototype to a production-grade, verifiable system, the simulated vision models must be clearly demarcated, MQTT topics and payloads must be aligned with hardware contracts, and the backend must enforce strict null-preservation on sensor inputs.
