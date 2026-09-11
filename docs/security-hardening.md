# AgriSaathi AI — Security Hardening & Zero-Trust Guidelines
**Version**: 1.0.0 | **Compliance Standard**: OWASP API Security Top 10

---

## 1. Authentication & JWT Validation

- **Current State**: Frontend uses Supabase Auth. Backend validates incoming Supabase JWT tokens via `mlbackend/auth.py`.
- **Validation Rules**:
  - `sub` claim maps to authenticated user profile ID.
  - Token signature is verified against `SUPABASE_JWT_SECRET`.
  - Expiration timestamp (`exp`) is strictly enforced; expired tokens return HTTP 401 with `WWW-Authenticate: Bearer`.
- **Production Setting**: Set `ENFORCE_JWT_AUTH=true` in production deployment environments.

---

## 2. Row Level Security (RLS) Ownership Chain

All database tables in Supabase PostgreSQL enforce strict ownership chains rooted at `auth.uid()`:

```
auth.users (id)
    └── profiles (id)
         └── farms (profile_id)
              └── farm_zones (farm_id)
                   └── devices (profile_id)
                        ├── telemetry (device_id)
                        └── pump_commands (requested_by)
```

No cross-tenant data leakage is permitted. Queries automatically filter by `auth.uid() = profile_id`.

---

## 3. MQTT Hardware Security

- **Development Prototype**: Anonymous MQTT over port 1883.
- **Production Hardening Checklist**:
  1. Transition to TLS port 8883 (`MQTT_USE_TLS=true`).
  2. Configure mutual TLS (mTLS) with client certificate authentication (`MQTT_CLIENT_CERT`, `MQTT_CLIENT_KEY`, `MQTT_CA_CERT`).
  3. Enforce Access Control Lists (ACLs) on broker topics:
     - `ESP32_NODE_01` can ONLY publish to `agrisaathi/nodes/ESP32_NODE_01/telemetry`.
     - `ESP32_NODE_01` can ONLY subscribe to `agrisaathi/nodes/ESP32_NODE_01/commands`.
     - Backend service role holds exclusive subscription/publishing rights.
  4. Never expose MQTT credentials or broker ports to Android or web clients.

---

## 4. CORS & API Exposure

- In production, CORS is restricted to trusted origins (`https://agrisaathi.vercel.app`, local development hosts).
- Wildcard `allow_origins=["*"]` is disabled when `ENFORCE_JWT_AUTH=true`.
- Sensitive hardware command endpoints (`POST /api/pump/command`) require valid user sessions and evaluate Rain Lockout safety gates before execution.

---

## 5. Secret Management & Git Hygiene

- `.env.local` and `.env` are strictly excluded in `.gitignore`.
- `.env.example` provides the canonical template without sensitive values.
- Automated pre-commit secret scanning (e.g. `gitleaks`) should be enabled before pushing commits.
