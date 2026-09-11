# AgriSaathi AI — Supabase Database Migration & Verification Guide (Phase 4)

## Overview
This document guides the operator through verifying and applying the Supabase PostgreSQL database schemas for AgriSaathi AI.

- **Status**: `READY FOR MANUAL STEP` (Local mock & SQLite offline cache verified; Cloud execution requires live Supabase credentials)
- **Primary Migration**: [`supabase/migrations/20260911_agrisaathi_core.sql`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/supabase/migrations/20260911_agrisaathi_core.sql) (16 tables)
- **Delta Migration**: [`supabase/migrations/20260911_notifications_and_sync.sql`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/supabase/migrations/20260911_notifications_and_sync.sql) (4 tables)

---

## 1. Table Architecture

### Core Tables (20260911_agrisaathi_core.sql)
1. `profiles`: Farmer user identity, language preferences, phone, role.
2. `farms`: Agricultural farm boundary, GPS coordinates, soil type, total acres.
3. `farm_zones`: Sub-divided zones/plots with primary crop and target moisture thresholds.
4. `devices`: Edge IoT hardware (ESP32, Qualcomm RB5 gateway) with battery, RSSI, status.
5. `device_zone_assignments`: Mapping between edge nodes and farm zones.
6. `telemetry`: Time-series sensor packets (moisture, temp, humidity, NPK, vibration, rain).
7. `device_status_events`: Online/offline connectivity transitions.
8. `actuator_states`: Current relay status of pumps, valves, and misting hardware.
9. `pump_commands`: Audit trail of actuator actions (requested, published, acknowledged, executed) with rain lockout safety.
10. `alerts`: System, agricultural, and safety alerts.
11. `ai_inference_records`: Audit log of all model inferences (vision, crop recommendation, irrigation).
12. `model_registry`: Model metadata, weights versioning, provenance, accuracy benchmark tags.
13. `rag_documents`: Vector embeddings and agricultural knowledge base texts.
14. `conversation_sessions`: LLM advisor dialogue sessions.
15. `conversation_messages`: Multilingual message history.
16. `audit_events`: System compliance and security audit logs.

### Notifications & Offline Sync Delta (20260911_notifications_and_sync.sql)
17. `notifications`: Canonical provider-independent notifications across all 15 event types.
18. `notification_delivery`: Multi-channel delivery ledger (In-App, TTS, Edge Relay).
19. `notification_read_state`: Per-user read receipt markers.
20. `offline_sync_events`: Idempotent action queue tracking `client_action_id` to guarantee zero duplicate executions upon network reconnection.

---

## 2. Step-by-Step Manual Execution

### Method A: Via Supabase Dashboard (Recommended)
1. Log in to [Supabase Dashboard](https://supabase.com/dashboard).
2. Open your AgriSaathi project.
3. Navigate to **SQL Editor** in the left sidebar.
4. Paste and execute `supabase/migrations/20260911_agrisaathi_core.sql`.
5. Paste and execute `supabase/migrations/20260911_notifications_and_sync.sql`.
6. Confirm all 20 tables appear under **Table Editor**.

### Method B: Via Supabase CLI
```bash
supabase db push
# or
supabase migration up
```

---

## 3. Verification Queries

Run the following SQL snippet in the Supabase SQL Editor to verify tables and RLS status:

```sql
SELECT 
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
```

Expected result: All 20 tables listed with `rowsecurity = true`.

---

## 4. Offline Fallback Behavior
When `SUPABASE_URL` and `SUPABASE_KEY` are unset or network is offline, AgriSaathi automatically routes all telemetry, notifications, and pump commands through local SQLite databases (`farm_analytics.db` and `hybrid_farm_edge.db`). Zero telemetry or command loss occurs.
