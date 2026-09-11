# AgriSaathi AI — Comprehensive Data Source Audit

**Date**: 2026-09-11  
**Auditor**: AgriSaathi AI Architecture & Verification Pipeline  
**Specification**: SIH26180 Precision Agriculture  

---

## Executive Summary

This audit establishes a complete trace of every displayed field across the AgriSaathi AI system — from the physical or simulated ESP32 edge node, MQTT broker, and FastAPI backend services to the local SQLite/Supabase databases and the React Native Android screens.

Every field is audited for:
- Traceability: Live data pipeline vs rule-based vs model prediction vs simulated vs unavailable.
- Provenance Integrity: Ensuring no simulated or missing values are disguised as live measurements.
- Null Safety: Preventing silent conversion of missing telemetry to `0` or arbitrary default strings.

---

## Data Source Audit Matrix

| Field | Backend source | Database/table | API endpoint | Android screen | Provenance | Current issue / Remediation |
|---|---|---|---|---|---|---|
| **Soil Moisture (%)** | `mqtt_service.py` / `main.py` | `hybrid_farm_edge.db` (`telemetry_records`) | `GET /telemetry` | `SensorScreen`, `TelemetryScreen` | `LIVE_SENSOR` / `SIMULATED` | Must be tagged `SIMULATED` when ESP32 is running in simulator mode. Range checked (0–100%). Never defaulted to 0.0 when missing. |
| **Air Temperature (°C)** | `mqtt_service.py` / `main.py` | `hybrid_farm_edge.db` (`telemetry_records`) | `GET /telemetry` | `SensorScreen`, `TelemetryScreen` | `LIVE_SENSOR` / `SIMULATED` | Null-safe parsing. Out-of-range ADC flagged as `UNAVAILABLE`. |
| **Relative Humidity (%)** | `mqtt_service.py` / `main.py` | `hybrid_farm_edge.db` (`telemetry_records`) | `GET /telemetry` | `SensorScreen`, `TelemetryScreen` | `LIVE_SENSOR` / `SIMULATED` | Range checked (0–100%). Distinct from 0.0% when unmeasured. |
| **Soil Nitrogen (N) (mg/kg)** | `mqtt_service.py` (`payload.soil_n`) | `hybrid_farm_edge.db` (`telemetry_records`) | `GET /telemetry` | `SensorScreen`, `CropRecommendationScreen` | `LIVE_SENSOR` / `UNAVAILABLE` | If NPK probe is absent, returns `null` with label `Not measured`, never silent 0. |
| **Soil Phosphorus (P) (mg/kg)** | `mqtt_service.py` (`payload.soil_p`) | `hybrid_farm_edge.db` (`telemetry_records`) | `GET /telemetry` | `SensorScreen`, `CropRecommendationScreen` | `LIVE_SENSOR` / `UNAVAILABLE` | If NPK probe is absent, returns `null` with label `Not measured`. |
| **Soil Potassium (K) (mg/kg)** | `mqtt_service.py` (`payload.soil_k`) | `hybrid_farm_edge.db` (`telemetry_records`) | `GET /telemetry` | `SensorScreen`, `CropRecommendationScreen` | `LIVE_SENSOR` / `UNAVAILABLE` | If NPK probe is absent, returns `null` with label `Not measured`. |
| **Soil pH** | `mqtt_service.py` (`payload.soil_ph`) | `hybrid_farm_edge.db` (`telemetry_records`) | `GET /telemetry` | `SensorScreen`, `CropRecommendationScreen` | `LIVE_SENSOR` / `UNAVAILABLE` | Range checked (3.5–9.5). Marked `Not measured` if sensor absent. |
| **Device Battery (%)** | `mqtt_service.py` (`payload.battery_level`) | `hybrid_farm_edge.db` (`telemetry_records`) | `GET /telemetry`, `GET /api/devices/{id}/lifecycle` | `SensorScreen`, `SettingsScreen` | `LIVE_SENSOR` / `UNAVAILABLE` | Dynamic battery percentage; marked `UNAVAILABLE` if device packet does not include battery voltage. |
| **Device RSSI (dBm)** | `mqtt_service.py` (`payload.wifi_rssi`) | `hybrid_farm_edge.db` (`telemetry_records`) | `GET /telemetry` | `SensorScreen`, `SettingsScreen` | `LIVE_SENSOR` / `UNAVAILABLE` | Live Wi-Fi signal strength in dBm with freshness timestamp. |
| **Device Online / Offline Status** | `mqtt_service.py` (LWT & retained status) | In-memory + `hybrid_farm_edge.db` | `GET /ready`, `GET /api/devices/{id}/lifecycle` | `SensorScreen`, `SettingsScreen` | `LIVE_SENSOR` | Tracks MQTT LWT (Last Will and Testament) `agrisaathi/nodes/{id}/status`. Stale after 3 minutes without heartbeat. |
| **Recommended Crop** | `mlbackend/model.joblib` (RandomForest) | N/A (Trained ML Model) | `POST /api/recommend` | `CropRecommendationScreen` | `MODEL_PREDICTION` | Must cleanly separate static `test_accuracy` (99.1%) from dynamic `prediction_confidence`. |
| **Crop Prediction Confidence** | `model.predict_proba()` | N/A | `POST /api/recommend` | `CropRecommendationScreen` | `MODEL_PREDICTION` | Probability of top predicted class, formatted as percentage. Top 3 alternatives exposed. |
| **Model Test Accuracy** | Model evaluation benchmark | N/A | `POST /api/recommend`, `GET /models/status` | `CropRecommendationScreen` | `MODEL_PREDICTION` | Fixed at 99.1% (Kaggle Crop Recommendation Benchmark). Clearly labeled as benchmark accuracy. |
| **Leaf Disease Diagnosis** | `vision_model.joblib` (Ensemble) | N/A (Image Inference) | `POST /api/vision-diagnose` | `VisionScreen` | `EXPERIMENTAL` | Hybrid ensemble vision model. Honestly tagged `EXPERIMENTAL` in model registry. |
| **Irrigation Assessment & Recommendation** | `risk_engine.py` / `main.py` | Rules + sensor data | `POST /api/irrigation/assess` | `SensorScreen`, `PumpControlScreen` | `RULE_BASED` | Combines FAO-56 moisture deficit with rain forecast. |
| **Rain Lockout State** | `pump_controller.py` / `services.py` | OpenWeather forecast | `POST /pump/command`, `GET /api/weather-advice` | `SensorScreen`, `PumpControlScreen` | `LIVE_WEATHER` / `RULE_BASED` | Actuates lock when rain probability ≥ 50%. Clearly displays lockout reason to farmer. |
| **Pump Desired State** | `pump_controller.py` | `hybrid_farm_edge.db` (`pump_commands`) | `POST /pump/command`, `GET /pump/commands` | `PumpControlScreen`, `SensorScreen` | `RULE_BASED` / `USER_ACTION` | State requested by user/automation (`COMMAND_REQUESTED`, `COMMAND_PUBLISHED`). |
| **Pump Physical Reported State** | `mqtt_service.py` (`agrisaathi/nodes/{id}/telemetry`) | `hybrid_farm_edge.db` (`pump_commands`) | `GET /pump/commands/{id}` | `PumpControlScreen`, `SensorScreen` | `LIVE_SENSOR` | Only confirmed when ESP32 publishes execution acknowledgement (`EXECUTED`). |
| **Water Flow Rate (L/min)** | `mqtt_service.py` (`payload.flow_rate`) | `hybrid_farm_edge.db` (`telemetry_records`) | `GET /telemetry` | `PumpControlScreen` | `UNAVAILABLE` | Displayed as `Flow rate: Not measured` unless physical flow sensor is attached. Never fake `0.0 L/min`. |
| **Weather Temperature & Forecast** | OpenWeather API (`services.py`) | N/A (Live HTTP API) | `POST /api/weather-advice`, `POST /api/crop-risk` | `SensorScreen` | `LIVE_WEATHER` | Falls back gracefully to `UNAVAILABLE` if API key is not configured, preventing crashes. |
| **Multi-Agent Decision Advisory** | `agent_orchestrator.py` | RAG Knowledge Base + SQLite Memory | `POST /api/chat` | `DecisionScreen`, `ChatScreen` | `HYBRID` | Grounded multi-agent response with explicit provenance citation badges. |
| **In-App Notifications** | `internal_notifications.py` | `hybrid_farm_edge.db` (`notifications`) | `GET /notifications` | `AlertsScreen` | `RULE_BASED` / `SYSTEM_EVENT` | SQLite backed, decoupled from external SMS/Twilio. Full sync states (`PENDING`, `SYNCED`, `READ`). |
| **Offline Sync Queue** | `OfflineStore.ts` (AsyncStorage) | SQLite (`hybrid_farm_edge.db`) | `POST /notifications/sync` | `SettingsScreen`, `AlertsScreen` | `HISTORICAL_DATABASE` | Idempotent batch syncing with `client_action_id` deduplication. |

---

## Provenance Value Hierarchy & Standardization

All components must standardize on these 10 truthful provenance classes:

```
1. LIVE_SENSOR               - Live physical telemetry received from hardware node within freshness window (<3 min)
2. LIVE_WEATHER              - Live meteorology data from connected weather API provider
3. SOURCE_BACKED_KNOWLEDGE   - Curated agronomic research, ICAR/FAO publications, and extension guidelines
4. HISTORICAL_DATABASE       - Cached telemetry and previous crop records from local SQLite or Supabase
5. RULE_BASED                - Deterministic agronomic logic (e.g. FAO-56 irrigation thresholding, rain lockout)
6. MODEL_PREDICTION          - Machine learning inference output (e.g. Random Forest Crop Recommendation)
7. EXPERIMENTAL              - Research-grade ML models undergoing validation (e.g. Leaf Disease Vision Classifier)
8. SIMULATED                 - Test telemetry generated by ESP32 software simulator
9. UNAVAILABLE               - Data provider or physical sensor unconfigured or disconnected
10. STALE                    - Cached data whose freshness window has expired without new uplink packets
```
