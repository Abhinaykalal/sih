# AgriSaathi AI — Hardware Integration Guide
## ESP32 Sensor Node Setup for SIH26180

---

## 1. Hardware Requirements

| Component | Model | Purpose |
|-----------|-------|---------|
| Microcontroller | ESP32-WROOM-32D | Main field controller |
| Soil Moisture | Capacitive V1.2 (resistor-less) | Root zone moisture (0–100%) |
| Soil Temperature | DS18B20 waterproof | Soil temp at 10cm depth |
| Air Temp/Humidity | DHT22 (or SHT31) | Above-canopy climate |
| Soil pH | DFRobot SEN0169 | pH 0–14 range |
| Soil EC | DFRobot SEN0244 | Salinity / conductivity |
| NPK Sensor | JXBS-3001-TR | N, P, K via RS485 Modbus |
| Power | 18650 Li-ion × 2 + TP4056 | 4200mAh field battery |
| Solar | 6V 1W mini panel | Solar trickle charging |
| Connectivity | ESP32 built-in Wi-Fi | 2.4GHz to farm router |
| Status LED | WS2812B RGB | Health indicator |

---

## 2. ESP32 Pin Mapping

```
GPIO 32  → Soil Moisture (ADC1_CH4, analog)
GPIO 33  → DS18B20 (OneWire data)
GPIO 26  → DHT22 data
GPIO 34  → pH sensor (ADC1_CH6, analog)
GPIO 35  → EC sensor (ADC1_CH7, analog)
GPIO 16  → RS485 TX (NPK Modbus)
GPIO 17  → RS485 RX (NPK Modbus)
GPIO 4   → DE/RE RS485 control
GPIO 5   → WS2812B LED data
VIN      → 5V USB / solar
GND      → Common ground
```

---

## 3. Firmware Architecture

```
ESP32 Firmware (PlatformIO / Arduino)
├── sensors/
│   ├── soil_moisture.h    ← ADC reads with 16x oversampling
│   ├── ds18b20.h          ← OneWire temperature
│   ├── dht22.h            ← Air temp/humidity
│   ├── ph_sensor.h        ← ADC + calibration (pH4/7 buffers)
│   ├── ec_sensor.h        ← ADC + temperature compensation
│   └── npk_modbus.h       ← RS485 Modbus RTU read
├── comms/
│   ├── wifi_manager.h     ← WPA2 Wi-Fi with reconnect
│   ├── mqtt_client.h      ← Mosquitto pub/sub
│   └── ota_update.h       ← OTA firmware updates
├── power/
│   └── deep_sleep.h       ← 10min sleep cycles to save battery
└── main.cpp               ← Main loop
```

---

## 4. MQTT Protocol

### Telemetry Publish Topic
```
agrisaathi/{farm_id}/{field_id}/telemetry
```

### Payload Schema (JSON)
```json
{
  "schemaVersion": 1,
  "deviceId": "ESP32-FIELD-001",
  "farmId": "farm-punjab-001",
  "fieldId": "field-rice-n1",
  "crop": "Rice",
  "growthStage": "Vegetative",
  "timestamp": "2026-01-01T06:00:00Z",
  "data_source": "LIVE",
  "readings": {
    "soil_moisture_pct": 52.4,
    "soil_temperature_c": 23.6,
    "soil_ph": 6.8,
    "soil_ec_ds_m": 1.12,
    "air_temperature_c": 29.2,
    "air_humidity_pct": 67.0,
    "rain_detected": false,
    "NPK_ppm": { "N": 44.2, "P": 21.6, "K": 37.8 }
  },
  "device": {
    "battery_v": 4.02,
    "rssi_dbm": -58,
    "firmware": "0.1.4",
    "uptime_s": 86400
  },
  "sensor_health": {
    "status": "HEALTHY",
    "issues": [],
    "battery_level_pct": 80
  }
}
```

---

## 5. Backend MQTT Subscription

The `mqtt_service.py` subscribes to:
```
agrisaathi/+/+/telemetry
```
and routes messages to the telemetry store. The `AgentOrchestrator` reads the latest value from the store when a farmer query arrives.

**If MQTT broker is unreachable**, the orchestrator automatically falls back to the `ESP32TelemetrySimulator` (`esp32_simulator.py`) which generates physics-based time-series readings marked `data_source: SIMULATED`.

---

## 6. Calibration Procedures

### pH Sensor Calibration
1. Prepare pH 4.0 and pH 7.0 buffer solutions.
2. Rinse sensor with distilled water.
3. Submerge in pH 7.0 → record raw ADC value (`V7`).
4. Submerge in pH 4.0 → record raw ADC value (`V4`).
5. Calibration constants:
   - `slope = (7.0 - 4.0) / (V7 - V4)`
   - `offset = 7.0 - slope * V7`
6. Store in EEPROM / NVS flash.

### Soil Moisture Calibration
1. Record ADC reading in dry air → `DRY_ADC`.
2. Submerge sensor in water → `WET_ADC`.
3. `moisture% = (WET_ADC - raw) / (WET_ADC - DRY_ADC) * 100`

---

## 7. Power Budget & Battery Life

| Mode | Current Draw | Duration |
|------|-------------|---------|
| Active sensing | ~180 mA | 10 sec/cycle |
| Wi-Fi transmit | ~250 mA peak | 2 sec |
| Deep sleep | ~10 μA | ~10 min |
| **Average** | **~12 mA** | — |

**4200 mAh battery → ~14 days field life**
With 6V 1W solar charging: **indefinite in sunny weather**

---

## 8. LED Status Indicators

| Color | Pattern | Meaning |
|-------|---------|---------|
| 🟢 Green solid | — | All sensors healthy, connected |
| 🟡 Yellow blink | Slow | Wi-Fi connecting |
| 🔴 Red blink | Fast | Sensor error / hardware fault |
| 🔵 Blue blink | 1/sec | Publishing MQTT telemetry |
| ⚪ White pulse | — | OTA firmware update in progress |
| 🔴 Red solid | — | Critical: battery < 3.5V |

---

## 9. OTA Firmware Update

Updates are delivered via HTTP OTA from the backend:
```
GET http://<backend_ip>:8000/api/firmware/latest
```

Trigger remotely via MQTT command:
```
Topic: agrisaathi/{farm_id}/{field_id}/cmd
Payload: {"cmd": "ota_update", "url": "http://..."}
```

---

## 10. Sensor Health Monitoring Rules

The firmware and backend both perform health checks:

| Condition | Action |
|-----------|--------|
| Moisture > 100% or < 0% | Flag IMPOSSIBLE_MOISTURE |
| Temperature > 60°C or < -10°C | Flag TEMPERATURE_OUT_OF_RANGE |
| Battery voltage < 3.5V | Flag LOW_BATTERY, send alert |
| RSSI < -85 dBm | Flag POOR_SIGNAL |
| No publish in > 30 min | Backend flags sensor OFFLINE |

The AgriSaathi AI will display **"Sensor offline"** to the farmer if no valid reading arrives within 30 minutes. It will **never** fabricate readings.

---

## 11. Future: Qualcomm Edge Gateway Integration

For production deployment at scale:
- **Qualcomm QCS610 (Robotics RB5)** gateway collects MQTT from multiple ESP32 nodes via local broker
- Runs **ONNX / TFLite** edge inference (crop disease model quantized to INT8)
- Sends inference results + aggregated telemetry to cloud backend
- Reduces cloud bandwidth by ~80% compared to raw sensor uploads

See `docs/ai-architecture.md` for edge inference model specifications.
