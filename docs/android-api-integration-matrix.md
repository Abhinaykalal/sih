# AgriSaathi AI — Android API Integration Matrix

**Date**: 2026-09-11  
**Auditor**: AgriSaathi AI Verification Pipeline  
**Specification**: SIH26180 Precision Agriculture Mobile Integration  

---

## Complete Screen-to-API Integration Matrix

| Screen | API Endpoint | Request Schema | Response Schema | Live Source | Loading State | Error State | Offline State | Hardcoded Values Removed |
|---|---|---|---|---|---|---|---|---|
| **SensorScreen (Dashboard)** | `GET /telemetry?device_id=ESP32_NODE_01` | Query: `device_id`, `limit=1` | Array/Object of `telemetry_records` with moisture, temp, humidity, NPK, battery, RSSI, rain | `LIVE_SENSOR` / `SIMULATED` | `ActivityIndicator` + Pull-to-Refresh | Offline Banner fallback to SQLite cache | Local SQLite cached record | Fixed static "Updated 2s ago" with dynamic relative timestamp; flow rate honestly marked "Not measured" |
| **SensorScreen (Weather)** | `POST /api/weather-advice` | `{ lat: float, lon: float, crop: string }` | `{ weather_status, temp, humidity, rainfall_mm, rain_probability_pct, upcoming_threats }` | `LIVE_WEATHER` / `UNAVAILABLE` | Graceful default cards | Fallback to UNAVAILABLE with reason | Cached weather advice | Static rainfall & weather conditions replaced by live OpenWeather responses with null-safety |
| **CropRecommendationScreen** | `POST /api/recommend` | `CropFeatures` (`N, P, K, temperature, humidity, ph, rainfall, lang`) | `RecommendationResponse` (`recommended_crop, prediction_confidence, test_accuracy, alternative_crops, warnings`) | `MODEL_PREDICTION` | Inline button spinner | Error banner with validation guidance | Offline notice with manual entry option | Removed conflation of 99.1% test accuracy with prediction confidence; added top 3 alternative crops |
| **PumpControlScreen** | `GET /pump/state`, `POST /pump/command` | `PumpCommandRequest` (`device_id, command_type, duration_sec, reason, manual_override`) | `PumpCommandResult` (`command_id, status, rain_lockout, reason, created_at`) | `LIVE_SENSOR` / `RULE_BASED` | Button loading indicator | Lockout alert dialog with override option | Queue to offline store | Removed fake 24.5 L/min flow rate (now "Not measured"); implemented audited emergency override |
| **AlertsScreen** | `GET /notifications` | Query: `severity, unread_only, limit` | `List[NotificationRecord]` (`id, title, message, severity, created_at, read_at`) | `RULE_BASED` / `SYSTEM_EVENT` | Full-screen spinner | Retry action button | Cached notification list | Removed developer-centric Twilio excision jargon into system info/settings page |
| **DecisionScreen** | `POST /api/chat`, `POST /api/irrigation/assess` | `{ message, crop, stage, field_id }` | `{ answer, intent, evidence, telemetry_source, provenance }` | `HYBRID` (`RAG + SENSOR`) | Inline evaluation spinner | Fallback to rule-based FAO-56 stage | Stored local guidance | Static determination grounded in live moisture and weather risk |
| **VisionScreen** | `POST /api/vision-diagnose` | `{ image: base64, crop_type, growth_stage }` | `{ disease, pathogen, severity, confidence, organic_treatment, chemical_treatment }` | `EXPERIMENTAL` | In-viewfinder spinner | Diagnostic error banner | Standard disease profile | Labeled honestly as EXPERIMENTAL in accordance with model registry |
| **TelemetryScreen** | `GET /telemetry?device_id=ESP32_NODE_01&limit=20` | Query: `device_id`, `limit=20` | `List[telemetry_records]` with timestamps | `HISTORICAL_DATABASE` | Chart loading placeholder | Fallback data points | Cached time-series buffer | Preserves null values distinctly from zero |
| **SettingsScreen** | `GET /health`, `POST /api/offline-sync` | `OfflineSyncRequest` (`deviceId, queuedActions`) | Sync results with `processed_count, duplicate_skipped_count` | `HISTORICAL_DATABASE` | Syncing spinner | Connection error banner | Displays queued action count | Backend URL switcher tested live |

---

## Data Freshness & Stale-Data Protocol

1. **Active Threshold**: Packets received within < 180 seconds are tagged `LIVE_SENSOR`.
2. **Stale Threshold**: Packets older than 180 seconds are tagged `STALE` with elapsed time displayed to the farmer.
3. **Missing Metrics**: If an individual sensor channel (such as NPK or Flow Rate) is not equipped on the node, it is returned as `null` and displayed as `Not measured` or `Unavailable`, never converted to zero.
