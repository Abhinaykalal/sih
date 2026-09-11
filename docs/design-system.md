# AgriSaathi AI — Mobile Design System & UI Specification

## 1. Visual System Overview
The AgriSaathi AI mobile application is built to deliver a premium agricultural SaaS experience tailored to farmers and agronomists. It uses an organic, friendly, yet high-precision aesthetic defined in the design reference.

| Design Token | Hex / Value | Purpose |
|---|---|---|
| **Background Light** | `#F5FBF1` | Soft organic green backdrop across all screens |
| **Card Surface** | `#FFFFFF` | Rounded container cards with minimal soft elevation |
| **Primary Text** | `#123D25` | Deep forest green for high contrast readability |
| **Secondary Text** | `#4A6B56` | Muted olive-green for labels and subtitles |
| **Primary Accent** | `#2E8B36` | Fresh vibrant green for positive states & primary CTAs |
| **Sunlight Yellow** | `#F4C542` | Warm amber-yellow for weather & cautionary badges |
| **AI Feature Accent** | `#7667E8` | Subtle violet accent reserved for AI features & badges |
| **Border Radius** | `16px - 20px` | Smooth rounded corners on cards and action buttons |
| **Shadow** | `elevation: 2` | Clean, non-distracting soft elevation |

---

## 2. Screen Specifications (8 Core Screens)

### Screen 1: Dashboard (`SensorScreen.tsx`)
- **Farmer Greeting**: `"Hello, Ramesh!"` with avatar and zone badge.
- **Zone Selector**: Quick-tap chips for Zone 1 (Paddy), Zone 2 (Orchard), Zone 3 (Polyhouse).
- **Rain Lockout Banner**: Highlights active rain lockout (`85% Rain Forecast 12mm`) and safety rationale.
- **Node Status**: Live ESP32 connection badge (`Online • Battery 94% • RSSI -62dBm`).
- **4 Metric Cards (2x2)**: Soil Moisture (`45.2%`), Soil & Air Temp (`26.8°C`), Air Humidity (`68.4%`), NPK Nutrients (`42:18:34 kg/ha`).
- **Irrigation Recommendation**: FAO-56 Engine output (`HOLD PUMP`).
- **Quick Action Grid**: Direct routes to Crop Advisory, Leaf Vision, Pump Control, and Telemetry.

### Screen 2: Crop Recommendation (`CropRecommendationScreen.tsx`)
- **Badge**: `REAL MODEL (RANDOM FOREST)`
- **Telemetry Pre-fill**: One-touch synchronization of soil NPK and climate telemetry from ESP32.
- **Primary Result Card**: Crop name (`Rice PR-126`), `99.1% Confidence`, yield potential, and AWD water plan.
- **Alternative Candidates**: Secondary viable crops (Cotton, Jute, Maize) with confidence rankings.

### Screen 3: Leaf Disease Vision (`VisionScreen.tsx`)
- **Badge**: `EXPERIMENTAL AI`
- **Scanning Viewfinder**: Clean camera guide frame with corner reticles and scanning laser indicator.
- **Diagnostic Result**: Disease classification (`Bacterial Leaf Blight`), pathogen (`Xanthomonas oryzae`), severity level, and dual biological + chemical management steps.

### Screen 4: Notifications & Alerts (`AlertsScreen.tsx`)
- **Filter Tabs**: All, Critical, Warning, Info.
- **Sync Badge**: Real-time indication of local SQLite and offline action synchronization state.
- **Notification Cards**: Canonical events across 15 types with read receipts and resolution actions.

### Screen 5: Settings & Edge Connectivity (`SettingsScreen.tsx`)
- **Farmer Profile**: Operator identity, farm boundary, and land holding details.
- **Multilingual Switcher**: Instant localization (English, Hindi, Punjabi, Telugu).
- **Offline Data Engine**: SQLite queue counter with idempotent sync trigger.
- **Edge Gateway Status**: Status of ESP32 node and Qualcomm Robotics RB5 Edge Gateway.

### Screen 6: Telemetry Trends (`TelemetryScreen.tsx`)
- **Interactive SVG Chart**: Continuous gradient area chart showing soil moisture dynamics against target bands.
- **Time Range Filters**: 1 Day, 7 Days, 30 Days.
- **Null-Preserving Data Table**: Strict preservation of SQL NULL values without replacement by zero.

### Screen 7: Decision Engine (`DecisionScreen.tsx`)
- **4-Stage Pipeline Stepper**:
  1. Sensor Telemetry (ESP32)
  2. FAO-56 Water Balance (Evapotranspiration rules)
  3. Safety & Weather Interlock (Rain Lockout)
  4. Grounded Output (`HOLD PUMP`)
- **Compliance Checklist**: Mathematical verification and audit provenance.

### Screen 8: Actuator Pump Control (`PumpControlScreen.tsx`)
- **Pump Status**: Real-time relay state, flow rate, and safety lockout condition.
- **Lifecycle Stepper**: 4 stages: `Requested -> Published -> Acknowledged -> Executed`.
- **Interlock Testing**: Demonstrates automatic command blocking under active rain forecast.
- **Emergency Override**: Audited farmer override switch.
