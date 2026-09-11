# AgriSaathi AI — Deployment & Production Operations Guide
**Document Version**: 2.0.0 | **Authoritative Specification**: SIH26180 AgriSaathi AI

---

## 1. Architectural Overview

AgriSaathi AI deployment is structured across 4 decoupled production layers:

1. **FastAPI Backend**: Hosts AI/ML inference, multi-agent orchestrator, MQTT bridge, actuator pump controller, and Supabase synchronization.
2. **Next.js Web Application**: Farmer and agronomist operations dashboard.
3. **Supabase PostgreSQL Cloud DB**: Persistent storage, Row-Level Security (RLS), authentication, and realtime websocket sync.
4. **Android Native/React Native Mobile App**: Mobile companion for farmers with offline action queue and live sensor telemetry.

---

## 2. FastAPI Backend Deployment

### Option A: Containerized Deployment (Docker / VPS / AWS EC2)
```bash
# 1. Build Docker image
docker build -t agrisaathi-backend:latest .

# 2. Run container with production environment
docker run -d \
  -p 8000:8000 \
  --name agrisaathi-backend \
  --env-file .env \
  agrisaathi-backend:latest
```

### Option B: Railway / Render (Procfile Provided)
The repository contains `Procfile` and `railway.toml`:
- **Start Command**: `uvicorn mlbackend.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/health`
- **Readiness Check Path**: `/ready`

### Required Backend Environment Variables:
```ini
PORT=8000
ENFORCE_JWT_AUTH=false # Set to true when authenticating farmer sessions
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_KEY=<your-supabase-service-role-key>
SUPABASE_JWT_SECRET=<your-supabase-jwt-secret>
MQTT_BROKER_HOST=broker.hivemq.com # or private TLS broker
MQTT_BROKER_PORT=1883
MQTT_UPLINK_TOPIC=agrisaathi/nodes/ESP32_NODE_01/telemetry
MQTT_DOWNLINK_TOPIC=agrisaathi/nodes/ESP32_NODE_01/commands
MQTT_STATUS_TOPIC=agrisaathi/nodes/ESP32_NODE_01/status
OPENWEATHER_API_KEY=<optional-openweather-key>
TWILIO_ACCOUNT_SID=<optional-twilio-sid>
TWILIO_AUTH_TOKEN=<optional-twilio-token>
TWILIO_FROM_NUMBER=<optional-twilio-phone>
TELEGRAM_BOT_TOKEN=<optional-telegram-bot-token>
```

---

## 3. Web Application Deployment (Vercel)

The Next.js web application is pre-configured for Vercel deployment:

```bash
# Deploy to Vercel via CLI
npx vercel --prod
```

### Required Web Frontend Environment Variables:
```ini
NEXT_PUBLIC_API_BASE_URL=https://<your-backend-domain>.com
NEXT_PUBLIC_SUPABASE_URL=https://<your-project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-supabase-anon-key>
```

---

## 4. Supabase Database Setup

Follow `docs/supabase-migration-guide.md`:
1. Execute `supabase/migrations/20260911_agrisaathi_core.sql` in the Supabase Dashboard SQL Editor.
2. Verify table creation and RLS activation.
3. Current execution state: `READY — AWAITING MANUAL SQL EXECUTION`.

---

## 5. MQTT Broker Setup

- **Production Cloud Broker**: HiveMQ Cloud (Free 100 devices with TLS 8883) or EMQX Cloud.
- **Local / Edge Testing**: Eclipse Mosquitto via `docker-compose up mqtt-broker`.
- **Topics**:
  - Telemetry: `agrisaathi/nodes/ESP32_NODE_01/telemetry`
  - Actuator Commands: `agrisaathi/nodes/ESP32_NODE_01/commands`
  - Node Status: `agrisaathi/nodes/ESP32_NODE_01/status`

---

## 6. Verification Probes

Verify deployment health:
```bash
# 1. Liveness
curl https://<backend-host>/health

# 2. Readiness
curl https://<backend-host>/ready

# 3. Version and Specification
curl https://<backend-host>/version

# 4. Model Registry Transparency
curl https://<backend-host>/models/status
```
