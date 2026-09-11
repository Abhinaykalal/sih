# AgriSaathi AI — Supabase Migration Rollback Plan
**Migration Reference**: `20260911_agrisaathi_core.sql` | **Safety Classification**: Non-Destructive

---

## 1. Rollback Philosophy & Safety Guardrails

- The migration `20260911_agrisaathi_core.sql` was intentionally authored with non-destructive clauses (`CREATE TABLE IF NOT EXISTS`, conditional DO blocks).
- Under NO circumstances should `DROP DATABASE` or bulk deletion of pre-existing user accounts be performed.
- If a rollback is required, only the newly created tables and auxiliary RLS policies are reverted, preserving the base `profiles` and `auth.users` tables.

---

## 2. Safe Rollback Script

If you need to roll back the schema additions, execute the following script in the Supabase SQL Editor:

```sql
-- Disable RLS and drop newly created tables in reverse dependency order
DROP TABLE IF EXISTS public.audit_events CASCADE;
DROP TABLE IF EXISTS public.offline_sync_queue CASCADE;
DROP TABLE IF EXISTS public.conversation_messages CASCADE;
DROP TABLE IF EXISTS public.conversation_sessions CASCADE;
DROP TABLE IF EXISTS public.rag_documents CASCADE;
DROP TABLE IF EXISTS public.model_registry CASCADE;
DROP TABLE IF EXISTS public.ai_inference_records CASCADE;
DROP TABLE IF EXISTS public.alerts CASCADE;
DROP TABLE IF EXISTS public.pump_commands CASCADE;
DROP TABLE IF EXISTS public.actuator_states CASCADE;
DROP TABLE IF EXISTS public.device_status_events CASCADE;
DROP TABLE IF EXISTS public.telemetry CASCADE;
DROP TABLE IF EXISTS public.device_zone_assignments CASCADE;
DROP TABLE IF EXISTS public.devices CASCADE;
DROP TABLE IF EXISTS public.farm_zones CASCADE;
DROP TABLE IF EXISTS public.farms CASCADE;

-- NOTE: DO NOT DROP public.profiles AS IT HOUSES AUTHENTICATED USER ACCOUNTS!
-- Simply revert optional columns added during migration:
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'role') THEN
        ALTER TABLE public.profiles DROP COLUMN role;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'preferred_language') THEN
        ALTER TABLE public.profiles DROP COLUMN preferred_language;
    END IF;
END $$;
```

---

## 3. Post-Rollback Verification

Confirm the public schema has returned to its initial state:
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```
Only `profiles` (and any other pre-existing custom tables) should remain.
