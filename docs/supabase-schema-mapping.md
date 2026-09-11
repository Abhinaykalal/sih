# AgriSaathi AI — Supabase Database Schema Mapping
**Version**: 1.0.0 | **Migration Reference**: `20260911_agrisaathi_core.sql`

---

## 1. Overview & Architectural Principle

The AgriSaathi AI database topology employs a **Hybrid Offline-Edge + Cloud Source-of-Truth** model:
- **Cloud Database (Supabase PostgreSQL)**: Authoritative cloud store for multi-farmer accounts, farms, zones, registered devices, verified telemetry time-series, pump actuation records, and conversation history.
- **Local SQLite Stores**: Local cache and offline buffers running on the FastAPI edge backend (`mlbackend/farm_analytics.db`, `hybrid_farm_edge.db`, and `conversation_memory.db`).
- **Android Local Cache**: Encrypted React Native `AsyncStorage` cache for offline field operation.

---

## 2. Legacy SQLite to Supabase Entity Mapping

| SQLite Table / Concept | Local SQLite File | Supabase PostgreSQL Table | Notes & Schema Enhancements |
| :--- | :--- | :--- | :--- |
| `farmer_profiles` | `hybrid_farm_edge.db` | `public.profiles` | Linked to `auth.users(id)` via UUID with role-based access control. |
| *None* (Implicit) | *N/A* | `public.farms` | Introduces multi-farm spatial boundaries, location lat/lon, and acreage. |
| `zone_states` | `farm_analytics.db` | `public.farm_zones` | Explicit relational model connecting zones to farms with target moisture. |
| *None* (Hardcoded) | *N/A* | `public.devices` | First-class device registry with capabilities JSONB, hardware/firmware versions. |
| `telemetry` | `farm_analytics.db` | `public.telemetry` | Full telemetry table supporting 12-bit ADC, sunlight, vibration, NPK, edge AI. |
| `sync_queue` / `offline_sync_queue`| Both local DBs | `public.offline_sync_queue` | Idempotent sync queue indexed by `client_action_id` to eliminate replays. |
| *None* | *N/A* | `public.pump_commands` | Actuator command lifecycle tracking (`requested` -> `published` -> `acknowledged` -> `executed`). |
| *None* (In-memory cooldowns) | `main.py` | `public.alerts` | Persistent alerts with severity (`CRITICAL`, `HIGH`, `INFO`) and acknowledgment. |
| `messages` | `conversation_memory.db` | `public.conversation_messages`| Linked to `conversation_sessions` with sliding context window support. |
| *In-memory list* | `model_registry.py` | `public.model_registry` | Truth-audited model inventory tracking genuine training statuses. |
| *In-memory list* | `rag_engine.py` | `public.rag_documents` | ICAR, IMD, and FAO agricultural extension advisories. |
| *None* | *N/A* | `public.audit_events` | Immutable security and actuation audit log for compliance. |

---

## 3. Hardware Payload to Supabase Ingestion Column Mapping

The incoming ESP32 MQTT JSON payload maps directly to `public.telemetry`:

```json
{
  "device_id": "ESP32_NODE_01",
  "timestamp": 1726014600,
  "telemetry": {
    "soil_moisture_pct": 65,
    "soil_raw_adc": 1450,
    "temperature_c": 28.5,
    "humidity_pct": 60,
    "sunlight_detected": true
  },
  "actuator": {
    "pump_active": false
  },
  "edge_ai": {
    "last_scan_result": "Early Blight",
    "confidence_pct": 89
  }
}
```

| Inbound JSON Path | Supabase Column | Data Type | Constraint & Null Rule |
| :--- | :--- | :--- | :--- |
| `device_id` | `device_id` | `TEXT` | References `devices(device_id)`, NOT NULL |
| `timestamp` | `device_timestamp` | `BIGINT` | Secondary edge timestamp, nullable |
| *(Generated at ingestion)* | `received_at` | `TIMESTAMPTZ` | Authoritative backend time (`NOW()`), NOT NULL |
| `telemetry.soil_moisture_pct` | `soil_moisture_pct` | `NUMERIC(5,2)` | Checked between 0 and 100, nullable |
| `telemetry.soil_raw_adc` | `soil_raw_adc` | `INTEGER` | Checked between 0 and 4095, nullable |
| `telemetry.temperature_c` | `temperature_c` | `NUMERIC(5,2)` | Checked between -10 and 60, nullable |
| `telemetry.humidity_pct` | `humidity_pct` | `NUMERIC(5,2)` | Checked between 0 and 100, nullable |
| `telemetry.sunlight_detected` | `sunlight_detected` | `BOOLEAN` | Nullable |
| `telemetry.vibration_detected` | `vibration_detected`| `BOOLEAN` | Optional, nullable |
| `telemetry.vibration_rms` | `vibration_rms` | `NUMERIC(8,4)` | Optional, checked $\ge 0$, nullable |
| `telemetry.nitrogen` | `nitrogen` | `NUMERIC(7,2)` | Optional, checked $\ge 0$, nullable |
| `telemetry.phosphorus` | `phosphorus` | `NUMERIC(7,2)` | Optional, checked $\ge 0$, nullable |
| `telemetry.potassium` | `potassium` | `NUMERIC(7,2)` | Optional, checked $\ge 0$, nullable |
| `actuator.pump_active` | `pump_active` | `BOOLEAN` | Nullable |
| `edge_ai.last_scan_result` | `edge_ai_result` | `TEXT` | Nullable |
| `edge_ai.confidence_pct` | `edge_ai_confidence_pct`| `NUMERIC(5,2)` | Checked between 0 and 100, nullable |
| *(Entire incoming packet)* | `raw_payload` | `JSONB` | Stored verbatim for audit provenance |
| *(Source classification)* | `data_source` | `TEXT` | `'MQTT_EDGE'`, `'HTTP_EDGE'`, `'SIMULATED'` |
| *(Validation check)* | `ingestion_status` | `TEXT` | `'VALID'`, `'WARNING_OUT_OF_RANGE'`, etc. |
