-- AgriSaathi AI: Phase 4 Delta Migration
-- Provider-Independent Canonical Notifications & Offline Client Synchronization
-- Idempotent, safe for multiple executions (CREATE TABLE IF NOT EXISTS, DO blocks)

-- 1. Canonical Notifications Table
CREATE TABLE IF NOT EXISTS public.notifications (
    id TEXT PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    farm_id UUID REFERENCES public.farms(id) ON DELETE SET NULL,
    zone_id UUID REFERENCES public.farm_zones(id) ON DELETE SET NULL,
    device_id TEXT,
    notification_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('INFO', 'LOW', 'MODERATE', 'WARNING', 'HIGH', 'CRITICAL')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    read_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    source_event_id TEXT UNIQUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    synced_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON public.notifications(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON public.notifications(notification_type);
CREATE INDEX IF NOT EXISTS idx_notifications_source_event ON public.notifications(source_event_id);

-- 2. Notification Delivery Tracking (Multi-Channel / In-App / Hardware Relay)
CREATE TABLE IF NOT EXISTS public.notification_delivery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id TEXT NOT NULL REFERENCES public.notifications(id) ON DELETE CASCADE,
    channel TEXT NOT NULL CHECK (channel IN ('IN_APP_BANNER', 'VOICE_TTS', 'EDGE_RELAY', 'SYSTEM_PUSH')),
    delivery_status TEXT NOT NULL DEFAULT 'DELIVERED' CHECK (delivery_status IN ('PENDING', 'DELIVERED', 'FAILED', 'EXPIRED')),
    delivered_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    failure_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_delivery_notif_id ON public.notification_delivery(notification_id);

-- 3. Notification Read State (Per User Tracking)
CREATE TABLE IF NOT EXISTS public.notification_read_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    notification_id TEXT NOT NULL REFERENCES public.notifications(id) ON DELETE CASCADE,
    read_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT uq_user_notif_read UNIQUE (user_id, notification_id)
);

CREATE INDEX IF NOT EXISTS idx_read_state_user ON public.notification_read_state(user_id);

-- 4. Offline Sync Events (Idempotent Client Action Queue)
CREATE TABLE IF NOT EXISTS public.offline_sync_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_action_id TEXT UNIQUE NOT NULL,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    device_id TEXT,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    client_timestamp TIMESTAMPTZ NOT NULL,
    server_received_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    processed_status TEXT NOT NULL DEFAULT 'PROCESSED' CHECK (processed_status IN ('PENDING', 'PROCESSED', 'DUPLICATE_SKIPPED', 'FAILED')),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_offline_sync_action_id ON public.offline_sync_events(client_action_id);
CREATE INDEX IF NOT EXISTS idx_offline_sync_user ON public.offline_sync_events(user_id, server_received_at DESC);

-- Enable Row Level Security
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_delivery ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_read_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.offline_sync_events ENABLE ROW LEVEL SECURITY;

-- Row Level Security Policies
-- Notifications: Users can view notifications belonging to their profile or public farm broadcast
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'notifications' AND policyname = 'Users can view their notifications'
    ) THEN
        CREATE POLICY "Users can view their notifications"
            ON public.notifications
            FOR SELECT
            USING (auth.uid() = user_id OR user_id IS NULL);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'notifications' AND policyname = 'Service role can manage notifications'
    ) THEN
        CREATE POLICY "Service role can manage notifications"
            ON public.notifications
            FOR ALL
            USING (auth.role() = 'service_role');
    END IF;
END $$;

-- Notification Read State: Users can manage their read markers
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'notification_read_state' AND policyname = 'Users can view their read state'
    ) THEN
        CREATE POLICY "Users can view their read state"
            ON public.notification_read_state
            FOR ALL
            USING (auth.uid() = user_id);
    END IF;
END $$;

-- Offline Sync Events: Users can insert and view their sync events
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'offline_sync_events' AND policyname = 'Users can manage their offline sync events'
    ) THEN
        CREATE POLICY "Users can manage their offline sync events"
            ON public.offline_sync_events
            FOR ALL
            USING (auth.uid() = user_id OR user_id IS NULL);
    END IF;
END $$;
