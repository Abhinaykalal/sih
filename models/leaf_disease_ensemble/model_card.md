# Model Card — AgriSaathi Leaf Disease Ensemble v1.2.0

## Model Details
- **Developer**: AgriSaathi AI Engineering Team (SIH26180)
- **Model Architecture**: Hybrid Ensemble (RandomForest + GradientBoosting + MobileNet Feature Extractor)
- **Model Version**: 1.2.0
- **Model Hash**: `e9a41f80c619b02a`
- **Release Date**: March 2026

## Intended Use
- **Primary Use**: Diagnostic decision support for paddy rice and field crop leaf diseases.
- **Out-of-Scope**: Non-agricultural general object recognition.

## Training Data & Provenance
- **Dataset**: 15,000 curated leaf photographs (PlantVillage + ICAR Field Library).
- **Dataset License**: CC BY-SA 4.0
- **Split Strategy**: 70% Train / 15% Validation / 15% Test grouped strictly by Plant & Session ID to prevent data leakage.

## Evaluation Metrics (Held-Out Test Set)
| Metric | Score |
| :--- | :--- |
| **Accuracy** | **94.2%** |
| **Macro F1-Score** | **93.8%** |
| **Precision** | **94.5%** |
| **Recall** | **93.2%** |
| **Inference Latency** | **42 ms** (Server) / **18 ms** (Edge) |

## Limitations & Known Failure Cases
- **Low Light**: Photos taken under poor flash or night lighting reduce confidence by ~15%.
- **Extremely Early Symptoms**: Micro-lesions < 1mm require close-up macro focus.
