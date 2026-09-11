# AgriSaathi AI — 3-Minute Jury Demonstration Script (SIH26180)

**Target Audience**: Smart India Hackathon Jury & Agricultural Experts  
**Duration**: Exactly 3 Minutes (180 Seconds)  
**Devices**: Android Mobile App (Physical or Emulator) + FastAPI Edge Server

---

## Beat 1: Grounded Field Telemetry & Rain Lockout (0:00 – 0:45)

**Presenter Action**:
- Hold up the Android App displaying the **Home Dashboard** (`SensorScreen`).
- Point to the top greeting: *"Hello, Ramesh! Green Valley Farm, Ludhiana"*.
- Point to the live **Rain Lockout Banner**: *"Rain Lockout: ACTIVE (85% Rain Forecast, 12mm)"*.

**Spoken Script**:
> *"Good morning, respected jury members. We present AgriSaathi AI, a grounded, offline-first precision farming system.
> 
> Notice our clean, farmer-first dashboard. Unlike generic dashboards that display fabricated data, every number here is strictly grounded. Our ESP32 field node reports live soil moisture at 45.2% and temperature at 26.8°C.
> 
> Crucially, our weather engine detected an impending 12mm rainfall with 85% probability. Immediately, AgriSaathi engaged an autonomous **Rain Lockout Interlock**, holding the irrigation pump to save groundwater and prevent crop root damage."*

---

## Beat 2: Actuator Pump Control with Safety Interlock (0:45 – 1:30)

**Presenter Action**:
- Navigate to the **Pump Control Screen** (`PumpControlScreen`).
- Tap **"Turn Pump ON"**.
- Show the immediate pop-up alert: *"🛡️ Pump Activation Blocked: Rain Lockout Active"*.
- Toggle **"Manual Emergency Override"** and dispatch again to show the 4-stage lifecycle stepper: `Requested -> Published -> Acknowledged -> Executed`.

**Spoken Script**:
> *"Now let's test our actuator safety system. I am attempting to turn the irrigation pump ON.
> 
> As you can see, the backend **blocks the command immediately**. It logs a canonical `PUMP_COMMAND_BLOCKED` audit event.
> 
> But what if a farmer needs to flush fertilizer? We provide a safety-monitored **Manual Emergency Override**. When toggled, the command passes through our complete 4-stage lifecycle: Requested by backend, Published over MQTT, Acknowledged by edge hardware, and Executed by physical relay confirmation. Full accountability, zero runaway pumps."*

---

## Beat 3: Multi-Variable Crop & Leaf Disease AI (1:30 – 2:15)

**Presenter Action**:
- Navigate to the **Crop Advisory Screen** (`CropRecommendationScreen`).
- Tap **"Sync"** to pre-fill soil NPK from the live sensor telemetry. Tap **"Predict Optimal Crops"**.
- Highlight the **"REAL MODEL (RANDOM FOREST)"** badge and 99.1% test accuracy.
- Switch to **Leaf Vision Screen** (`VisionScreen`), point to the **"EXPERIMENTAL AI"** badge, and show the disease diagnostic result.

**Spoken Script**:
> *"Next is our agricultural intelligence engine. Our Crop Recommendation is powered by a real Random Forest model trained on verified ICAR multi-region datasets across 22 crops, achieving verified 99.1% test accuracy. It reads the ESP32 soil NPK directly and recommends Rice PR-126 with an Alternate Wetting and Drying schedule.
> 
> For leaf diseases, we believe in scientific honesty. Our computer vision module is marked transparently as **EXPERIMENTAL AI** while training on 115,000 augmented leaf images completes. It detects Bacterial Leaf Blight and provides both biological and chemical remedies."*

---

## Beat 4: Offline Resilience & Zero Third-Party Dependencies (2:15 – 3:00)

**Presenter Action**:
- Navigate to **Notifications** (`AlertsScreen`) and **Settings** (`SettingsScreen`).
- Point to the **"Offline Mode Active"** banner and the **"0 Pending"** sync badge.
- Tap **"Synchronize Offline Queue"** to demonstrate instant batch synchronization.

**Spoken Script**:
> *"Finally, rural India faces real network dead-zones. AgriSaathi AI is completely **offline-first**.
> 
> We have eliminated all third-party SMS and Twilio dependencies in favor of our own canonical, provider-independent notification architecture. When the farmer loses cellular coverage, all actions and notifications queue in local SQLite with idempotent client action IDs. The moment signal returns, our backend syncs them with zero duplicate writes.
> 
> AgriSaathi AI combines mathematical rigor, hardware fail-safes, and honest artificial intelligence to empower every Indian farmer. Thank you!"*
