# AgriSentinel Edge Architecture & File Segregation

This repository is segregated cleanly into **Hardware Sensor Firmware**, **Edge Gateway Daemons**, **Mobile Application UI**, and **FastAPI Intelligence Backend**.

---

## 📁 Clean File Segregation Structure

```
agrisaathi-main/
│
├── 🔌 edge_hardware/                        <-- HARDWARE & SENSOR NODE CODE
│   ├── esp32_sensor_node.ino               # C++ Firmware for ESP32 / Arduino Microcontroller
│   ├── qualcomm_edge_gateway.py            # Python Daemon for Qualcomm Edge DevKit / Serial Reader
│   └── README.md                           # Hardware Architecture Guide
│
├── 📱 src/                                  <-- MOBILE-FIRST WEB APP (Frontend)
│   ├── app/
│   │   ├── command-center/page.tsx         # /command-center Mobile View Route
│   │   └── advisor/page.tsx                # AI Advisor Chat Route
│   └── components/
│       └── FarmCommandCenter.tsx           # 100% Mobile Responsive Command Grid & Simulator
│
└── 🧠 mlbackend/                            <-- EDGE INTELLIGENCE BACKEND (Python)
    ├── main.py                             # FastAPI Engine & REST Endpoints
    ├── risk_engine.py                      # 4-Zone Multimodal Risk Engine
    ├── llm_service.py                      # 3-Tier Resilient Offline LLM Fallback Chain
    └── database.py                         # SQLite Offline Telemetry Store & Sync Manager
```

---

## 📱 Mobile Compatibility Features
* **Touch-Friendly Controls**: Touch sliders for IoT telemetry tuning, full-width tap targets, and touch scrollable tab bars.
* **Responsive Breakpoints**: Auto-adapting 1-column mobile layouts for Android/iOS smartphones up to 3-column desktop displays.
* **Offline PWA Capability**: Operates smoothly on mobile browsers even when network connectivity drops.
