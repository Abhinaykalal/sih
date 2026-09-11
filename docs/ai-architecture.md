# AgriSaathi AI — Intelligence, RAG & Agent Architecture Documentation

This document describes the multi-model AI agent architecture, evidence fusion pipeline, dataset quality standards, model provenance, and response validation engine in **AgriSaathi AI** (SIH26180).

---

## 1. System Architecture & Flow

```
USER QUERY / CROP PHOTO
           │
           ▼
   POST /api/agent/chat (Agent Orchestrator)
           │
           ├───────────────────────────┼───────────────────────────┐
           ▼                           ▼                           ▼
  Specialized ML Models      Live Telemetry & Weather     RAG Knowledge Vector Search
  - VisionModelProvider       - ESP32 Moisture / Temp      - ICAR Guidelines
  - IrrigationModelProvider   - OpenWeatherMap Forecast    - IMD Agromet Bulletins
  - NutrientModelProvider     - Stale Sensor Guard         - FAO-56 ET0 Standards
           │                           │                           │
           └───────────────────────────┴───────────────────────────┘
                                       │
                                       ▼
                            Evidence Fusion Engine
                                       │
                                       ▼
                           LLM Response Generation
                         (Cloud LLM / Ollama Local)
                                       │
                                       ▼
                            Response Validator Guard
                       (Grounding & Anti-Hallucination)
                                       │
                                       ▼
                            Structured Response JSON
```

---

## 2. Model Providers & Calibration (`mlbackend/model_providers.py`)

Every AI prediction is produced by a specialized model provider with calibrated confidence:

- **`VisionModelProvider`**: Computer vision pathology classification with Out-of-Distribution (OOD) and blurry/uninformative image detection.
- **`IrrigationModelProvider`**: Multi-variable agronomic irrigation engine combining Penman-Monteith Evapotranspiration (ET0), soil moisture %, soil temp, humidity, and rainfall forecast.
- **`NutrientDeficiencyModelProvider`**: Distinguishes visually observed symptom hypotheses from measured soil NPK sensor data.

---

## 3. RAG Knowledge Search (`mlbackend/rag_engine.py`)

- **Trusted Sources Only**: Ingests authentic ICAR (Indian Council of Agricultural Research), IMD (India Meteorological Department), and FAO advisories.
- **Contextual Filtering**: Filters retrieval by crop (e.g. Rice), region (e.g. Telangana / Punjab), topic (e.g. irrigation / disease), and language.
- **Zero Source Hallucination**: Every citation returns genuine document metadata (title, source, URL, publication date).

---

## 4. Dataset Quality & Leakage Prevention (`mlbackend/dataset_pipeline.py`)

- **Disjoint Split Strategy**: Prevents data leakage by splitting training, validation, and test sets strictly at the **Plant-Level and Session-Level**.
- **Quality Audits**: Deduplication via perceptual hashing (pHash) and MD5 checksums.

---

## 5. Structured Response API Contract (`POST /api/agent/chat`)

```json
{
  "answer": "**What I Found:** Your soil moisture is currently **42.5%** with an air temperature of **29.2°C**.\n\n**Assessment:** Soil moisture is currently optimal (42.5%). Evapotranspiration loss is 2.1 mm/day. No immediate irrigation required.",
  "language": "en",
  "intent": "irrigation_assessment",
  "confidence": {
    "overall": 0.94,
    "level": "high",
    "calibration_method": "Platt_Scaling_Validation"
  },
  "evidence": [
    { "type": "sensor", "name": "soil_moisture", "value": 42.5, "unit": "%" },
    { "type": "weather", "name": "rain_forecast", "value": 0.0, "unit": "mm" }
  ],
  "actions": [
    "Maintain current irrigation schedule.",
    "Reassess after expected weather changes."
  ],
  "sources": [
    {
      "title": "ICAR Package of Practices for Rice Water & Irrigation Management",
      "source": "ICAR - Indian Institute of Rice Research (IIRR)",
      "url": "https://www.icar-iirr.org/advisories/water_management.pdf"
    }
  ],
  "model_versions": {
    "agent_orchestrator": "2.0.0",
    "vision_model": "1.2.0",
    "irrigation_model": "2.0.0",
    "rag_engine": "1.0.0"
  }
}
```
