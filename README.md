# AgriSaathi AI — Precision Agriculture Platform

> **Full-stack AI-powered precision agriculture system** with ESP32 IoT telemetry, multilingual RAG (ICAR/IMD/FAO), hybrid LLM inference (Ollama local + Groq cloud), FastAPI backend, and a React Native Android app.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React Native](https://img.shields.io/badge/React%20Native-Expo-61DAFB?logo=react)](https://expo.dev)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase)](https://supabase.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)

---

## Features

| Module | Description |
|---|---|
| **Sensor Dashboard** | Live ESP32 telemetry — soil moisture, NPK, temperature, humidity, pH |
| **Smart Pump Control** | 4-stage MQTT command lifecycle with rain lockout safety gate |
| **AI Chat** | Multilingual RAG (EN/HI/TE) grounded on ICAR/IMD/FAO verified docs |
| **Crop Recommendation** | ML model with 22 crops, live telemetry pre-fill |
| **Leaf Vision** | Image-based disease detection |
| **Alerts System** | Real-time agronomic anomaly notifications |
| **Offline Mode** | Full offline queue with background sync via AsyncStorage |

---

## Architecture

```
Android App (Expo/React Native)
    │
    ├─ ApiClient.ts → FastAPI backend (local or Render)
    │
FastAPI Backend (mlbackend/)
    ├─ /api/ai/chat       → HybridLLMProvider → [Ollama | Groq | RAG_ONLY]
    ├─ /api/ai/rag/query  → MultilingualRAGService (ICAR/IMD/FAO docs)
    ├─ /api/sensor/       → ESP32 telemetry + Supabase
    ├─ /api/pump/         → PumpController (safety-gated, MQTT)
    ├─ /api/crop/         → Scikit-learn ML model
    └─ /health            → Health probe

ESP32 (edge_hardware/)
    └─ MQTT → FastAPI → Supabase → Android
```

---

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/Abhinaykalal/sih.git
cd sih
```

### 2. Backend Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env.local
# Edit .env.local with your Supabase URL, API keys, etc.

# Start the backend
python -m uvicorn mlbackend.main:app --host 127.0.0.1 --port 8000 --reload
# API docs: http://127.0.0.1:8000/docs
# Health:   http://127.0.0.1:8000/health
```

### 3. Ollama Setup (Local AI — Development Only)
```bash
# Install Ollama from https://ollama.com
# Pull the recommended model
ollama pull qwen2.5:7b-instruct

# Ollama runs automatically on http://127.0.0.1:11434
# The backend detects it at startup
```

### 4. RAG Knowledge Base
The RAG system indexes verified documents automatically at startup from `data/rag/`.
To re-index manually:
```bash
POST http://127.0.0.1:8000/api/ai/rag/reindex
```

### 5. Android App Setup
```bash
cd android-app
npm install

# For Expo Go (physical device):
npx expo start

# For debug APK build:
cd android
.\gradlew clean assembleDebug
# APK → android/app/build/outputs/apk/debug/app-debug.apk
```

### 6. Configure Backend URL in App
In the app → **Settings** → **Backend URL**, enter:
- **Emulator**: `http://10.0.2.2:8000`
- **Physical device (same WiFi)**: `http://<your-LAN-IP>:8000`
- **Cloud (Render)**: `https://agrisaathi-api.onrender.com`

---

## Environment Variables

See [`.env.example`](.env.example) for a full list. Key variables:

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase anon or service-role key |
| `GROQ_API_KEY` | Groq cloud LLM key (for Render deployment) |
| `GROQ_MODEL` | Groq model name (default: `llama-3.1-8b-instant`) |
| `OLLAMA_BASE_URL` | Ollama server URL (default: `http://127.0.0.1:11434`) |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API key |

---

## LLM Provider Logic

The backend auto-selects the best available provider at runtime:

```
1. Ollama (if reachable at OLLAMA_BASE_URL)  → used in local development
2. Groq  (if GROQ_API_KEY is set)           → used on Render/cloud
3. RAG_ONLY (honest fallback)               → returns source-backed excerpts
                                               with full ICAR/IMD/FAO citations
```

The active provider is always reported in `/api/ai/status` and each AI response. **No API key is ever returned in any API response or logged.**

---

## Cloud Deployment (Render)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New Web Service** → connect your GitHub repo
3. Render auto-detects `render.yaml`
4. Add secret env vars in Render Dashboard → Environment:
   - `GROQ_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `OPENWEATHER_API_KEY`
5. Deploy → your API will be at `https://agrisaathi-api.onrender.com`

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health probe |
| `/api/ai/status` | GET | Provider status + RAG stats |
| `/api/ai/chat` | POST | Grounded multilingual AI chat |
| `/api/ai/rag/query` | POST | Direct RAG query |
| `/api/ai/rag/sources` | GET | Indexed document list |
| `/api/sensor/telemetry/{device_id}` | GET | Live sensor data |
| `/api/pump/state/{device_id}` | GET | Pump state |
| `/api/pump/command` | POST | Dispatch pump command |
| `/api/crop/recommend` | POST | ML crop recommendation |
| `/api/notifications/` | GET | Farm alerts |

Full Swagger docs: `http://localhost:8000/docs`

---

## Safety Guarantees

- **Pump safety**: The LLM has zero authority over pump actuation. All commands require user confirmation and are dispatched only through `pump_controller.py` with hardware-enforced rain lockout.
- **No hallucination**: If RAG returns 0 chunks, response is `UNAVAILABLE` — never fabricated content.
- **No key leakage**: API keys are loaded exclusively from environment variables and never appear in responses, logs, or source code.

---

## Test Suite

```bash
# RAG + Ollama integration tests (12 tests)
python -m pytest mlbackend/test_rag_ollama.py -v

# Full integration suite (44 tests)
python -m pytest mlbackend/test_integration.py -v

# RAG data leakage check
python mlbackend/check_rag_leakage.py
```

---

## Project Structure

```
agrisaathi-sih/
├── mlbackend/              # FastAPI backend
│   ├── main.py             # Routes + middleware
│   ├── llm_provider.py     # Hybrid LLM (Ollama/Groq/RAG_ONLY)
│   ├── rag_service.py      # Multilingual RAG
│   ├── ollama_service.py   # Ollama wrapper
│   ├── pump_controller.py  # Safety-gated pump control
│   ├── db_layer.py         # Supabase + SQLite abstraction
│   └── ...
├── android-app/            # React Native Expo app
│   └── src/
│       ├── screens/        # All app screens
│       ├── services/       # ApiClient, OfflineStore
│       └── components/     # ProvenanceBadge, etc.
├── data/rag/               # RAG training/validation/test splits
├── edge_hardware/          # ESP32 firmware & MQTT configs
├── docs/                   # Validation reports
├── render.yaml             # Render.com deployment blueprint
├── Dockerfile              # Docker container config
└── .env.example            # Environment variables template
```

---

## Hardware (ESP32)

The ESP32 node reads:
- Soil moisture (capacitive sensor)
- Temperature & humidity (DHT22)
- Soil NPK (RS485 sensor)
- Rain detection

And publishes to the MQTT broker at topic `agrisaathi/esp32/{device_id}/telemetry`.

---

## License

This project is developed for Smart India Hackathon (SIH). All agricultural advisory content is sourced from ICAR, IMD, FAO, and PJTSAU verified extension publications.
