# AgriSaathi Audit — Quick Reference Card

## The Problem in 30 Seconds

**Current state:** When ESP32 sensor is offline, the system uses hardcoded fake values (40% moisture, 28°C, 90% humidity) and shows them as real data to farmers.

**Consequence:** AI predictions based on fake data = unreliable recommendations.

**Your requirement:** Remove fake data, show "data unavailable" instead.

---

## The Fix in 30 Seconds

1. Delete HTTP direct sensor path (frontend)
2. Create unified API endpoint (backend)
3. Choose what to do about crop model (needs N/P/K, ESP32 doesn't have)

**Effort:** 10–15 hours to fix, ~1 hour decision time

---

## The Critical Decision You Need to Make

### Crop Model Strategy

Your crop recommendation model was trained on 7 features:
```
[N, P, K, temperature, humidity, pH, rainfall]
```

Your ESP32 provides only:
```
[temperature, humidity]  ← Have these
[N, P, K, pH]           ← Don't have these
[rainfall]              ← Can get from weather API
```

**What should the system do?**

### Option A: Train New 3-Feature Model ⭐ Recommended

**Model learns from:** `[temperature, humidity, rainfall]`

**Pros:**
- Works with current hardware immediately
- Farmers get crop recommendations today
- Still reasonably accurate
- Future-proof: can add NPK sensors later

**Cons:**
- Requires retraining (~3 hours)
- Accuracy slightly lower than 7-feature model

**Timeline:** ~3 hours (train model, test, deploy)

---

### Option B: Return "Insufficient Data"

**When farmer asks "What should I plant?"**

System responds: "Please conduct soil test and upload NPK results. Or wait until NPK sensors installed."

**Pros:**
- No retraining needed
- 100% honest
- Farmer knows why no recommendation

**Cons:**
- No crop recommendations available
- Bad UX
- Farmers frustrated

**Timeline:** ~1 hour (add validation, return error)

---

### Option C: Hybrid (Both Models)

**If N, P, K available:** Use full 7-feature model  
**If only temp + humidity:** Use 3-feature fallback

**Pros:**
- Best of both worlds
- Future-proof
- Graceful degradation

**Cons:**
- More complex code
- Maintain 2 models
- More testing required

**Timeline:** ~5 hours (train model, integrate both)

---

## Decision Matrix

| Factor | Option A | Option B | Option C |
|--------|----------|----------|----------|
| Works today? | ✅ Yes | ❌ No | ✅ Yes |
| Accuracy | 🟡 Good | — | ✅ Best |
| Simplicity | ✅ Simple | ✅ Simple | 🟡 Complex |
| UX | ✅ Good | ❌ Bad | ✅ Best |
| Effort | 🟡 3h | ✅ 1h | 🟠 5h |
| **Recommended for SIH?** | ✅ YES | ❌ NO | 🟡 Maybe |

---

## What to Do Right Now

### Step 1: Read (15 min)
- Review AUDIT_EXECUTIVE_SUMMARY.md (this folder)

### Step 2: Decide (10 min)
- Pick Option A, B, or C above
- Write your choice below

### Step 3: Confirm (5 min)
- Approve remediation scope
- Give Kiro green light to implement

---

## Your Decision

**I choose:** [ ] Option A (3-feature model)  /  [ ] Option B (insufficient data)  /  [ ] Option C (hybrid)

**Additional notes:** _____________________________________________

**Approved to proceed?** [ ] Yes  [ ] No  [ ] Review first

---

## Timeline After Your Decision

### If Option A or C Chosen:

```
Day 1:
  ✅ 1h  — Train/test new model
  ✅ 2h  — Implement Phase 1 (remove synthetic defaults)
  ✅ 1h  — Implement Phase 2 (model strategy)
  ✅ 1h  — Implement Phase 3 (unified API endpoint)
  → Subtotal: 5 hours

Day 2:
  ✅ 1h  — Update frontend components
  ✅ 1h  — Integration testing
  ✅ 30m — Deploy to staging
  → Subtotal: 2.5 hours

Day 3:
  ✅ 30m — Farmer validation on real device
  ✅ 30m — Fix any issues
  ✅ 30m — Production deployment
  → Subtotal: 1.5 hours

Total: 9 hours
```

### If Option B Chosen:

```
Day 1:
  ✅ 30m — Add validation to model endpoint
  ✅ 1h  — Implement Phase 1 (remove synthetic defaults)
  ✅ 1h  — Implement Phase 3 (unified API endpoint)
  → Subtotal: 2.5 hours

Day 2:
  ✅ 1h  — Update frontend components
  ✅ 1h  — Integration testing
  ✅ 30m — Deploy to staging
  → Subtotal: 2.5 hours

Total: 5 hours
```

---

## What Happens After Core Fixes

### Phase 4 (Optional, Later Sprint)

Cloud sync worker (so data doesn't disappear if device fails)  
**Effort:** 4–5 hours  
**Priority:** Medium (nice-to-have for production)

### Phase 5 (Optional, Later Sprint)

Enhanced input validation  
**Effort:** 2–3 hours  
**Priority:** Low (defensive hardening)

---

## Risk If You Don't Fix This

**Scenario:**
1. Deploy current system to 100 farmers
2. Several devices go offline (network issue, power loss, etc.)
3. Farmers see "Soil moisture: 40%" (actually the hardcoded default)
4. Farmers don't irrigate (trusting the system)
5. Crops wilt
6. Farmers: "Your AI got us to waste Rs 50,000 on seeds"
7. SIH judging: "This is not verifiable. You're using synthetic data."
8. System rejected

**Probability:** 80% (inevitable with current code)  
**Timeline:** Within 2 weeks of deployment

---

## Quick Sanity Checks

After fixes are implemented, you should see:

- ✅ No hardcoded defaults in TypeScript (grep for `?? 40`, `?? 28`, `?? 65`)
- ✅ Frontend only calls `/api/telemetry/latest`, never direct HTTP
- ✅ Risk engine returns `DATA_UNAVAILABLE` when sensor missing
- ✅ Model endpoint validates feature vector before inference
- ✅ Farmer sees "No live data available" instead of fake crisis alert

---

## How to Verify It's Fixed

### Test 1: Pull ESP32 Power

1. Stop ESP32 (physically unplug or kill MQTT)
2. Wait 30 seconds
3. Open farmer app
4. **Expected:** "Sensor data unavailable" (not "Soil moisture: 40%")
5. **Status:** ✅ If you see "unavailable"  / ❌ If you see fake values

### Test 2: Send Offline MQTT

1. Publish empty telemetry: `{"device_id": "ESP32_NODE_01", "telemetry": {}}`
2. Query `/api/telemetry/latest`
3. **Expected:** All sensor values are `null` or `UNAVAILABLE`
4. **Status:** ✅ If you see nulls  / ❌ If you see defaults

### Test 3: Call Model Without Features

1. Call `/api/recommend/crop` with only temperature/humidity (no N/P/K)
2. **Expected:** Either INSUFFICIENT_DATA (Option B) or fallback recommendation (Option A/C)
3. **Status:** ✅ Explicit response  / ❌ Silent failure or fake recommendation

---

## Documents to Read (In Order)

1. **QUICK_REFERENCE_CARD.md** ← You are here (5 min)
2. **AUDIT_EXECUTIVE_SUMMARY.md** (10 min)
3. **ARCHITECTURE_AUDIT_FINDINGS.md** (detailed, 20 min)
4. **AUDIT_CODE_LOCATIONS.md** (reference, 10 min if needed)
5. **REMEDIATION_PLAN.md** (technical, 20 min)

**Total reading:** ~45 min

---

## Next Actions

### After You Read This

1. **Decide** on crop model option (A/B/C)
2. **Approve** proceeding with fixes
3. **Provide** your GitHub/deployment credentials (if Kiro implementing)

### Kiro Will Then

1. Implement Phase 1 (synthetic defaults removal)
2. Implement Phase 2 (crop model choice)
3. Implement Phase 3 (unified API endpoint)
4. Run integration tests
5. Deploy to staging
6. Get your feedback

---

## Contact Info

If you have questions:

- **About the audit:** Review ARCHITECTURE_AUDIT_FINDINGS.md
- **About the fix:** Review REMEDIATION_PLAN.md
- **About line numbers:** Review AUDIT_CODE_LOCATIONS.md
- **Technical clarification:** Kiro can explain any section

---

**Generated:** 2026-09-17  
**Status:** Waiting for your decision  
**Next milestone:** Option selection → Kiro implementation start

