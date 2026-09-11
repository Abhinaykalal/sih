# AgriSaathi AI — Hardware Team Communication & Interface Requests
**Document Version**: 1.0.0 | **Target Node**: `ESP32_NODE_01` | **Status**: Active Specifications

---

## Overview

This document outlines the formal technical requests and interface contracts communicated from the Software/AI/Cloud engineering team to the ESP32 firmware and hardware team.

In strict compliance with project governance:
- Software does NOT modify ESP32 firmware, GPIO pin mappings, relay circuitry, or sensor calibration code.
- Software is fully backward-compatible with existing hardware telemetry and treats newly planned sensors as optional, nullable fields.
- Zero and `NULL` are treated as distinct values across the entire software stack.

---

## Hardware Interface Requests

### Request HW-01: Vibration Sensor Integration & Payload Contract
- **Reason**: The software requires mechanical anomaly detection on the irrigation pump motor (detecting bearing wear, impeller cavitation, dry-run imbalance) and optional physical node tampering detection.
- **Existing Software Expectation**: Optional, backward-compatible fields in the telemetry payload. If the sensor is not present, uncalibrated, or reading fails, fields must be omitted or transmitted as `null`.
- **Required Hardware Information**:
  1. Sensor model (e.g. SW-420 digital vibration switch vs. ADXL345 / MPU6050 3-axis analog/I2C accelerometer).
  2. Pin connection on ESP32 (GPIO pin number).
  3. Sampling rate and calculation window (e.g. 100 Hz sampling for 500 ms root-mean-square).
  4. Baseline resting value vs. normal motor operation threshold vs. anomaly threshold.
- **Whether It Blocks Implementation**: **NO**. The backend telemetry schema accepts optional `vibration_detected` (boolean) and `vibration_rms` (float). If absent, they default to `NULL` in PostgreSQL and `None` in Python without rejecting the packet.
- **Exact Expected Payload Field**:
  ```json
  "telemetry": {
    "vibration_detected": false,
    "vibration_rms": 0.04
  }
  ```
- **Expected Unit**: RMS acceleration in $g$ ($9.81\text{ m/s}^2$) or dimensionless relative RMS amplitude.
- **Expected Data Type**:
  - `vibration_detected`: `boolean` (`true` / `false`)
  - `vibration_rms`: `float` ($\ge 0.0$)
- **Expected Missing-Value Behavior**: JSON `null` (never transmit `0` or `false` when the sensor is absent or disconnected).

---

### Request HW-02: Soil NPK Sensor Integration & Calibration
- **Reason**: The software provides agronomic fertilizer optimization and nutrient deficiency detection. Distinguishing between chemical fertilizer requirements and irrigation needs requires verified soil Nitrogen, Phosphorus, and Potassium readings.
- **Existing Software Expectation**: Optional, backward-compatible fields. When absent, the software clearly labels NPK data as `Not Available` and directs the farmer to conduct an ICAR laboratory soil test rather than inventing dosage recommendations.
- **Required Hardware Information**:
  1. Sensor model (e.g. RS485 Modbus NPK optical/chemical soil sensor via MAX485 transceiver vs. analog approximation).
  2. UART pins (TX/RX GPIOs) and baud rate (standard 9600 bps, 8N1).
  3. Calibration status against standard soil chemical extractants (Bray/Olsen for P, Ammonium Acetate for K, Alkaline Permanganate for N).
  4. Operating voltage and power draw (RS485 sensors typically require 9V–24V DC step-up).
- **Whether It Blocks Implementation**: **NO**. The backend telemetry schema accepts optional `nitrogen`, `phosphorus`, and `potassium` fields. If absent, they default to `NULL`.
- **Exact Expected Payload Field**:
  ```json
  "telemetry": {
    "nitrogen": 45.0,
    "phosphorus": 22.0,
    "potassium": 38.0
  }
  ```
- **Expected Unit**: $\text{mg/kg}$ (ppm in dry soil).
- **Expected Data Type**: `float` ($\ge 0.0$).
- **Expected Missing-Value Behavior**: JSON `null` (never transmit `0` for missing NPK, as zero indicates extreme biological sterility).

---

### Request HW-03: MQTT Retained Status & Last Will and Testament (LWT)
- **Reason**: The software must accurately track device lifecycle (`online`, `offline`, `unknown`) and trigger offline alerts when field nodes lose connectivity or power.
- **Existing Software Expectation**:
  - Broker Topic: `agrisaathi/nodes/ESP32_NODE_01/status`
  - LWT Payload: `"offline"` (QoS 1, Retained = `true`)
  - Boot Payload: `"online"` (QoS 1, Retained = `true`)
- **Required Hardware Information**: Confirmation of MQTT client keep-alive interval (recommended: 30 seconds) and LWT configuration in ESP32 firmware.
- **Whether It Blocks Implementation**: **NO**. The backend subscribes to the status topic and also implements a heartbeat timeout watchdog (flags node `offline` if no telemetry is received within 120 seconds).
- **Exact Expected Payload**: Plain string `"online"` or `"offline"`.
- **Expected Missing-Value Behavior**: Retained state on broker.

---

### Request HW-04: Actuator Command Acknowledgement & Execution Feedback
- **Reason**: The software needs verifiable feedback when a pump command (`PUMP_ON`, `PUMP_OFF`, `MISTER_ON`, `MISTER_OFF`) is received and executed by the relay hardware.
- **Existing Software Expectation**:
  - Downlink Command Topic: `agrisaathi/nodes/ESP32_NODE_01/commands`
  - Command Payload dispatched by Backend:
    ```json
    {
      "command_id": "cmd_a1b2c3d4",
      "command": "PUMP_ON",
      "duration_sec": 300,
      "timestamp": 1726014605
    }
    ```
  - Uplink Acknowledgement on `agrisaathi/nodes/ESP32_NODE_01/telemetry`:
    In the next telemetry frame, the `actuator` block should reflect the physical relay status:
    ```json
    "actuator": {
      "pump_active": true,
      "last_executed_command_id": "cmd_a1b2c3d4"
    }
    ```
- **Required Hardware Information**: Confirmation whether the firmware will echo `last_executed_command_id` or publish to a dedicated command response topic.
- **Whether It Blocks Implementation**: **NO**. The backend tracks command states through `requested` -> `published` -> `acknowledged` -> `executed` based on the `pump_active` field in subsequent telemetry packets.

---

## Summary of Software Ingestion Rules for Hardware Team

| Sensor / Telemetry Metric | Hardware Range | Software Ingestion Field | Required or Optional | Missing-Value Representation |
| :--- | :--- | :--- | :--- | :--- |
| **Soil Moisture Percentage** | 0.0 – 100.0% | `soil_moisture_pct` | Required | `null` |
| **Soil Raw ADC Value** | 0 – 4095 (12-bit) | `soil_raw_adc` | Required | `null` |
| **Ambient Air Temperature** | -10.0 – 60.0°C | `temperature_c` | Required | `null` |
| **Relative Air Humidity** | 0.0 – 100.0% | `humidity_pct` | Required | `null` |
| **Sunlight Detection** | `true` / `false` | `sunlight_detected` | Required | `null` |
| **Pump Relay State** | `true` / `false` | `pump_active` | Required | `null` |
| **Vibration Detection** | `true` / `false` | `vibration_detected` | Optional | `null` |
| **Vibration RMS** | $\ge 0.0$ | `vibration_rms` | Optional | `null` |
| **Soil Nitrogen (N)** | $\ge 0.0\text{ mg/kg}$ | `nitrogen` | Optional | `null` |
| **Soil Phosphorus (P)** | $\ge 0.0\text{ mg/kg}$ | `phosphorus` | Optional | `null` |
| **Soil Potassium (K)** | $\ge 0.0\text{ mg/kg}$ | `potassium` | Optional | `null` |
| **Edge AI Diagnosis** | String label | `edge_ai_result` | Optional | `null` |
| **Edge AI Confidence** | 0 – 100% | `edge_ai_confidence_pct` | Optional | `null` |
