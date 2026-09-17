# AgriSaathi Datasets

This directory maintains the training and validation datasets for AgriSaathi's machine learning models.

## Dataset Reproducibility

To prevent the Git repository from inflating with gigabytes of high-resolution images, we use a dataset generation pipeline. The directories (`raw`, `processed`, `external`, `vision/images`) are populated dynamically by our dataset generation scripts.

### Generating the Vision Dataset

To run the vision training pipeline (`mlbackend/train_vision_model.py`) locally or in CI, you must first bootstrap the synthetic image dataset:

```bash
python -m mlbackend.datasets.generate_vision_dataset
```

This will:
1. Create `datasets/vision/images/` and populate it with synthetic representations for each supported crop disease class (e.g. `datasets/vision/images/rice__blast/`).
2. Generate `datasets/vision/vision_manifest.csv` which enforces leakage protection during cross-validation via `group_id`.

Once populated, the end-to-end training pipeline is fully reproducible natively from this checkout.

## Structure
- `manifests/`: Defines metadata and sources for real-world benchmark datasets.
- `vision/`: Contains the generated computer vision datasets.
- `raw/`: Placeholder for ingested tabular data.
- `processed/`: Placeholder for featurized datasets.
