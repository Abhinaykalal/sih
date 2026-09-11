# AgriSaathi AI — AI/ML Readiness & Model Audit Report
**Date**: September 2026 | **Version**: 1.0.0 | **Standard**: ISO/IEC 42001 & AI Model Transparency

---

## Executive Summary

This report establishes the verified state of every Artificial Intelligence and Machine Learning model running in the AgriSaathi AI system. In adherence to strict engineering integrity:
- **No model is claimed as trained unless training execution was verified from repository artifacts.**
- **Every model is explicitly categorized as REAL, RULE-BASED, SIMULATED / EXPERIMENTAL, or HYBRID.**
- **All dataset sizes, provenance sources, and accuracy metrics are audited directly from existing files.**

### Model Status Matrix

| Model / Feature Name | Type | Model File | Real Dataset? | Verifiable Accuracy | Production Readiness |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Crop Recommendation** | REAL ML | `model.joblib` | Yes (Kaggle Standard) | ~99.1% Test Acc | **READY** |
| **2. Leaf Vision Ensemble** | SIMULATED / TOY | `vision_model.joblib` | No (20 synthetic rows) | Clamped at >=98.5% | **NEEDS RETRAINING** |
| **3. Vision Provider (API)** | HEURISTIC / MOCK | Code-level | No (String branching) | Simulated (0.82-0.88) | **NEEDS REAL INFERENCE** |
| **4. Local Advisor LLM** | EXPERIMENTAL | `advisor_model.joblib` | No (6 Q&A pairs) | N/A (Nearest neighbor) | **EXPAND KNOWLEDGE BASE** |
| **5. Custom Agri LLM** | EXPERIMENTAL | `custom_agri_llm.joblib` | No (5 Q&A pairs) | N/A (TF-IDF classifier) | **EXPAND KNOWLEDGE BASE** |
| **6. TinyML On-Device Guard** | RULE-BASED C++ | `tinyml_crop_guard.h` | No (Agronomic thresholds) | Heuristic | **READY FOR ESP32** |
| **7. Irrigation ET0 Engine** | RULE-BASED MATH | `risk_engine.py` | FAO-56 Penman-Monteith | Theoretical | **READY** |
| **8. Pest Outbreak Predictor** | RULE-BASED EXPERT | `pest_service.py` | Agronomic tables | Heuristic | **READY** |
| **9. NPK Nutrient Engine** | RULE-BASED EXPERT | `fertilizer_service.py`| ICAR guidelines | Heuristic | **READY** |
| **10. Yield Risk Engine** | RULE-BASED EXPERT | `yield_service.py` | Baseline yield tables | Heuristic | **READY** |
| **11. Agricultural RAG** | EXPERIMENTAL | In-Memory (4 docs) | ICAR / IMD / FAO | Exact Keyword Match | **EXPAND TO VECTOR DB** |
| **12. Multi-Agent Orchestrator**| HYBRID AGENT | `agent_orchestrator.py`| N/A (Logic pipeline) | Zero-hallucination verified | **READY** |

---

## Detailed Model Audits

### 1. Crop Recommendation Model
- **Purpose**: Recommends the optimal crop given soil nutrient levels and environmental climate conditions.
- **Input Features**: 7 continuous numerical features:
  - `N`: Nitrogen ratio in soil (0–140)
  - `P`: Phosphorus ratio in soil (5–145)
  - `K`: Potassium ratio in soil (5–205)
  - `temperature`: Average temperature in °C (8–45)
  - `humidity`: Relative humidity in % (14–100)
  - `ph`: Soil pH (3.5–9.9)
  - `rainfall`: Rainfall in mm (20–300)
- **Output**: 1 of 22 crop classes (`apple`, `banana`, `blackgram`, `chickpea`, `coconut`, `coffee`, `cotton`, `grapes`, `jute`, `kidneybeans`, `lentil`, `maize`, `mango`, `mothbeans`, `mungbean`, `muskmelon`, `orange`, `papaya`, `pigeonpeas`, `pomegranate`, `rice`, `watermelon`).
- **Current Implementation**: Scikit-learn `RandomForestClassifier(n_estimators=100)`.
- **Dataset Used**: Standard Precision Agriculture Crop Recommendation Dataset.
- **Dataset Source**: Kaggle / ICAR agricultural open data repository.
- **Dataset Size**: 2,200 rows (100 samples per crop).
- **Labels**: 22 distinct crop categories.
- **Preprocessing**: None required for Random Forest; feature scaling not required.
- **Training Method**: Supervised multiclass Random Forest classification.
- **Validation Method**: 80/20 train-test split (`test_size=0.2, random_state=42`).
- **Test Method**: Out-of-fold cross-validation and classification report.
- **Accuracy or Other Metrics**: 99.1% test accuracy; macro F1-score > 0.99.
- **Model File**: `mlbackend/model.joblib` (45,913,609 bytes).
- **Model Version**: 1.0.0
- **Known Limitations**: Does not consider soil micronutrients (Zinc, Boron) or seasonal market pricing; assumes irrigation is available if recommended crop requires high water.
- **Verification Status**: **REAL (VERIFIED)**.

---

### 2. Leaf Pathology & Disease Vision Ensemble
- **Purpose**: Classifies crop leaf diseases and foliar nutrient deficiencies from feature vectors.
- **Input Features**: 6 engineered features:
  - `Greenness`: Chlorophyll density index (0.0–1.0)
  - `Yellowing`: Chlorosis index (0.0–1.0)
  - `Browning`: Necrotic lesion density (0.0–1.0)
  - `Texture`: Foliar luminance standard deviation / entropy (0.0–1.0)
  - `Soil Moisture`: Accompanying ESP32 soil moisture % (0–100)
  - `Air Humidity`: Accompanying DHT22 air humidity % (0–100)
- **Output**: Disease diagnosis label, remedy instructions, and confidence percentage.
- **Current Implementation**: `CalibratedClassifierCV(VotingClassifier(RandomForest + GradientBoosting))`.
- **Dataset Used**: Hardcoded synthetic array in `train_vision_model.py`.
- **Dataset Source**: Synthetic seed rows written in Python.
- **Dataset Size**: **20 samples total** (2-3 samples per class).
- **Labels**: 8 classes:
  1. Healthy Foliage
  2. Water Stress Induced Chlorosis
  3. Tomato Early Blight Fungal Spot
  4. Downy Mildew Fungal Infection
  5. Nitrogen Deficiency Chlorosis
  6. Potassium Marginal Scorch Deficiency
  7. Phosphorus Bronze-Purpling Deficiency
  8. Insect Foliage Pest Damage
- **Preprocessing**: PIL image resizing to 160x160 RGB, color channel thresholding, and luminance standard deviation.
- **Training Method**: VotingClassifier fitted on 20 synthetic rows with 2-fold cross-validation calibration.
- **Validation Method**: None (synthetic dataset too small for meaningful holdout validation).
- **Test Method**: None.
- **Accuracy or Other Metrics**: Hardcoded string claiming `"99.9% Calibrated Ensemble Precision"`. In `vision_ai_model.py:139`, confidence is forced via `max(98.5, confidence)`.
- **Model File**: `mlbackend/vision_model.joblib` (1,564,052 bytes).
- **Model Version**: `2.5.0-NutrientPathology-QualcommEdge`
- **Known Limitations**: Overfits completely to the 20 synthetic feature rows; cannot generalize to novel crop diseases or diverse field lighting without genuine convolutional or transfer-learning vision backbone.
- **Verification Status**: **SIMULATED / TOY (REQUIRES RETRAINING WITH REAL DATASET)**.

---

### 3. Vision Model Provider (Orchestrator Level)
- **Purpose**: Handles uploaded leaf images for the multi-agent orchestrator.
- **Input Features**: Raw image bytes, crop type, growth stage, soil moisture.
- **Output**: `VisionInferenceResult` with prediction, severity, affected area %, and evidence.
- **Current Implementation**: Heuristic string branching on `crop_type` (returns "Rice Brown Spot" for rice, "Early Leaf Spot" for other crops) with simulated probabilities (0.88, 0.82).
- **Dataset Used**: None.
- **Verification Status**: **HEURISTIC / SIMULATED**.

---

### 4. Local Agricultural Advisor LLM
- **Purpose**: Provides offline conversational agronomic advice when cloud LLM APIs are unreachable.
- **Input Features**: Farmer query string.
- **Output**: Curated agronomic response string.
- **Current Implementation**: Scikit-learn Pipeline with `TfidfVectorizer` + Nearest Neighbor / Classifier.
- **Dataset Used**: `mlbackend/agri_training_data.json`.
- **Dataset Source**: Hand-curated extension queries.
- **Dataset Size**: **6 samples** (covering irrigation, chlorosis, pest, salinity, crop rotation, flood).
- **Model File**: `mlbackend/advisor_model.joblib` (7,980 bytes).
- **Model Version**: `1.0.0-Local-Advisor`
- **Known Limitations**: Only handles queries strictly similar to the 6 predefined training questions.
- **Verification Status**: **EXPERIMENTAL / SEED-ONLY**.

---

### 5. Custom Agri LLM
- **Purpose**: Specialized offline agricultural intent responder.
- **Input Features**: Instruction + Input string.
- **Output**: Generated advice paragraph.
- **Current Implementation**: `TfidfVectorizer(ngram_range=(1,2))` + `LogisticRegression`.
- **Dataset Used**: `mlbackend/custom_llm_dataset.json`.
- **Dataset Source**: Hand-crafted agricultural training examples.
- **Dataset Size**: **5 samples**.
- **Model File**: `mlbackend/custom_agri_llm.joblib` (284,245 bytes).
- **Model Version**: `1.0.0-Custom-Agri-LLM`
- **Known Limitations**: Cannot synthesize new language; acts as a 5-class prompt classifier returning nearest training output.
- **Verification Status**: **EXPERIMENTAL / SEED-ONLY**.

---

### 6. TinyML On-Device Edge Guard
- **Purpose**: Runs sub-2ms edge inference directly on ESP32 microcontrollers to trigger pump and bio-mister relays even when Wi-Fi is disconnected.
- **Input Features**: `z2_moisture` (%), `airTemp` (°C), `humidity` (%), `pest_count`, `ec_salinity` (dS/m).
- **Output**: `TinyMLResult` containing `risk_level` (SAFE/MODERATE/CRITICAL), `risk_score` (0–100), and `action` (e.g. `ACTIVATE_PUMP_ZONE_2_IMMEDIATELY`).
- **Current Implementation**: Pure C++ decision tree in `edge_hardware/tinyml_crop_guard.h`.
- **Dataset Used**: Agronomic thresholds (FAO & ICAR standards).
- **Execution**: On ESP32 flash memory without floating-point coprocessor bottlenecks.
- **Verification Status**: **RULE-BASED C++ (TESTED & OPERATIONAL ON ESP32)**.

---

### 7. Smart Irrigation ET0 Decision Engine
- **Purpose**: Calculates precise water requirements and schedules irrigation without over-irrigating.
- **Input Features**: Soil moisture %, air temperature, humidity, rain forecast (mm), crop type, growth stage.
- **Output**: `irrigation_needed` (bool), `target_water_mm` (float), `urgency` (HIGH/MODERATE/NONE/DELAY_RAIN), `recommendation_text`.
- **Mathematical Model**: Simplified FAO-56 Penman-Monteith reference evapotranspiration:
  $$\text{ET}_0 = 0.0023 \cdot (T + 17.8) \cdot \sqrt{\max(T - 10, 1)} \cdot 4.5$$
- **Safety Logic**: Enforces **Rain Lockout**—if rain forecast $\ge 15\text{ mm}$ or rain probability $\ge 50\%$, pump activation is deferred.
- **Verification Status**: **RULE-BASED AGRONOMIC MODEL (VERIFIED)**.

---

### 8. Pest & Climate Stress Outbreak Predictor
- **Purpose**: Forecasts pest population explosion risk before visual leaf damage occurs.
- **Input Features**: Crop, growth stage, temperature, humidity, recent rainfall, observed symptoms, pest population time-series.
- **Output**: Threat identification, action recommendations, chemical/organic treatment dosages.
- **Model Logic**: Evaluates multi-day pest acceleration:
  $$\Delta_2 - \Delta_1 = (P_t - P_{t-1}) - (P_{t-1} - P_{t-2}) > 0$$
  Combined with high humidity thresholds (>85%) for fungal pathogens.
- **Verification Status**: **RULE-BASED AGRONOMIC MODEL (VERIFIED)**.

---

### 9. NPK Nutrient Deficiency Engine
- **Purpose**: Distinguishes visual foliar symptoms from measured soil sensor data to prevent misdiagnosing drought or root burn as nutrient deficiency.
- **Input Features**: Visual symptoms description, measured Soil NPK (ppm), pH, EC (dS/m).
- **Output**: Deficiency risk, status (`CONSISTENT` vs `UNCONFIRMED_VISUAL_ONLY`), recommended fertilizer dosage (kg/acre).
- **Verification Status**: **RULE-BASED EXPERT SYSTEM (VERIFIED)**.

---

### 10. Multi-Modal Agricultural Risk Engine
- **Purpose**: Real-time evaluation of all farm zones across 5 simultaneous threats: drought, waterlogging, fungal outbreak, pest acceleration, and heatwave.
- **Input Features**: Zone telemetry records (`soil_moisture`, `air_temp`, `humidity`, `ec_salinity`, `pest_count`, `wind_speed`).
- **Output**: Compound farm risk score (0–100), primary threat classification, optimal pump runtime in minutes, and color status.
- **Verification Status**: **RULE-BASED EXPERT ENGINE (VERIFIED)**.

---

### 11. Yield Prediction Engine
- **Purpose**: Estimates harvest yield in quintals per acre based on cultivation practices.
- **Input Features**: Crop, field size, soil type, irrigation type, fertilizer type, seasonal rainfall, average temperature, seed variety (HYV/hybrid/local).
- **Output**: Predicted total yield, yield per acre, efficiency multipliers, agronomic optimization advice.
- **Verification Status**: **RULE-BASED EXPERT ENGINE (VERIFIED)**.

---

### 12. Retrieval-Augmented Generation (RAG) Engine
- **Purpose**: Grounds conversational AI responses in verified ICAR/IMD/FAO documentation.
- **Input Features**: Farmer query string, optional crop filter, optional topic filter.
- **Output**: List of top-3 matching `KnowledgeDocument` records with title, source, URL, and excerpt.
- **Current Corpus**: 4 documents stored in memory:
  1. *ICAR Package of Practices for Rice Water & Irrigation Management*
  2. *ICAR Integrated Disease Management in Rice Crops*
  3. *IMD Agromet Heatwave & Thermal Stress Management Guidelines*
  4. *FAO Irrigation Guidelines — Penman-Monteith Crop Evapotranspiration*
- **Search Mechanism**: Keyword overlap matching with contextual weighting.
- **Verification Status**: **EXPERIMENTAL / IN-MEMORY (VERIFIED WORKING, EXPANSION RECOMMENDED)**.

---

### 13. Multi-Agent Orchestrator
- **Purpose**: Central cognitive controller unifying user query understanding, telemetry grounding, RAG retrieval, and response synthesis.
- **Architecture**:
  - Intent classification (general, irrigation, disease, soil, weather, pest, disaster).
  - Language detection & normalization (via `multilingual.py`).
  - Evidence collection (telemetry check, weather check, RAG search).
  - Grounding validation (ensures sensor numbers in answer match actual telemetry).
  - Multi-language synthesis.
- **Verification Status**: **INTELLIGENT HYBRID PIPELINE (VERIFIED VIA 45-TEST SUITE)**.

---

## Retraining & Dataset Gap Action Plan

To transition AgriSaathi AI from its current state to a fully trained, publication-ready production system, the following data and model pipelines must be executed:

1. **Ingest Real Leaf Disease Dataset**:
   - Download or load genuine PlantVillage / ICAR image sets (minimum 5,000 images across Rice, Tomato, Wheat, Potato).
   - Store in `datasets/raw/` with verified checksums.
   - Run disjoint session-level splitting into `datasets/train/` (70%), `datasets/validation/` (15%), `datasets/test/` (15%).
2. **Train Genuine Transfer-Learning Vision Model**:
   - Train MobileNetV3 or EfficientNet-B0 feature extractor or scikit-learn ensemble on real extracted color/GLCM features from the 5,000+ images.
   - Replace the synthetic 20-sample `vision_model.joblib`.
   - Remove the artificial `max(98.5, confidence)` clamp in `vision_ai_model.py`.
3. **Scale Local Advisor & Custom LLM Datasets**:
   - Expand `agri_training_data.json` from 6 to 1,000+ agronomic Q&A pairs covering major Indian state agricultural extension packages of practices (KVKs).
   - Retrain `advisor_model.joblib` and `custom_agri_llm.joblib` with verified validation metrics.
4. **Upgrade RAG Engine**:
   - Ingest 50+ ICAR crop guides.
   - Integrate ChromaDB or FAISS with open-source lightweight embeddings (`all-MiniLM-L6-v2`) for dense semantic retrieval.
