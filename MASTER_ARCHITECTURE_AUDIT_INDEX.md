# AgriSaathi Architecture Audit — Master Index

**Complete Analysis of Cross-File Synthetic Defaults & Coordinated Remediation Plan**

**Status:** ✅ Analysis Complete | 🟡 Awaiting User Decision | 🔴 Implementation Pending

---

## 📊 Audit Scope

**Timeline:** September 17, 2026  
**Method:** Static code analysis + cross-file contract tracing  
**Coverage:** 5 architectural tiers (sensor hardware → MQTT → DB → AI → frontend)  
**Files Analyzed:** 25+  
**Violations Found:** 7 major categories with 11 specific code locations

---

## 📚 Complete Document Set

### Layer 1: Initial Findings (First Analysis Session)

1. **ARCHITECTURE_AUDIT_FINDINGS.md** (20 min read)
   - 5-tier analysis structure
   - "Golden principle": real data or DATA_UNAVAILABLE, never synthetic
   - Target architecture diagram
   - Remediation roadmap (5 phases)

2. **AUDIT_EXECUTIVE_SUMMARY.md** (15 min read)
   - What's working vs broken
   - Risk metrics and business impact
   - Quick status table

3. **AUDIT_CODE_LOCATIONS.md** (reference)
   - Line-by-line code locations
   - Exact violations with code samples
   - Search commands to find issues

4. **REMEDIATION_PLAN.md** (technical)
   - Phase 1-5 detailed tasks
   - Code examples for each fix
   - Testing strategy

5. **QUICK_REFERENCE_CARD.md** (decision guide)
   - Problem in 30 seconds
   - 3 options for crop model strategy
   - Decision matrix

---

### Layer 2: Deep Cross-File Analysis (This Session)

6. **CROSS_FILE_CONTRACT_VIOLATIONS.md** ⭐ (START HERE for technical details)
   - 7 violation categories with exact lines
   - Violation 1A-F: Synthetic defaults at 6 layers
   - Violation 2: Vision AI trustworthiness
   - Violation 3: No freshness tracking
   - Violation 4: Device metadata fabrication
   - Violation 5: Competing telemetry paths
   - Violation 6: Feature contract mismatch
   - Violation 7: Confidence score validation
   - Summary table of all violations
   - Cross-file dependency groups

7. **CANONICAL_SCHEMAS.md** ⭐ (Schema designs)
   - Schema 1: CanonicalTelemetry (with freshness + data quality)
   - Schema 2: VisionDiagnosis (with sensor validation)
   - Schema 3: DeviceStatus (with lifecycle states)
   - Schema 4: AIPredictionResponse (unified AI format)
   - Example JSON responses for each schema
   - Exact Pydantic class definitions

8. **COORDINATED_REMEDIATION_ORDER.md** ⭐ (Implementation guide)
   - 6-phase implementation plan
   - Dependency chain diagram
   - Exact tasks with code examples
   - 15.5-hour timeline
   - Testing & rollout strategy
   - Pre-deployment checklist

---

## 🎯 Key Findings Summary

### Problem: Synthetic Defaults at Multiple Layers

| Layer | File | Issue | Severity |
|-------|------|-------|----------|
| Frontend | sensorService.ts:66-69 | Fallback to 40%, 28°C, 65%, 8000 lux | 🔴 |
| Backend Weather | main.py:675-678 | Uses `or` for weather defaults | 🔴 |
| Vision AI | main.py:1324-1339 | Synthetic 16%, 35°C, 1.2 for fusion | 🔴 |
| Risk Engine | risk_engine.py:305-306 | Uses `rain_prob or 0` | 🟠 |
| Model Providers | model_providers.py:228-230 | NPK defaults to 45, 22, 38 | 🟠 |
| Mobile | LocalOfflineAdvisor.ts:18 | Defaults to 28°C offline | 🟡 |

### Problem: Vision AI Not Trustworthy

Current pipeline:
```
IMAGE → validate → SVM → RETURN diagnosis
```

What actually happens:
```
IMAGE → validate → SVM → (call multimodal fusion with SYNTHETIC soil/temp/EC) → confident-looking result
```

Fix needed:
```
IMAGE → validate → SVM → CHECK: do required sensors exist AND are real?
  ├─ NO → RETURN image-only (or INSUFFICIENT_SENSORS)
  └─ YES → perform fusion
```

### Problem: No Freshness Tracking

Current state:
- Telemetry received 3 days ago
- Frontend calls /api/telemetry/latest
- System returns: `"data_source": "MQTT_VALIDATED"` (sounds fresh!)
- Reality: Device is offline, data is stale

Fix needed:
- Every response includes: `age_seconds`, `data_quality` status, `received_at`
- Data quality: LIVE (≤10 min), STALE (>10 min, ≤6 hrs), OFFLINE (>6 hrs)

### Problem: Device Metadata Fabricated

Current registration response:
```json
{
  "status": "ONLINE",
  "battery_pct": 94,
  "signal_rssi_dbm": -62,
  "firmware_version": "v2.4.1"
}
```

Problem:
- Status is "ONLINE" but device never sent telemetry
- Battery/signal/firmware are hardcoded values
- Caller can't tell what's real vs invented

Fix needed:
- Status should be "REGISTERED" (device created, awaiting first telemetry)
- Metadata fields should be `null` until real telemetry arrives
- All metadata sourced from actual device packets

### Problem: Competing Telemetry Paths

Current system has 5 ways to get sensor data:

1. ✅ MQTT → mqtt_service → DB → canonical_telemetry (good)
2. ❌ HTTP /sensors → sensorService.ts → [fallback defaults] (bad)
3. ⚠️ HTTP /sensors → Next.js proxy (redundant)
4. ⚠️ /api/sensor-data endpoint (unclear)
5. ⚠️ Simulator (testing only, but could leak)

Result: Inconsistent validation, different defaults, confusion about what's "true"

Fix: Single canonical path only
```
ESP32 → MQTT → mqtt_service → validation → canonical_telemetry → /api/telemetry/latest
```

---

## 🏗️ Architecture After Fixes

### Current (Broken)

```
ESP32 ──→ MQTT ───→ SQLite
    \\──→ HTTP /sensors ──→ Fallback defaults ──→ Frontend
```

### After Remediation (Fixed)

```
ESP32
   │
   MQTT/TLS (encrypted)
   │
   ▼
┌─────────────────────────┐
│ mqtt_service.py         │
│ - Parse JSON            │
│ - Validate ranges       │
│ - Preserve nulls        │
│ - Set server timestamp  │
│ - Anti-spoofing check   │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ Canonical Telemetry DB  │
│ - No defaults injected  │
│ - Deduplication by hash │
│ - Device lifecycle      │
└──────────┬──────────────┘
           │
    ┌──────┼──────┐
    ▼      ▼      ▼
  Risk   ML     Vision
 Engine  Model   AI
    │      │      │
    └──────┼──────┘
           ▼
┌─────────────────────────┐
│ FastAPI Canonical API   │
│ - Single source of truth│
│ - Freshness tracking    │
│ - Data quality status   │
└──────────┬──────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
  Web           Android
 Dashboard      App
```

---

## 📋 Implementation Roadmap

### Phase 0: Schemas & Config (2.5 hours)
- Create canonical schemas (CanonicalTelemetry, VisionDiagnosis, DeviceStatus, AIPredictionResponse)
- Add freshness thresholds to config.py

### Phase 1: MQTT Service (3 hours)
- Add explicit server-side timestamp tracking
- Update device lifecycle to auto-compute state from age

### Phase 2: Database Layer (2 hours)
- New method: get_latest_telemetry_canonical() with freshness metadata
- Helper: compute_data_quality() based on age

### Phase 3: Main.py API Endpoints (4 hours)
- Create /api/telemetry/latest endpoint
- Fix weather fallback defaults
- Fix vision multimodal fusion
- Update all AI endpoints to use unified schema

### Phase 4: Vision AI (2 hours)
- Add sensor availability check before multimodal fusion
- Return INSUFFICIENT_SENSORS when needed

### Phase 5: Frontend (2 hours)
- Remove HTTP direct ESP32 path
- Remove all fallback defaults
- Update components to show "data unavailable" explicitly

### Phase 6: Android (1 hour, parallel)
- Remove offline advisor hardcoded defaults

**Total: ~15.5 hours** (13.5 sequential + 2 parallel)

---

## ✅ Success Criteria

After implementation, the system should satisfy:

- [ ] **No synthetic defaults** — grep finds zero `?? NUMBER` or `or NUMBER` patterns
- [ ] **Explicit "unavailable"** — UI shows "Sensor offline" not "40% moisture"
- [ ] **Freshness tracking** — every response includes age_seconds and data_quality
- [ ] **Single canonical path** — ESP32 → MQTT → API → Frontend only
- [ ] **Device state accurate** — REGISTERED, ONLINE, STALE, OFFLINE computed from age
- [ ] **Device metadata real** — battery%, signal, firmware from telemetry, not hardcoded
- [ ] **Vision AI trustworthy** — no multimodal fusion without real sensors
- [ ] **AI confidence bounded** — includes calibration status and OOD checks
- [ ] **Feature contracts explicit** — required vs available features documented

---

## 🚀 User Decision Points

### Decision 1: Proceed with Implementation?

**Options:**
- [ ] Proceed immediately (start Phase 0 today)
- [ ] Review more first (which documents?)
- [ ] Pause (timeline constraints)

### Decision 2: Crop Model Strategy

From AUDIT_EXECUTIVE_SUMMARY.md:

- [ ] Option A: Train new 3-feature model (temp, humidity, rainfall) — Recommended
- [ ] Option B: Return insufficient-data error for NPK-less farms
- [ ] Option C: Hybrid both models

**Recommendation:** Option A (works immediately, field-validated later)

### Decision 3: Implementation Ownership

- [ ] Kiro implements all phases (autonomous)
- [ ] Kiro implements Phase 0-3, user handles 4-5
- [ ] User implements with Kiro guidance
- [ ] Other arrangement

---

## 📖 How to Use These Documents

### For Quick Understanding
1. Read QUICK_REFERENCE_CARD.md (5 min)
2. Skim AUDIT_EXECUTIVE_SUMMARY.md (10 min)
3. Look at COORDINATED_REMEDIATION_ORDER.md summary table (5 min)

### For Technical Review
1. Read CROSS_FILE_CONTRACT_VIOLATIONS.md (20 min) — find your code
2. Review CANONICAL_SCHEMAS.md (15 min) — understand response format
3. Study COORDINATED_REMEDIATION_ORDER.md Task sections (30 min) — see exact changes

### For Implementation
1. Print/bookmark COORDINATED_REMEDIATION_ORDER.md (your implementation guide)
2. Keep CANONICAL_SCHEMAS.md open (reference while coding)
3. Use CROSS_FILE_CONTRACT_VIOLATIONS.md to validate fixes

### For Project Management
1. Use COORDINATED_REMEDIATION_ORDER.md task list for sprints
2. Check pre-deployment checklist before release
3. Monitor metrics post-deployment

---

## 📞 Questions by Category

### "What's broken?"
→ Read: CROSS_FILE_CONTRACT_VIOLATIONS.md (Violations #1-7)

### "Why is it broken?"
→ Read: ARCHITECTURE_AUDIT_FINDINGS.md (Tiers 1-5)

### "How do I fix it?"
→ Read: COORDINATED_REMEDIATION_ORDER.md (Phases 0-6)

### "What should the response look like?"
→ Read: CANONICAL_SCHEMAS.md (example JSON responses)

### "Where exactly is the bug?"
→ Read: AUDIT_CODE_LOCATIONS.md (exact line numbers)

### "How long will this take?"
→ Read: COORDINATED_REMEDIATION_ORDER.md (15.5 hours)

### "What's the risk if I don't fix it?"
→ Read: AUDIT_EXECUTIVE_SUMMARY.md (Risk section)

---

## 🔗 Document Dependency Graph

```
AUDIT_FINDINGS ──→ EXECUTIVE_SUMMARY ──→ QUICK_REFERENCE_CARD
                                              ↓
                                         User Decision
                                              ↓
CROSS_FILE_CONTRACTS ──→ CANONICAL_SCHEMAS ──→ REMEDIATION_ORDER
                              ↑                       ↓
                              └───────────────────────┘
                                   (Implementation)
```

---

## 📊 Violation Summary Table

| Category | File | Line(s) | Severity | Status |
|----------|------|---------|----------|--------|
| Synthetic defaults (frontend) | sensorService.ts | 66-69 | 🔴 | Documented |
| Weather fallback defaults | main.py | 675-678 | 🔴 | Documented |
| Vision multimodal synthetic | main.py | 1324-1339 | 🔴 | Documented |
| Risk engine rainfall default | risk_engine.py | 305-306 | 🟠 | Documented |
| Model provider NPK defaults | model_providers.py | 228-230 | 🟠 | Documented |
| Mobile offline advisor default | LocalOfflineAdvisor.ts | 18 | 🟡 | Documented |
| Vision AI sensor trust | main.py | 1324-1339 | 🔴 | Documented |
| No freshness tracking | All telemetry endpoints | N/A | 🔴 | Documented |
| Device metadata fabricated | main.py device-register | N/A | 🟠 | Documented |
| Competing telemetry paths | Multiple | Multiple | 🟠 | Documented |
| Feature contract mismatch | Training vs Hardware | N/A | 🔴 | Documented |
| Confidence not calibrated | main.py crop endpoint | N/A | 🟡 | Documented |

---

## 🎓 Lessons Learned

### Cross-File Contracts Matter

When file A returns data to file B, and B passes it to C:
- If A doesn't validate: B gets bad data
- If B doesn't preserve nulls: C gets fabricated defaults
- If C doesn't check freshness: User sees stale data as current

**Fix:** Explicit schema at every boundary.

### "or" Operator is Dangerous for Sensor Data

```python
# WRONG:
value = data.get("moisture") or 40  # If 0%, becomes 40%

# RIGHT:
value = data.get("moisture")
if value is None:
    # handle missing
```

### Confidence Scores Are Not Confidence

- Model probability (what SVM outputs) ≠ real-world confidence
- Need calibration, OOD checks, field validation
- Display confidence bounds, not point estimates

### Synthetic Data Leaks Through the System

One place injects synthetic defaults → all downstream consumers treat it as real → AI makes predictions based on fiction.

**Fix:** Single validation boundary (MQTT service), all downstream processes preserve nulls.

---

## 🏁 Next Steps

1. **Read** this document
2. **Review** CROSS_FILE_CONTRACT_VIOLATIONS.md for your files of interest
3. **Decide** on crop model strategy (Option A/B/C)
4. **Confirm** with user: Proceed with implementation?
5. **Follow** COORDINATED_REMEDIATION_ORDER.md phases in order

---

**Prepared by:** Kiro  
**Date:** September 17, 2026  
**Status:** Analysis Complete | Implementation Ready | Awaiting User Decision  
**Confidence:** High (all findings backed by code inspection)  
**Risk Level:** 🔴 Critical if unfixed | Implementation reduces to 🟡 Medium

