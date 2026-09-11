# AgriSaathi AI — Jury Evidence & Verification Checklist (SIH26180)

This checklist provides verifiable evidence, source code locations, and truthful status ratings for all architectural components required by the Smart India Hackathon evaluation panel.

---

## 1. System Architecture & Model Provenance

| Component | Truthful Status | Evidence File & Reference | Notes / Verified Benchmarks |
|---|---|---|---|
| **Crop Recommendation Model** | `COMPLETED` | [`mlbackend/model.joblib`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/model.joblib), [`mlbackend/main.py#L324`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/main.py#L324) | Real trained Random Forest on 22 crops; 99.1% verified test accuracy. |
| **Leaf Disease Vision Model** | `EXPERIMENTAL` | [`mlbackend/training/train_vision.py`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/training/train_vision.py), [`mlbackend/model_providers.py`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/model_providers.py) | Active background training on 115,739 PlantDoc/PlantVillage images. Labeled `EXPERIMENTAL AI` on mobile UI. |
| **FAO-56 Irrigation Engine** | `RULE-BASED` | [`mlbackend/irrigation_engine.py`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/irrigation_engine.py), [`mlbackend/main.py#L1604`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/main.py#L1604) | Calculates daily ET0 and root-zone water balance with strict Rain Lockout interlock. |
| **Pest Predictor Engine** | `RULE-BASED` | [`mlbackend/pest_service.py`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/pest_service.py) | Evaluates heat-degree days and humidity thresholds for yellow stem borer & blast. |
| **NPK Nutrient Engine** | `RULE-BASED` | [`mlbackend/fertilizer_service.py`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/fertilizer_service.py) | Soil nutrient deficit calculator with null safety; never replaces missing data with zero. |
| **Agricultural RAG Engine** | `COMPLETED WITH LIMITATIONS` | [`mlbackend/agent_orchestrator.py`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/agent_orchestrator.py) | Hybrid grounded orchestrator; prioritizes live telemetry and falls back gracefully when knowledge base is unavailable. |

---

## 2. Edge Hardware, MQTT & Actuator Safety

| Component | Truthful Status | Evidence File & Reference | Notes / Verified Benchmarks |
|---|---|---|---|
| **MQTT Communication Layer** | `COMPLETED` | [`mlbackend/mqtt_service.py`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/mqtt_service.py), [`edge_hardware/mosquitto.conf`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/edge_hardware/mosquitto.conf) | Exact topics defined: `agrisaathi/farm/{farm}/zone/{zone}/telemetry` and `commands`. |
| **Actuator Pump Controller** | `COMPLETED` | [`mlbackend/pump_controller.py`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/pump_controller.py), [`mlbackend/main.py#L1730`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/main.py#L1730) | Full 4-stage lifecycle: `requested -> published -> acknowledged -> executed`. |
| **Rain Lockout Interlock** | `COMPLETED` | [`mlbackend/pump_controller.py#L90-L128`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/pump_controller.py#L90-L128) | Blocks pump activation when active rain is true or rainfall forecast exceeds 5.0mm. |
| **Qualcomm RB5 Edge Gateway** | `COMPLETED` | [`edge_hardware/qualcomm_edge_gateway.py`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/edge_hardware/qualcomm_edge_gateway.py) | Local inference edge daemon with SNPE/ONNX runtime compatibility. |
| **Null Safety Compliance** | `COMPLETED` | [`mlbackend/db_layer.py#L92-L148`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/db_layer.py#L92-L148) | Missing sensor fields stored as SQL NULL; never converted to 0 or arbitrary defaults. |

---

## 3. Database, Notifications & Offline Resilience

| Component | Truthful Status | Evidence File & Reference | Notes / Verified Benchmarks |
|---|---|---|---|
| **Internal Notification System** | `COMPLETED` | [`mlbackend/internal_notifications.py`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/internal_notifications.py) | 15 canonical event types; completely provider-independent; zero SMS/Twilio dependencies. |
| **Twilio Removal** | `COMPLETED` | Verified across repo | Deleted `twilio_ivr.py`, excised from `package.json`, `requirements.txt`, and `config.py`. |
| **Offline Idempotent Sync** | `COMPLETED` | [`mlbackend/db_layer.py#L151-L196`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/mlbackend/db_layer.py#L151-L196), [`android-app/src/services/OfflineStore.ts`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/android-app/src/services/OfflineStore.ts) | Enforces `client_action_id` deduplication to prevent duplicate database writes. |
| **Supabase Core Migration** | `READY FOR MANUAL STEP` | [`supabase/migrations/20260911_agrisaathi_core.sql`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/supabase/migrations/20260911_agrisaathi_core.sql) | 16 canonical PostgreSQL tables with RLS and foreign keys. |
| **Supabase Delta Migration** | `READY FOR MANUAL STEP` | [`supabase/migrations/20260911_notifications_and_sync.sql`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/supabase/migrations/20260911_notifications_and_sync.sql) | 4 tables: `notifications`, `notification_delivery`, `notification_read_state`, `offline_sync_events`. |

---

## 4. Mobile Application UX (Design Reference Alignment)

| Screen | Truthful Status | Evidence File | Features |
|---|---|---|---|
| **Sensor Dashboard** | `COMPLETED` | [`android-app/src/screens/SensorScreen.tsx`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/android-app/src/screens/SensorScreen.tsx) | "Hello, Ramesh!", Rain Lockout banner, 4 metric cards, pump status, FAO-56 card, 4 quick actions. |
| **Crop Recommendation** | `COMPLETED` | [`android-app/src/screens/CropRecommendationScreen.tsx`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/android-app/src/screens/CropRecommendationScreen.tsx) | ESP32 pre-fill, Random Forest 99.1% result, yield estimation, alternative candidates. |
| **Leaf Vision** | `COMPLETED` | [`android-app/src/screens/VisionScreen.tsx`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/android-app/src/screens/VisionScreen.tsx) | Scanning guide frame, `EXPERIMENTAL AI` badge, confidence bar, dual organic + chemical remedies. |
| **Alerts & Notifications** | `COMPLETED` | [`android-app/src/screens/AlertsScreen.tsx`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/android-app/src/screens/AlertsScreen.tsx) | Severity filter tabs, sync badge, read/resolve actions. |
| **Settings & Sync** | `COMPLETED` | [`android-app/src/screens/SettingsScreen.tsx`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/android-app/src/screens/SettingsScreen.tsx) | Farmer profile, language switcher, offline queue counter, backend API URL configuration. |
| **Telemetry Trends** | `COMPLETED` | [`android-app/src/screens/TelemetryScreen.tsx`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/android-app/src/screens/TelemetryScreen.tsx) | SVG area chart, time-range chips (1D/7D/30D), null-preserving table. |
| **Decision Engine** | `COMPLETED` | [`android-app/src/screens/DecisionScreen.tsx`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/android-app/src/screens/DecisionScreen.tsx) | 4-stage pipeline stepper, evidence checklist, re-evaluate button. |
| **Pump Actuator Control** | `COMPLETED` | [`android-app/src/screens/PumpControlScreen.tsx`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/android-app/src/screens/PumpControlScreen.tsx) | 4-stage lifecycle stepper, rain lockout blocked test, manual override switch. |
