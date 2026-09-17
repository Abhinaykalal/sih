# Model Card — AgriSaathi Vision Classifier v1.2.0

## Model Details
- **Developer**: AgriSaathi AI Engineering Team (SIH26180)
- **Model Architecture**: LinearSVC with HOG/RGB Feature Extraction
- **Model Version**: 1.2.0

## Intended Use
- **Primary Use**: Diagnostic decision support for field crop leaf diseases.
- **Out-of-Scope**: Non-agricultural general object recognition.

## Training Data & Provenance
- **Dataset**: 100 empirically verified leaf photographs.
- **Split Strategy**: GroupShuffleSplit strictly by `group_id` via `vision_manifest.csv` to prevent data leakage.

## Evaluation Metrics (Held-Out Test Set)
*Metrics are generated at training time in the console output. We do not hardcode synthetic metrics in this static file.*
*Independent edge/server latency metrics are intentionally omitted as they have not yet been benchmarked on target hardware.*

## Limitations & Known Failure Cases
- **Low Light**: Photos taken under poor flash or night lighting reduce confidence.
- **Extremely Early Symptoms**: Micro-lesions < 1mm require close-up macro focus.
