"""
AgriSaathi Vision Model Training Script
=======================================
Execution Command:
    python -m mlbackend.training.train_vision

Executes the full vision training pipeline:
- Ingests PlantDoc foliar images from datasets/raw/plantdoc/
- Deduplicates and validates image integrity (MD5)
- Performs disjoint stratified split (70/15/15) with leakage verification
- Extracts foliar chromatic signatures (greenness, chlorosis, browning, texture)
- Trains a Calibrated Voting Ensemble (Random Forest + Gradient Boosting)
- Evaluates on held-out test set with honest per-class metrics
- Exports model artifacts, metadata, metrics, and evaluation report to models/leaf_disease_vision/

If PlantDoc archive is not downloaded, trains on synthetic test fixture (TEST_ONLY).
"""

import os
import json
import joblib
from datetime import datetime, timezone

from mlbackend.vision.pipeline import run_pipeline
from mlbackend.vision.test_fixture import generate_and_train_test_fixture
from mlbackend.datasets.validator import DatasetValidator

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
MODELS_DIR = os.path.join(ROOT_DIR, "models", "leaf_disease_vision")
PLANTDOC_DIR = os.path.join(ROOT_DIR, "datasets", "raw", "plantdoc")
PLANTVILLAGE_DIR = os.path.join(ROOT_DIR, "datasets", "raw", "plantvillage")
OUTPUT_MODEL = os.path.join(ROOT_DIR, "mlbackend", "vision_model.joblib")

def main():
    print("=========================================================")
    print("AgriSaathi — Vision Pathology Model Training & Evaluation")
    print("=========================================================")
    os.makedirs(MODELS_DIR, exist_ok=True)

    # Auto-detect available datasets
    dataset_dirs = []
    for name, path in [("PlantDoc", PLANTDOC_DIR), ("PlantVillage", PLANTVILLAGE_DIR)]:
        if os.path.exists(path):
            dataset_dirs.append(path)
            print(f"  Found dataset: {name} at {path}")
        else:
            print(f"  Dataset not found: {name} ({path})")

    # Run the full pipeline with all available datasets
    result = run_pipeline(
        dataset_dirs=dataset_dirs if dataset_dirs else None,
        dataset_dir=PLANTDOC_DIR,  # fallback for backward compat
        output_model_path=OUTPUT_MODEL
    )

    is_real = result.get("status") == "COMPLETED_REAL_DATA"
    is_fixture = not is_real

    if is_real:
        status = "EXPERIMENTAL"
        test_metrics = result.get("test_metrics", {})
        val_metrics = result.get("validation_metrics", {})
        classes_trained = result.get("classes_trained", 0)
        limitations = [
            "Trained on PlantDoc dataset (~2,600 images). Not validated on farm cameras.",
            "Requires macro focus and balanced ambient lighting; night flash degrades accuracy.",
            f"Evaluated on {result.get('split', {}).get('test', 0)} held-out test images."
        ]
    else:
        status = "TEST_ONLY"
        test_metrics = result.get("metrics", {})
        val_metrics = {}
        classes_trained = 4
        limitations = [
            "Trained on synthetic test fixture for CI validation.",
            "Not validated for commercial field deployment until real PlantDoc images are trained."
        ]

    # Compute model checksum
    checksum = DatasetValidator.compute_sha256(OUTPUT_MODEL) if os.path.exists(OUTPUT_MODEL) else "NONE"

    # Copy artifact to models directory
    dest_artifact = os.path.join(MODELS_DIR, "vision_ensemble.joblib")
    if os.path.exists(OUTPUT_MODEL):
        with open(OUTPUT_MODEL, "rb") as fsrc, open(dest_artifact, "wb") as fdst:
            fdst.write(fsrc.read())

    # Determine classes from model or fallback
    if os.path.exists(OUTPUT_MODEL):
        try:
            pkg = joblib.load(OUTPUT_MODEL)
            classes = pkg.get("classes", [])
        except Exception:
            classes = []
    if not classes:
        classes = ["Healthy Foliage", "Water Stress Induced Chlorosis", "Tomato Early Blight Fungal Spot", "Downy Mildew Fungal Infection"]

    # ===== ARTIFACT 1: metadata.json =====
    metadata = {
        "model_name": "AgriSaathi Foliar Disease & Nutrient Vision Classifier",
        "version": "3.0.0-PlantDoc" if is_real else "2.5.0-TestFixture",
        "architecture": "CalibratedVotingClassifier(RandomForest + GradientBoosting)",
        "dataset_name": "PlantDoc GitHub Dataset" if is_real else "Synthetic Test Fixture",
        "dataset_size": result.get("total_images_ingested", 0) if is_real else 20,
        "artifact_path": "mlbackend/vision_model.joblib",
        "artifact_checksum": checksum,
        "classes_count": len(classes),
        "classes": classes,
        "features": ["greenness", "yellowing", "browning", "texture"],
        "training_date": datetime.now(timezone.utc).isoformat(),
        "model_status": status,
        "field_validation_required": True,
        "is_test_fixture": is_fixture,
        "known_limitations": limitations,
        "split_info": result.get("split", {}),
        "leakage_check": result.get("leakage_check", "NOT_CHECKED"),
        "training_time_seconds": result.get("training_time_seconds", 0)
    }
    with open(os.path.join(MODELS_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # ===== ARTIFACT 2: metrics.json =====
    eval_source = test_metrics if is_real else test_metrics
    metrics = {
        "test_accuracy": eval_source.get("overall_accuracy", 0.0),
        "test_macro_f1": eval_source.get("macro_f1", 0.0),
        "test_weighted_f1": eval_source.get("weighted_f1", 0.0),
        "test_per_class": eval_source.get("per_class_metrics", {}),
        "test_confusion_matrix": eval_source.get("confusion_matrix", []),
        "validation_accuracy": val_metrics.get("overall_accuracy", 0.0) if val_metrics else None,
        "validation_macro_f1": val_metrics.get("macro_f1", 0.0) if val_metrics else None,
        "evaluation_source": "Held-out PlantDoc test split (15%)" if is_real else "Synthetic test fixture"
    }
    with open(os.path.join(MODELS_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # ===== ARTIFACT 3: training_config.json =====
    config = {
        "algorithm": "CalibratedVotingClassifier",
        "estimators": ["RandomForestClassifier(100)", "GradientBoostingClassifier(100)"],
        "voting": "soft",
        "cv_folds": 3 if is_real else 2,
        "split_strategy": "Disjoint Stratified Split (70/15/15)",
        "split_seed": 42,
        "leakage_prevention": "File-path disjoint verification",
        "feature_extraction": "RGB chromatic analysis (greenness, yellowing, browning, texture)",
        "preprocessing": "PIL resize to 160x160, normalize to [0,1]",
        "test_fixture_mode": is_fixture,
        "dataset_dir": PLANTDOC_DIR if is_real else "N/A"
    }
    with open(os.path.join(MODELS_DIR, "training_config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    # ===== ARTIFACT 4: evaluation_report.md =====
    test_acc = metrics["test_accuracy"]
    test_f1 = metrics["test_macro_f1"]
    test_wf1 = metrics["test_weighted_f1"]

    per_class_table = ""
    for cls, m in metrics.get("test_per_class", {}).items():
        per_class_table += f"| {cls} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1_score']:.3f} | {m['support']} |\n"

    report_md = f"""# Vision Model Evaluation Report

- **Model Status**: `{status}`
- **Field Validation Required**: `YES`
- **Model Checksum**: `{checksum}`
- **Dataset**: {"PlantDoc (~2,600 images)" if is_real else "Synthetic Test Fixture (20 samples)"}
- **Split**: {json.dumps(result.get("split", {}))}
- **Leakage Check**: {result.get("leakage_check", "N/A")}

## Test Set Metrics

| Metric | Value |
|--------|-------|
| Overall Accuracy | {test_acc} |
| Macro F1-Score | {test_f1} |
| Weighted F1-Score | {test_wf1} |

## Per-Class Breakdown

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|----|---------|
{per_class_table}

## Reproduction Command

```powershell
python -m mlbackend.training.train_vision
```

> [!WARNING]
> This model is currently in status `{status}`. It has NOT been certified on farm cameras under unconstrained sunlight.
"""
    with open(os.path.join(MODELS_DIR, "evaluation_report.md"), "w", encoding="utf-8") as f:
        f.write(report_md)

    # ===== ARTIFACT 5: README.md =====
    readme_md = f"""# Leaf Disease Vision Ensemble

- **Status**: `{status}`
- **Artifact**: `mlbackend/vision_model.joblib`
- **Dataset**: {"PlantDoc GitHub" if is_real else "Synthetic Test Fixture"}
- **Test Accuracy**: {test_acc}
- **Macro F1**: {test_f1}
- **Verification**: Run `python -m mlbackend.training.train_vision`
"""
    with open(os.path.join(MODELS_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_md)

    print(f"\n  Training complete. Status: {status}. Artifacts saved to: {MODELS_DIR}")
    if is_real:
        print(f"  Test Accuracy: {test_acc}")
        print(f"  Macro F1:      {test_f1}")
        print(f"  Classes:       {len(classes)}")
    print("=========================================================\n")

if __name__ == "__main__":
    main()
