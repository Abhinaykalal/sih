# AgriSaathi AI — Android APK Build & Deployment Guide

This document contains step-by-step instructions for building, packaging, installing, and testing the farmer-facing **AgriSaathi AI Android Application APK** (SIH26180).

---

## 1. Environment & Tools Prerequisites

To compile the Android APK, ensure the following software tools are installed on your build machine:

- **Operating System**: Windows 10/11, macOS, or Linux
- **Node.js**: `v18.0.0` or later (tested on Node `v24.14.0`)
- **npm**: `v10.0.0` or later (tested on npm `v11.9.0`)
- **Java Development Kit (JDK)**: **JDK 17 (LTS)** or **JDK 21**
- **Android SDK**: API Level **34** (Android 14.0) with Build Tools **34.0.0**
- **Gradle**: **Gradle 8.2.1** (automatically supplied via `gradlew`)
- **Android Device / Emulator**: Android 7.0+ (API 24+) physical phone or Android Studio AVD

---

## 2. Environment Variables Setup

Configure the environment variables in your system / shell profile (`~/.bashrc`, `~/.zshrc`, or Windows Environment Variables):

```bash
# Java Home Configuration
export JAVA_HOME="C:\Program Files\Java\jdk-17"  # Adjust for your JDK installation path
export PATH="$JAVA_HOME/bin:$PATH"

# Android SDK Path
export ANDROID_HOME="C:\Users\<YourUsername>\AppData\Local\Android\Sdk" # Windows
# export ANDROID_HOME="$HOME/Library/Android/sdk"                      # macOS
export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH"

# AgriSaathi Backend URL for Android Physical Phone Testing
export AGRISAATHI_API_URL="http://192.168.1.100:8000"
```

---

## 3. Project Structure

```
agrisaathi-sih/
├── android-app/                       # Primary Farmer Android Application
│   ├── android/                       # Native Android Gradle Project
│   │   ├── app/
│   │   │   ├── build.gradle          # App module Gradle configuration
│   │   │   └── src/main/
│   │   │       └── AndroidManifest.xml # Permissions (Camera, Mic, Internet)
│   │   ├── build.gradle              # Project-level Gradle build script
│   │   ├── settings.gradle           # Settings Gradle script
│   │   ├── gradlew                   # Linux/macOS Gradle Wrapper
│   │   └── gradlew.bat               # Windows Gradle Wrapper
│   ├── src/
│   │   ├── services/
│   │   │   ├── ApiClient.ts          # Centralized Network Abstraction
│   │   │   └── OfflineStore.ts       # Local Offline Cache & Sync Queue
│   │   └── screens/
│   │       ├── ChatScreen.tsx        # AgriSaathi AI Voice/Text Assistant
│   │       ├── VisionScreen.tsx      # Leaf Image AI Vision Diagnosis
│   │       ├── SensorScreen.tsx      # Live ESP32 Telemetry Dashboard
│   │       ├── ProvisioningScreen.tsx# ESP32 Device Registration
│   │       ├── AlertsScreen.tsx      # Resilience Warnings & Dispatch
│   │       └── SettingsScreen.tsx    # Configurable AGRISAATHI_API_URL
│   ├── App.tsx                        # Main App Shell & Bottom Navigation
│   ├── app.json                       # Expo / Android Build Config
│   └── package.json                   # React Native Dependencies
```

---

## 4. Configuring Backend Server URL (`AGRISAATHI_API_URL`)

> ⚠️ **IMPORTANT**: On a physical Android smartphone, `localhost` or `127.0.0.1` points to **the smartphone itself**, not your laptop running the backend!

### Finding Your Computer's LAN IP:
1. On Windows: Open Command Prompt / PowerShell and run `ipconfig`. Find `IPv4 Address` (e.g. `192.168.1.50`).
2. On macOS/Linux: Run `ifconfig` or `ip a` (e.g. `192.168.1.50`).

### Setting the URL in the App:
- Launch the AgriSaathi Android App.
- Open **Settings (⚙️)** from the top right or tab bar.
- Update **AgriSaathi Backend Server URL** to `http://<YOUR_LAN_IP>:8000`.
- Tap **Save & Test Server Connection**.

---

## 5. Building Debug APK

Navigate to the `android-app` directory and install dependencies:

```bash
cd android-app
npm install
```

To compile a **Debug APK** using the native Android Gradle Wrapper:

### Windows (PowerShell / CMD):
```powershell
cd android
.\gradlew.bat assembleDebug
```

### macOS / Linux:
```bash
cd android
chmod +x gradlew
./gradlew assembleDebug
```

### Debug APK Output Location:
```
android-app/android/app/build/outputs/apk/debug/app-debug.apk
```

---

## 6. Building Release APK

To compile an optimized **Release APK**:

### Windows (PowerShell / CMD):
```powershell
cd android
.\gradlew.bat assembleRelease
```

### macOS / Linux:
```bash
cd android
./gradlew assembleRelease
```

### Release APK Output Location:
```
android-app/android/app/build/outputs/apk/release/app-release-unsigned.apk
```

---

## 7. Installing APK onto Android Physical Device

1. Enable **Developer Options** and **USB Debugging** on your Android smartphone.
2. Connect the smartphone to your laptop via USB.
3. Verify connection via `adb`:
   ```bash
   adb devices
   ```
4. Install the compiled APK:
   ```bash
   adb install -r android/app/build/outputs/apk/debug/app-debug.apk
   ```

---

## 8. Physical-Device Testing Flow

Once installed, execute the following end-to-end SIH demonstration test:

1. **Backend Server Launch**:
   ```bash
   cd mlbackend
   python main.py
   ```
2. **Launch App**: Open AgriSaathi AI on phone.
3. **Verify API Connection**: Check top bar status indicator.
4. **AI Chat Test**: Ask *"Should I irrigate my rice field?"* -> Verify live ESP32 moisture telemetry & weather are queried dynamically by backend AI agent.
5. **Leaf Vision Test**: Go to **Leaf AI**, capture/select crop leaf image -> Verify confidence, severity, and recommended actions.
6. **Live ESP32 Dashboard**: Go to **Sensors**, verify soil moisture %, soil temp, NPK breakdown, and signal metrics.
7. **Offline Mode Test**: Toggle Airplane mode on phone -> App switches to **OFFLINE MODE** with cached telemetry and queued sync actions.

---

## 9. Security & Secret Integrity

- **No Secrets in APK**: The APK contains **NO** LLM API keys, Supabase service-role keys, or weather secrets.
- **Backend Isolation**: All third-party secrets remain strictly inside `.env.local` on the FastAPI server.
