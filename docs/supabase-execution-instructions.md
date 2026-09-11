# AgriSaathi AI — Supabase Migration Execution Instructions
**Date**: September 2026 | **Target**: Existing Supabase Project (`cmerfrcefbqhduzobyrz`)

---

## Prerequisites
- You must have administrative / owner access to your Supabase project dashboard:
  `https://supabase.com/dashboard/project/cmerfrcefbqhduzobyrz`
- Migration file to run:
  `supabase/migrations/20260911_agrisaathi_core.sql`

---

## Step-by-Step Dashboard Execution

1. **Log in to Supabase Dashboard**:
   Navigate to [https://supabase.com/dashboard](https://supabase.com/dashboard) and select your AgriSaathi project.

2. **Open the SQL Editor**:
   In the left-hand navigation sidebar, click on the **SQL Editor** icon (shaped like a terminal / `>_`).

3. **Create a New Query**:
   Click **+ New Query** at the top.

4. **Paste the Migration Script**:
   Copy the entire contents of [`supabase/migrations/20260911_agrisaathi_core.sql`](file:///c:/Users/Abhinay/OneDrive/Desktop/agrisaathi-sih/supabase/migrations/20260911_agrisaathi_core.sql) and paste it into the query window.

5. **Execute the Migration**:
   Click the green **Run** button (or press `Ctrl+Enter` / `Cmd+Enter`).

6. **Verify Successful Execution**:
   - The query results pane will display: `Success. No rows returned` (or row insertion confirmations for the model registry seeds).
   - In the left sidebar, click **Table Editor**. You should now see all 16 tables:
     - `profiles`, `farms`, `farm_zones`, `devices`, `device_zone_assignments`
     - `telemetry`, `device_status_events`, `actuator_states`, `pump_commands`
     - `alerts`, `ai_inference_records`, `model_registry`, `rag_documents`
     - `conversation_sessions`, `conversation_messages`, `offline_sync_queue`, `audit_events`
   - Click on **Authentication** -> **Policies** and verify that Row Level Security (RLS) is enabled on each farmer-owned table with strict `auth.uid()` checks.

---

## Validation Queries

Run the following sanity-check queries in the SQL Editor after migration:

```sql
-- 1. Check table existence
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- 2. Verify model registry seeds
SELECT model_name, model_version, model_status 
FROM public.model_registry;

-- 3. Verify RAG document seeds
SELECT doc_id, title, source 
FROM public.rag_documents;

-- 4. Verify RLS status on all tables
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';
```
