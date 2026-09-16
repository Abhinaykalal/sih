# AgriSaathi AI — SIH Precision Agriculture Prototype

> **Reality-first status:** this repository contains a substantial FastAPI + React Native prototype with experimental ML/RAG/IoT components. Not every advertised capability is production-verified. The status below intentionally distinguishes implemented code from experimentally validated or hardware-dependent behavior.

## Capability status

| Area | Repository status | Reality boundary |
|---|---|---|
| FastAPI backend | IMPLEMENTED | Multiple routes are present; deployment still requires environment configuration and endpoint-level testing. |
| React Native Android app | IMPLEMENTED | App screens/services exist; full device validation is still required. |
| Crop recommendation | EXPERIMENTAL | A scikit-learn artifact is loaded when present. Reported confidence is per-input prediction confidence, not test accuracy. |
| Leaf vision | EXPERIMENTAL | `vision_ai_model.py` validates images and accepts only the repository's approved HOG/SVM artifact format. No diagnosis is returned if the compatible artifact is unavailable. |
| RAG | EXPERIMENTAL | RAG code exists, but the repository does not establish a complete reproducible production document-ingestion/vector-store benchmark. |
| MQTT | IMPLEMENTED TRANSPORT | Backend now uses a real MQTT client and refuses to report publication when disconnected. Broker credentials and a reachable broker are required. |
| Pump command lifecycle | EXPERIMENTAL / HARDWARE-DEPENDENT | Backend records requested/published/acknowledged/executed states, but physical execution requires a real device reporting the corresponding state. |
| ESP32 telemetry | PROTOTYPE | Firmware and telemetry paths exist, but real sensor calibration, device identity, TLS/authentication, and hardware-in-the-loop validation are not established by this repository alone. |
| Edge crop guard | RULE-BASED | `tinyml_crop_guard.h` contains transparent deterministic heuristics. It is **not** a trained TinyML model and makes no accuracy claim. |
| Offline storage | IMPLEMENTED LOCALLY | SQLite/in-memory mechanisms exist. A single durable production source of truth still needs to be established. |
| Production readiness | NOT VERIFIED | Security, cloud configuration, real hardware, model evaluation, load testing, observability, and deployment validation remain required. |

## Architecture

```text
React Native Android
        |
        | HTTPS + authenticated API calls
        v
FastAPI backend (mlbackend/)
   |       |        |        |
   |       |        |        +--> ML / vision / decision support
   |       |        +-----------> RAG / LLM services
   |       +--------------------> SQLite / optional Supabase
   +----------------------------> MQTT broker <--> ESP32 node
```

## Quick start

### Backend

```bash
python -m venv venv
# Windows: venv\\Scripts\\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt

# Create a local environment file from the template and configure it.
# Do not commit real credentials.
python -m uvicorn mlbackend.main:app --host 127.0.0.1 --port 8000 --reload
```

The interactive API documentation is available from the running FastAPI service at `/docs`.

### Android

```bash
cd android-app
npm install
npx expo start
```

Configure the backend URL in the app for your emulator, local network, or deployed API. Do not assume a particular cloud hostname unless your deployment actually uses it.

## Environment and security

Use `.env.example` as the configuration reference. Production deployments should provide, at minimum, the authentication secret and explicitly configured CORS origins. MQTT credentials and TLS settings must be supplied through environment variables.

The repair branch defaults to JWT enforcement and rejects wildcard CORS configuration. Development authentication bypass is permitted only when both development flags are explicitly enabled.

Never put passwords, JWT secrets, API keys, Wi-Fi credentials, or device secrets in source control. ESP32 credentials belong in the ignored `edge_hardware/secrets.h`, based on `edge_hardware/secrets.example.h`.

## Crop recommendation

The crop recommendation endpoint uses the available `model.joblib` artifact when it can be loaded. Its response contains a **prediction confidence** calculated from the model's output probabilities. The API does not treat a hard-coded number as test accuracy.

A genuine benchmark should be generated from a versioned held-out evaluation set and recorded with the model artifact, dataset provenance, split strategy, and reproducible evaluation command.

## Leaf vision

The vision path is deliberately conservative:

1. Decode and size-check the uploaded image.
2. Run a leaf-like image quality/scope gate.
3. Load only an artifact with the approved `agrisaathi_vision_hog_svm_v1` type.
4. Verify feature compatibility.
5. Return `NO_RELIABLE_RESULT` below the configured confidence threshold.
6. Return `MODEL_UNAVAILABLE` instead of inventing a diagnosis when the compatible artifact is missing.

The repository should not claim a disease benchmark unless the dataset, training run, held-out test results, and field validation are reproducible.

## MQTT and pump safety

MQTT publication is a real transport operation. A disconnected backend raises an error rather than returning a fake `published` status.

The pump controller is a safety-gated command layer. Physical execution must be confirmed by telemetry from the device; a mobile UI timeout is not evidence of physical execution. Rain lockout is not intended to be bypassed through a client-side override.

The LLM/RAG layer must never be treated as the authority for physical actuator state.

## Dataset provenance

`mlbackend/dataset_pipeline.py` now reports only evidence observable from an actual dataset manifest. It does not manufacture sample counts, duplicate-removal counts, leakage scores, accuracy, F1, precision, recall, or latency.

If `datasets/vision/vision_manifest.csv` is absent, the dataset report is `NOT_AVAILABLE` rather than `VALIDATED`.

## Testing

Run the repair contract tests with:

```bash
python -m pytest mlbackend/tests/test_repair_contracts.py -v
```

Additional existing test suites can be run when their external services and dependencies are configured. Test counts in this README are intentionally not presented as a guarantee of passing end-to-end hardware behavior.

## Hardware prototype

The `edge_hardware/` directory contains ESP32-related prototype code. Hardware-dependent claims require:

- a real board and identified sensor modules;
- calibrated sensor conversion constants;
- provisioned device credentials;
- a reachable MQTT broker;
- authenticated telemetry;
- hardware-in-the-loop tests;
- confirmation that reported actuator state reflects the physical device.

The edge crop guard is explicitly rule-based. It should not be described as trained TinyML without a reproducible training artifact and evaluation evidence.

## Repository structure

```text
mlbackend/       FastAPI backend, AI services, database and control logic
android-app/     React Native / Expo application
edge_hardware/   ESP32 prototype firmware and configuration examples
data/            Application/RAG data locations
models/          Model metadata and model-card material
docs/             Project documentation and validation material
.github/          CI workflows
```

## Current development branch

The forensic repair work is being developed on `fix/agrisaathi-forensic-repair`. Changes should be validated against real dependencies and hardware before being represented as production-complete.

## Project purpose

AgriSaathi is a Smart India Hackathon project/prototype exploring precision-agriculture decision support, sensor telemetry, agricultural knowledge retrieval, computer vision, and safe actuator integration.
