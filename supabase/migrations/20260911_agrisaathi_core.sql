-- ============================================================================
-- AGRISAATHI AI — PRODUCTION DATABASE MIGRATION
-- Migration Name: 20260911_agrisaathi_core.sql
-- Description: Non-destructive, idempotent schema definition for cloud source of truth.
-- Author: AgriSaathi Engineering Team
-- Safety: Uses CREATE TABLE IF NOT EXISTS, conditional ALTER, and DO blocks.
-- ============================================================================

-- Enable required extensions safely
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ----------------------------------------------------------------------------
-- 1. PROFILES (Extends existing auth.users profile table)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    full_name TEXT,
    avatar_url TEXT,
    phone TEXT,
    role TEXT DEFAULT 'farmer' CHECK (role IN ('farmer', 'agronomist', 'admin', 'service_role')),
    preferred_language TEXT DEFAULT 'en',
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Ensure phone and role columns exist if table was previously created
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'phone') THEN
        ALTER TABLE public.profiles ADD COLUMN phone TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'role') THEN
        ALTER TABLE public.profiles ADD COLUMN role TEXT DEFAULT 'farmer';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'preferred_language') THEN
        ALTER TABLE public.profiles ADD COLUMN preferred_language TEXT DEFAULT 'en';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 2. FARMS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.farms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    location_lat DOUBLE PRECISION,
    location_lon DOUBLE PRECISION,
    total_acres NUMERIC(8,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_farms_profile_id ON public.farms(profile_id);

-- ----------------------------------------------------------------------------
-- 3. FARM ZONES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.farm_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES public.farms(id) ON DELETE CASCADE,
    zone_number INTEGER NOT NULL,
    crop TEXT NOT NULL,
    growth_stage TEXT DEFAULT 'Vegetative',
    soil_type TEXT DEFAULT 'Loamy',
    target_moisture_pct NUMERIC(5,2) DEFAULT 45.0,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    UNIQUE(farm_id, zone_number)
);

CREATE INDEX IF NOT EXISTS idx_farm_zones_farm_id ON public.farm_zones(farm_id);

-- ----------------------------------------------------------------------------
-- 4. DEVICES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT NOT NULL UNIQUE,
    profile_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    farm_id UUID REFERENCES public.farms(id) ON DELETE SET NULL,
    zone_id UUID REFERENCES public.farm_zones(id) ON DELETE SET NULL,
    display_name TEXT DEFAULT 'Field Sensor Node',
    hardware_version TEXT DEFAULT 'v1.0-ESP32',
    firmware_version TEXT DEFAULT 'v1.4.2',
    status TEXT DEFAULT 'unknown' CHECK (status IN ('online', 'offline', 'unknown', 'degraded')),
    last_seen_at TIMESTAMPTZ,
    last_online_at TIMESTAMPTZ,
    last_offline_at TIMESTAMPTZ,
    mqtt_uplink_topic TEXT DEFAULT 'agrisaathi/nodes/ESP32_NODE_01/telemetry',
    mqtt_downlink_topic TEXT DEFAULT 'agrisaathi/nodes/ESP32_NODE_01/commands',
    mqtt_status_topic TEXT DEFAULT 'agrisaathi/nodes/ESP32_NODE_01/status',
    capabilities JSONB DEFAULT '{"soil_moisture": true, "temperature": true, "humidity": true, "sunlight": true, "vibration": false, "npk": false}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_devices_device_id ON public.devices(device_id);
CREATE INDEX IF NOT EXISTS idx_devices_profile_id ON public.devices(profile_id);

-- ----------------------------------------------------------------------------
-- 5. DEVICE ZONE ASSIGNMENTS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.device_zone_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT NOT NULL REFERENCES public.devices(device_id) ON DELETE CASCADE,
    zone_id UUID NOT NULL REFERENCES public.farm_zones(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    unassigned_at TIMESTAMPTZ
);

-- ----------------------------------------------------------------------------
-- 6. TELEMETRY (Authoritative Ingestion Table)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.telemetry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT NOT NULL REFERENCES public.devices(device_id) ON DELETE CASCADE,
    farm_id UUID REFERENCES public.farms(id) ON DELETE SET NULL,
    zone_id UUID REFERENCES public.farm_zones(id) ON DELETE SET NULL,
    received_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    device_timestamp BIGINT,
    soil_moisture_pct NUMERIC(5,2) CHECK (soil_moisture_pct IS NULL OR (soil_moisture_pct >= 0 AND soil_moisture_pct <= 100)),
    soil_raw_adc INTEGER CHECK (soil_raw_adc IS NULL OR (soil_raw_adc >= 0 AND soil_raw_adc <= 4095)),
    temperature_c NUMERIC(5,2) CHECK (temperature_c IS NULL OR (temperature_c >= -10 AND temperature_c <= 60)),
    humidity_pct NUMERIC(5,2) CHECK (humidity_pct IS NULL OR (humidity_pct >= 0 AND humidity_pct <= 100)),
    sunlight_detected BOOLEAN,
    vibration_detected BOOLEAN,
    vibration_rms NUMERIC(8,4) CHECK (vibration_rms IS NULL OR vibration_rms >= 0),
    nitrogen NUMERIC(7,2) CHECK (nitrogen IS NULL OR nitrogen >= 0),
    phosphorus NUMERIC(7,2) CHECK (phosphorus IS NULL OR phosphorus >= 0),
    potassium NUMERIC(7,2) CHECK (potassium IS NULL OR potassium >= 0),
    pump_active BOOLEAN,
    edge_ai_result TEXT,
    edge_ai_confidence_pct NUMERIC(5,2) CHECK (edge_ai_confidence_pct IS NULL OR (edge_ai_confidence_pct >= 0 AND edge_ai_confidence_pct <= 100)),
    raw_payload JSONB NOT NULL,
    data_source TEXT DEFAULT 'MQTT_EDGE' CHECK (data_source IN ('MQTT_EDGE', 'HTTP_EDGE', 'SIMULATED', 'MANUAL_OVERRIDE')),
    ingestion_status TEXT DEFAULT 'VALID' CHECK (ingestion_status IN ('VALID', 'WARNING_OUT_OF_RANGE', 'MALFORMED', 'REPLAY')),
    validation_errors TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_telemetry_device_time ON public.telemetry(device_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_received_at ON public.telemetry(received_at DESC);

-- ----------------------------------------------------------------------------
-- 7. DEVICE STATUS EVENTS (Lifecycle Logging)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.device_status_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT NOT NULL REFERENCES public.devices(device_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN ('online', 'offline', 'reconnect', 'lwt_death', 'battery_low', 'sensor_fault')),
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_device_status_events_device ON public.device_status_events(device_id, created_at DESC);

-- ----------------------------------------------------------------------------
-- 8. ACTUATOR STATES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.actuator_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT NOT NULL UNIQUE REFERENCES public.devices(device_id) ON DELETE CASCADE,
    pump_active BOOLEAN DEFAULT false,
    mister_active BOOLEAN DEFAULT false,
    last_command_id TEXT,
    last_state_change_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- ----------------------------------------------------------------------------
-- 9. PUMP COMMANDS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pump_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    command_id TEXT NOT NULL UNIQUE,
    device_id TEXT NOT NULL REFERENCES public.devices(device_id) ON DELETE CASCADE,
    farm_id UUID REFERENCES public.farms(id) ON DELETE SET NULL,
    zone_id UUID REFERENCES public.farm_zones(id) ON DELETE SET NULL,
    requested_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    command_type TEXT NOT NULL CHECK (command_type IN ('PUMP_ON', 'PUMP_OFF', 'MISTER_ON', 'MISTER_OFF')),
    duration_sec INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'requested' CHECK (status IN ('requested', 'blocked', 'published', 'acknowledged', 'executed', 'failed', 'expired')),
    reason TEXT,
    rain_lockout BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    published_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    acknowledgement_payload JSONB,
    command_payload JSONB,
    idempotency_key TEXT UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_pump_commands_device ON public.pump_commands(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pump_commands_status ON public.pump_commands(status);

-- ----------------------------------------------------------------------------
-- 10. ALERTS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT REFERENCES public.devices(device_id) ON DELETE SET NULL,
    farm_id UUID REFERENCES public.farms(id) ON DELETE CASCADE,
    zone_id UUID REFERENCES public.farm_zones(id) ON DELETE SET NULL,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('DROUGHT_STRESS', 'WATERLOGGING', 'PEST_OUTBREAK', 'FUNGAL_RISK', 'DEVICE_OFFLINE', 'RAIN_LOCKOUT', 'SYSTEM_WARNING')),
    severity TEXT NOT NULL CHECK (severity IN ('INFO', 'LOW', 'MODERATE', 'HIGH', 'CRITICAL')),
    message TEXT NOT NULL,
    metadata JSONB,
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alerts_farm_severity ON public.alerts(farm_id, severity, acknowledged);

-- ----------------------------------------------------------------------------
-- 11. AI INFERENCE RECORDS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.ai_inference_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    model_status TEXT NOT NULL CHECK (model_status IN ('REAL_VERIFIED', 'RULE_BASED', 'SIMULATED', 'EXPERIMENTAL', 'HYBRID')),
    input_summary JSONB NOT NULL,
    output_summary JSONB NOT NULL,
    confidence NUMERIC(5,4),
    latency_ms INTEGER,
    evidence_sources TEXT[],
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_records_created ON public.ai_inference_records(created_at DESC);

-- ----------------------------------------------------------------------------
-- 12. MODEL REGISTRY
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name TEXT NOT NULL UNIQUE,
    model_version TEXT NOT NULL,
    model_status TEXT NOT NULL CHECK (model_status IN ('REAL_VERIFIED', 'RULE_BASED', 'SIMULATED', 'EXPERIMENTAL', 'HYBRID', 'UNVERIFIED')),
    framework TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    dataset_source TEXT NOT NULL,
    metrics JSONB DEFAULT '{}'::jsonb,
    input_format TEXT NOT NULL,
    output_format TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Seed truth-audited models safely
INSERT INTO public.model_registry (model_name, model_version, model_status, framework, dataset_name, dataset_source, metrics, input_format, output_format, description)
VALUES 
    ('Crop Recommendation Classifier', '1.0.0', 'REAL_VERIFIED', 'scikit-learn RandomForestClassifier', 'Precision Agriculture 2,200 Rows', 'Kaggle / Agronomy Open Repository', '{"accuracy": 0.991, "macro_f1": 0.992}'::jsonb, 'N, P, K, temp, humidity, ph, rainfall', 'Recommended Crop (22 Classes)', 'Verified production model recommending optimal crop based on soil and climate.'),
    ('Leaf Disease Vision Ensemble', '2.5.0-Experimental', 'EXPERIMENTAL', 'scikit-learn VotingClassifier', 'Synthetic 20-row Feature Array', 'Repository Synthetic Seed (Pending PlantVillage)', '{"warning": "Not validated for field deployment"}'::jsonb, 'Greenness, Yellowing, Browning, Texture, Soil Moisture, Air Humidity', 'Disease Diagnosis Label', 'Experimental prototype classifier for leaf pathology features.'),
    ('Evapotranspiration Irrigation Engine', '2.0.0', 'RULE_BASED', 'FAO-56 Penman-Monteith Algorithm', 'FAO Irrigation & Drainage Paper No. 56', 'United Nations FAO Agronomy Guidelines', '{"standard": "FAO-56"}'::jsonb, 'Soil Moisture, Temp, Humidity, Rain Forecast', 'Irrigation Decision & Water Depth (mm)', 'Mathematical agronomic engine balancing soil moisture deficit and weather forecasts.'),
    ('Pest Acceleration Predictor', '1.1.0', 'RULE_BASED', 'Pest Population Velocity Curves', 'ICAR Integrated Pest Management Manuals', 'ICAR Extension Bulletins', '{"standard": "ICAR-IPM"}'::jsonb, 'Crop, Growth Stage, Temp, Humidity, Pest Count History', 'Pest Threat Level & Remediation', 'Rule-based threshold and second-derivative population acceleration engine.')
ON CONFLICT (model_name) DO UPDATE 
SET model_status = EXCLUDED.model_status, metrics = EXCLUDED.metrics, updated_at = NOW();

-- ----------------------------------------------------------------------------
-- 13. RAG DOCUMENTS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT,
    publication_date TEXT,
    crop TEXT DEFAULT 'General',
    region TEXT DEFAULT 'National',
    topic TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Seed trusted documents safely
INSERT INTO public.rag_documents (doc_id, title, source, url, publication_date, crop, region, topic, language, content)
VALUES
    ('doc_icar_rice_01', 'ICAR Package of Practices for Rice Water & Irrigation Management', 'ICAR - Indian Institute of Rice Research (IIRR)', 'https://www.icar-iirr.org/advisories/water_management.pdf', '2025-06-10', 'Rice', 'National', 'irrigation', 'en', 'During vegetative stage, maintain shallow standing water of 2-3 cm. Alternate Wetting and Drying (AWD) saves up to 30% water without yield reduction. Discontinue irrigation 10-15 days prior to harvest.'),
    ('doc_icar_rice_disease_02', 'ICAR Integrated Disease Management in Rice Crops', 'ICAR - Central Rice Research Institute (CRRI)', 'https://icar-nrri.in/disease_guidelines.pdf', '2025-08-04', 'Rice', 'National', 'disease_management', 'en', 'Brown Spot symptoms appear as oval reddish-brown lesions with grey centers. Apply spray of Carbendazim + Mancozeb (2 g/L) or Trichoderma viride bio-fungicide (5 g/L). Avoid excess Nitrogen application during humid weather.'),
    ('doc_imd_heatwave_03', 'IMD Agromet Heatwave & Thermal Stress Management Guidelines', 'India Meteorological Department (IMD)', 'https://mausam.imd.gov.in/agromet/bulletin.pdf', '2026-02-15', 'Wheat', 'North India', 'climate_resilience', 'en', 'To mitigate terminal heat stress in wheat during grain filling, apply light frequent irrigation. Potassium Nitrate (13-0-45) spray at 0.5% concentration improves osmotic tolerance during heatwaves exceeding 35°C.'),
    ('doc_fao_irrigation_04', 'FAO Irrigation Guidelines — Penman-Monteith Crop Evapotranspiration', 'Food and Agriculture Organization (FAO)', 'https://www.fao.org/land-water/databases-and-software/cropwat/en/', '2024-01-20', 'General', 'Global', 'irrigation', 'en', 'Crop water requirement ETc equals ET0 multiplied by Kc (crop coefficient). For vegetative paddy rice, Kc is 1.15. Irrigation scheduling must account for effective rainfall P_eff = P_rain * 0.8.')
ON CONFLICT (doc_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 14. CONVERSATION SESSIONS & MESSAGES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL UNIQUE,
    title TEXT DEFAULT 'AgriSaathi Farming Advice',
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

CREATE TABLE IF NOT EXISTS public.conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL REFERENCES public.conversation_sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant')),
    content TEXT NOT NULL,
    context_snapshot JSONB,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conv_messages_session ON public.conversation_messages(session_id, created_at ASC);

-- ----------------------------------------------------------------------------
-- 15. OFFLINE SYNC QUEUE
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.offline_sync_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    device_id TEXT NOT NULL,
    client_action_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_offline_sync_client_action ON public.offline_sync_queue(client_action_id);

-- ----------------------------------------------------------------------------
-- 16. AUDIT EVENTS (Immutable System Ledger)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_events_created ON public.audit_events(created_at DESC);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- Strict auth.uid() isolation across all farmer entities
-- ============================================================================

-- Profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can read own profile" ON public.profiles;
CREATE POLICY "Users can read own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);
DROP POLICY IF EXISTS "Users can insert own profile" ON public.profiles;
CREATE POLICY "Users can insert own profile" ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);

-- Farms
ALTER TABLE public.farms ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Farmers can view own farms" ON public.farms;
CREATE POLICY "Farmers can view own farms" ON public.farms FOR SELECT USING (auth.uid() = profile_id);
DROP POLICY IF EXISTS "Farmers can insert own farms" ON public.farms;
CREATE POLICY "Farmers can insert own farms" ON public.farms FOR INSERT WITH CHECK (auth.uid() = profile_id);
DROP POLICY IF EXISTS "Farmers can update own farms" ON public.farms;
CREATE POLICY "Farmers can update own farms" ON public.farms FOR UPDATE USING (auth.uid() = profile_id);
DROP POLICY IF EXISTS "Farmers can delete own farms" ON public.farms;
CREATE POLICY "Farmers can delete own farms" ON public.farms FOR DELETE USING (auth.uid() = profile_id);

-- Farm Zones
ALTER TABLE public.farm_zones ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Farmers can view zones in own farms" ON public.farm_zones;
CREATE POLICY "Farmers can view zones in own farms" ON public.farm_zones FOR SELECT 
    USING (EXISTS (SELECT 1 FROM public.farms WHERE farms.id = farm_zones.farm_id AND farms.profile_id = auth.uid()));
DROP POLICY IF EXISTS "Farmers can insert zones in own farms" ON public.farm_zones;
CREATE POLICY "Farmers can insert zones in own farms" ON public.farm_zones FOR INSERT 
    WITH CHECK (EXISTS (SELECT 1 FROM public.farms WHERE farms.id = farm_zones.farm_id AND farms.profile_id = auth.uid()));

-- Devices
ALTER TABLE public.devices ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Farmers can view own devices" ON public.devices;
CREATE POLICY "Farmers can view own devices" ON public.devices FOR SELECT USING (auth.uid() = profile_id);
DROP POLICY IF EXISTS "Farmers can update own devices" ON public.devices;
CREATE POLICY "Farmers can update own devices" ON public.devices FOR UPDATE USING (auth.uid() = profile_id);

-- Telemetry
ALTER TABLE public.telemetry ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Farmers can view telemetry from own devices" ON public.telemetry;
CREATE POLICY "Farmers can view telemetry from own devices" ON public.telemetry FOR SELECT 
    USING (EXISTS (SELECT 1 FROM public.devices WHERE devices.device_id = telemetry.device_id AND devices.profile_id = auth.uid()));

-- Pump Commands
ALTER TABLE public.pump_commands ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Farmers can view own pump commands" ON public.pump_commands;
CREATE POLICY "Farmers can view own pump commands" ON public.pump_commands FOR SELECT USING (auth.uid() = requested_by);
DROP POLICY IF EXISTS "Farmers can insert own pump commands" ON public.pump_commands;
CREATE POLICY "Farmers can insert own pump commands" ON public.pump_commands FOR INSERT WITH CHECK (auth.uid() = requested_by);

-- Alerts
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Farmers can view own alerts" ON public.alerts;
CREATE POLICY "Farmers can view own alerts" ON public.alerts FOR SELECT 
    USING (EXISTS (SELECT 1 FROM public.farms WHERE farms.id = alerts.farm_id AND farms.profile_id = auth.uid()));

-- Conversation Sessions & Messages
ALTER TABLE public.conversation_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Farmers can view own conversation sessions" ON public.conversation_sessions;
CREATE POLICY "Farmers can view own conversation sessions" ON public.conversation_sessions FOR SELECT USING (auth.uid() = profile_id);
DROP POLICY IF EXISTS "Farmers can insert own conversation sessions" ON public.conversation_sessions;
CREATE POLICY "Farmers can insert own conversation sessions" ON public.conversation_sessions FOR INSERT WITH CHECK (auth.uid() = profile_id);

ALTER TABLE public.conversation_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Farmers can view own conversation messages" ON public.conversation_messages;
CREATE POLICY "Farmers can view own conversation messages" ON public.conversation_messages FOR SELECT 
    USING (EXISTS (SELECT 1 FROM public.conversation_sessions WHERE conversation_sessions.session_id = conversation_messages.session_id AND conversation_sessions.profile_id = auth.uid()));

-- Model Registry & RAG Documents (Publicly readable by all authenticated users, modifications restricted)
ALTER TABLE public.model_registry ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone authenticated can view model registry" ON public.model_registry;
CREATE POLICY "Anyone authenticated can view model registry" ON public.model_registry FOR SELECT TO authenticated USING (true);

ALTER TABLE public.rag_documents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone authenticated can view rag documents" ON public.rag_documents;
CREATE POLICY "Anyone authenticated can view rag documents" ON public.rag_documents FOR SELECT TO authenticated USING (true);

-- Offline Sync Queue
ALTER TABLE public.offline_sync_queue ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view own offline sync queue" ON public.offline_sync_queue;
CREATE POLICY "Users can view own offline sync queue" ON public.offline_sync_queue FOR SELECT USING (auth.uid() = profile_id);
DROP POLICY IF EXISTS "Users can insert own offline sync actions" ON public.offline_sync_queue;
CREATE POLICY "Users can insert own offline sync actions" ON public.offline_sync_queue FOR INSERT WITH CHECK (auth.uid() = profile_id);

-- Audit Events (Read-only for actor, writes only from backend/service_role)
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view own audit logs" ON public.audit_events;
CREATE POLICY "Users can view own audit logs" ON public.audit_events FOR SELECT USING (auth.uid() = actor_id);
