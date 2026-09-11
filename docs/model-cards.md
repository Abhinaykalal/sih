# AgriSaathi AI — Model Cards

## Model Card 1: Crop Recommendation Model (`model.joblib`)

| Field | Value |
|-------|-------|
| **Model Type** | Random Forest Classifier |
| **Framework** | scikit-learn 1.x |
| **Input Features** | N, P, K (ppm), Temperature (°C), Humidity (%), pH, Rainfall (mm) |
| **Output** | Crop class label + probability distribution |
| **Classes** | 22 crops (rice, wheat, maize, cotton, sugarcane, jute, lentil, chickpea, kidney beans, pigeonpeas, mothbeans, mungbeans, blackgram, banana, mango, grapes, watermelon, muskmelon, apple, orange, papaya, coconut) |
| **Training Data** | Kaggle Crop Recommendation Dataset (2,200 samples) |
| **Accuracy** | ~99.1% cross-validated accuracy |
| **Last Trained** | SIH 2026 Phase 1 |
| **Known Limitations** | Trained on idealized soil data; requires real-world calibration before farmer deployment |
| **Use in AgriSaathi** | `/api/recommend` endpoint |

---

## Model Card 2: Vision / Crop Disease Detection (`vision_model.joblib`)

| Field | Value |
|-------|-------|
| **Model Type** | CNN feature extractor + Random Forest classifier |
| **Framework** | scikit-learn + Pillow for preprocessing |
| **Input** | RGB crop leaf image (any resolution, resized to 64×64) |
| **Output** | Disease class + confidence + severity + recommended actions |
| **Classes Supported** | Healthy, Bacterial Blight, Blast, Sheath Blight, Brown Spot, Leaf Folder, False Smut, Nitrogen Deficiency, Phosphorus Deficiency |
| **Supported Crops** | Rice (primary), Wheat, Maize (partial support) |
| **Training Data** | PlantVillage dataset subset + ICAR field imagery |
| **Performance** | ~78% accuracy on validation set (limited by training set quality) |
| **Known Limitations** | Low confidence on unusual lighting; requires good photo quality |
| **Confidence Threshold** | Results with confidence < 0.55 are flagged as "uncertain — consult local agronomist" |
| **Use in AgriSaathi** | `/api/agent/chat` (disease intent) + `/api/vision-analyze` |

---

## Model Card 3: Irrigation Assessment Model (Rule-Based + ET₀)

| Field | Value |
|-------|-------|
| **Model Type** | Physics-based (Penman-Monteith ET₀ simplified) + thresholds |
| **Framework** | Pure Python (no ML dependencies) |
| **Input** | Soil moisture (%), air temp (°C), humidity (%), rain forecast (mm), crop type, growth stage |
| **Output** | Irrigation needed (bool), recommended water (mm), confidence, recommendation text |
| **Crop-Specific Thresholds** | Rice: 45–75%, Wheat: 35–55%, Cotton: 40–65%, etc. |
| **Known Limitations** | Simplified ET₀ (full Penman-Monteith needs wind speed data) |
| **Data Dependency** | Requires live ESP32 soil moisture readings for reliable output |
| **Use in AgriSaathi** | `/api/irrigation/assess` + integrated via `AgentOrchestrator` |

---

## Model Card 4: Nutrient Deficiency Analyzer (Agronomic Rules)

| Field | Value |
|-------|-------|
| **Model Type** | Agronomic rule engine with ICAR TNAU thresholds |
| **Framework** | Pure Python |
| **Input** | N, P, K (ppm), pH, EC (dS/m), crop, growth stage |
| **Output** | Deficiency flags, severity, fertilizer recommendations |
| **Knowledge Source** | ICAR-TNAU fertilizer dose tables, IARI agronomic guidelines |
| **Known Limitations** | Does not account for soil texture or CEC; needs adaptation for local soil types |
| **Use in AgriSaathi** | Invoked via `AgentOrchestrator` on NPK-related user queries |

---

## Model Card 5: RAG Knowledge Engine (Agricultural Search)

| Field | Value |
|-------|-------|
| **Type** | Retrieval-Augmented Generation (RAG) search engine |
| **Index Backend** | scikit-learn TF-IDF + cosine similarity (offline, no GPU needed) |
| **Knowledge Base** | ICAR guidelines, IMD advisories, TNAU crop management, Krishi Vigyan Kendra recommendations |
| **Document Count** | ~150 curated agronomic documents (Phase 1) |
| **Languages Indexed** | English (Hindi planned in Phase 2) |
| **Retrieval Strategy** | Top-3 documents by cosine similarity, filtered by crop type |
| **Use in AgriSaathi** | All agent responses are RAG-grounded; sources listed in `StructuredAgentResponse.sources` |

---

## Model Card 6: Edge AI Inference Interface (TFLite/ONNX)

| Field | Value |
|-------|-------|
| **Status** | Interface ready; models pending quantization |
| **Target Runtime** | TensorFlow Lite (Android APK), ONNX Runtime (Qualcomm gateway) |
| **Quantization** | INT8 post-training quantization (PTQ) for mobile |
| **Target Accuracy After Quantization** | < 2% degradation from full-precision |
| **APK Integration** | Android app uses `ApiClient` → backend inference by default; local TFLite ready for offline mode |
| **Use in AgriSaathi** | Offline disease diagnosis when no internet connection |

---

## Bias & Fairness Notes

- All models were trained on publicly available agricultural datasets predominantly from South/North Indian farming conditions.
- Performance may vary for hill agriculture, arid zone farming (Rajasthan, Gujarat) and tribal farming areas.
- Planned future work: fine-tuning on state-specific (Punjab, Andhra Pradesh, Maharashtra) data from KVK field recordings.

## Data Governance

- No farmer PII is stored in any model weights.
- Conversation memory is stored locally on the backend server (SQLite) and not shared with third parties.
- Supabase cloud sync (optional) encrypts telemetry data at rest.
- API keys (Gemini, OpenWeather, Supabase) are stored server-side only and never embedded in the Android APK.
