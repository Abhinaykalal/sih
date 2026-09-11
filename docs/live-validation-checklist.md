# AgriSaathi AI — Live Hardware & Cloud Validation Checklist

**Date**: 2026-09-11  
**Scope**: Manual steps required for complete end-to-end physical hardware and cloud deployment  

---

## 1. Supabase Cloud Database Deployment
- [ ] Connect production Supabase project via environment variables:
  ```env
  SUPABASE_URL=https://your-project.supabase.co
  SUPABASE_KEY=your-supabase-service-role-key
  ```
- [ ] Run migration scripts located in `supabase/migrations/`:
  - `20260908_initial_schema.sql` (RLS policies, farm ownership, telemetry tables)
  - `20260909_offline_sync.sql` (Idempotent sync log, audit records)
- [ ] Verify Row Level Security (RLS) policies prevent unauthorized tenant access across farms.

---

## 2. MQTT Broker & Edge Gateway Pairing
- [ ] Start production Mosquitto broker on LAN / Cloud:
  ```bash
  mosquitto -c edge_hardware/mosquitto.conf -v
  ```
- [ ] Verify exact MQTT topics:
  - Uplink: `agrisaathi/nodes/ESP32_NODE_01/telemetry`
  - Downlink: `agrisaathi/nodes/ESP32_NODE_01/commands`
  - Status / LWT: `agrisaathi/nodes/ESP32_NODE_01/status`
- [ ] Launch Qualcomm Robotics RB5 edge gateway script:
  ```bash
  python edge_hardware/qualcomm_edge_gateway.py
  ```

---

## 3. Physical ESP32 Hardware Testing
- [ ] Flash ESP32 Node 01 with production firmware.
- [ ] Confirm capacitive soil moisture sensor calibration (0–100%).
- [ ] Confirm physical relay triggers within 2 seconds upon receiving `PUMP_ON` downlink command.
- [ ] Verify ESP32 transmits `PUMP_ON` execution confirmation packet back to broker.
- [ ] Test physical rain sensor disconnect and ensure Rain Lockout activates.
