# AgriSaathi AI — Supabase Database Migration Guide
**Document Version**: 2.0.0 | **Authoritative Specification**: SIH26180 AgriSaathi AI  
**Current Status**: `READY — AWAITING MANUAL SQL EXECUTION`

---

## 1. Migration File Specification

- **Exact SQL File Path**: `supabase/migrations/20260911_agrisaathi_core.sql`
- **File Size**: 26,961 Bytes
- **Target Database**: PostgreSQL 15+ (Existing Supabase Cloud Project)
- **Target Schema**: `public` with extensions `uuid-ossp`, `pgcrypto`
- **Current Execution State**: **`READY — AWAITING MANUAL SQL EXECUTION`**  
  *(Migration has NOT yet been run against the remote Supabase project. It must not be reported as completed until executed by the project owner in the Supabase Dashboard SQL Editor.)*

---

## 2. Pre-Migration Safety & Backup Recommendation

> [!CAUTION]
> **Zero Data Destruction Constraint**:
> 1. Do NOT delete or drop existing tables (`users`, `devices`, `sensor_telemetry`, etc.).
> 2. Do NOT drop or delete existing auth users in `auth.users`.
> 3. Do NOT create a new Supabase project — execute directly within the existing project.

### Recommended Pre-Migration Actions:
1. **Dashboard Backup**: Navigate to **Supabase Dashboard** -> **Project Settings** -> **Database** -> **Backups** -> **Schedule Manual Backup / Download Daily Snapshot**.
2. **CLI Dump (Alternative)**:
   ```bash
   pg_dump "postgresql://postgres:[YOUR-DB-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres" \
     --schema=public --clean --if-exists > supabase_backup_pre_20260911.sql
   ```

---

## 3. Step-by-Step Execution via Supabase Dashboard SQL Editor

1. Open the [Supabase Dashboard](https://app.supabase.com).
2. Select your existing AgriSaathi project.
3. In the left navigation menu, click **SQL Editor**.
4. Click **New Query** (or **+**).
5. Open the local migration file:
   `supabase/migrations/20260911_agrisaathi_core.sql`
6. Copy the entire contents of `20260911_agrisaathi_core.sql` into the SQL Editor.
7. Click the green **RUN** button (or press `Ctrl+Enter`).
8. Verify that the query output indicates:
   `Success. No rows returned` (or list of created tables and triggers).

---

## 4. Alternative: Supabase CLI Execution

If you have configured the Supabase CLI locally:

```bash
# 1. Link project
npx supabase link --project-ref <your-project-ref>

# 2. Push migration
npx supabase db push
```

---

## 5. Existing Schema Conflict Resolution

`20260911_agrisaathi_core.sql` is engineered with idempotent, non-destructive DDL:
- Uses `CREATE TABLE IF NOT EXISTS` for all canonical entities (`farms`, `zones`, `devices`, `telemetry`, `actuator_commands`, `ai_inferences`, `agricultural_alerts`, `rag_knowledge_base`, `offline_sync_queue`, `audit_events`).
- Uses `ADD COLUMN IF NOT EXISTS` for backward-compatible optional fields (`vibration_raw`, `vibration_rms`, `soil_n`, `soil_p`, `soil_k`).
- Recreates triggers using `DROP TRIGGER IF EXISTS ... BEFORE CREATE TRIGGER`.
- Uses `CREATE POLICY IF NOT EXISTS` or drops prior policies cleanly to prevent duplicate policy errors.

---

## 6. Post-Migration Verification SQL

After running the migration in the SQL Editor, execute the following verification query in a new SQL tab:

```sql
-- 1. Verify all 16 canonical tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN (
    'farmers', 'farms', 'zones', 'devices', 'device_status_logs',
    'telemetry', 'actuator_commands', 'ai_inferences', 'agricultural_alerts',
    'rag_knowledge_base', 'offline_sync_queue', 'audit_events'
  )
ORDER BY table_name;

-- 2. Verify Row-Level Security (RLS) is ENABLED on every table
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- 3. Verify Active Policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- 4. Verify Actuator Command Lifecycle Constraints
SELECT conname, pg_get_constraintdef(c.oid)
FROM pg_constraint c
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE n.nspname = 'public' AND c.conname LIKE '%pump%' OR c.conname LIKE '%status%';

-- 5. Verify Service-Role Ingestion Access
-- Ingesting devices using the service_role key bypasses farmer-level restrictions for IoT telemetry:
SELECT has_table_privilege('service_role', 'public.telemetry', 'INSERT');
```

### Expected Output Summary:
- **16 Tables**: All returned.
- **rowsecurity**: `true` for all tables.
- **Policies**: Farm ownership policies (`user_id = auth.uid()`) active on all tables.
- **Service-Role Privilege**: `true` for `INSERT` on `public.telemetry` and `public.actuator_commands`.

---

## 7. Safe Rollback Instructions

If unexpected conflicts arise during or after execution, execute the isolated rollback script:
`docs/supabase-rollback-plan.md`

Key rollback rules:
1. Do NOT drop user tables.
2. Only drop newly created foreign-key triggers or indices if they cause performance regressions.
3. Disable newly added policies with:
   ```sql
   ALTER TABLE public.actuator_commands DISABLE ROW LEVEL SECURITY;
   ```
   *(Or restore previous policy definitions).*
