# Vision Model Setup Guide

## Overview

The AgriSaathi leaf disease detection system requires a trained `vision_model.joblib` file to function. This guide explains how to train and deploy it.

## What the Vision Model Does

- Detects leaf diseases from crop images using HOG (Histogram of Oriented Gradients) + SVM
- Supports: Pepper Bell, Potato, Tomato diseases (10 classes)
- Returns: Disease diagnosis + confidence + recommended remedy
- Status: EXPERIMENTAL (not field-validated)
- Minimum confidence threshold: 70%

## Quick Start (5 minutes)

### Step 1: Ensure Dataset Exists

The PlantVillage dataset should already be in your repository:

```
datasets/PlantVillage/
├── Pepper__bell___Bacterial_spot/
├── Pepper__bell___healthy/
├── Potato___Early_blight/
├── Potato___Late_blight/
├── Potato___healthy/
├── Tomato_Bacterial_spot/
├── Tomato_Early_blight/
├── Tomato_Late_blight/
├── Tomato_Leaf_Mold/
└── Tomato_Septoria_leaf_spot/
```

**Check if dataset exists**:
```bash
ls -la datasets/PlantVillage/
```

If directories are empty or missing, download from: https://www.kaggle.com/datasets/arjuntejaswi/plant-village

### Step 2: Train the Model

```bash
# Navigate to mlbackend directory
cd mlbackend

# Run training script
python train_vision_model.py

# Optional: specify custom dataset location
python train_vision_model.py --data-dir ../datasets/PlantVillage --max-per-class 300
```

**What happens**:
1. Scans PlantVillage dataset for images
2. Extracts HOG (Histogram of Oriented Gradients) features from each image
3. Trains LinearSVC classifier with Platt calibration
4. Splits data: 80% train, 20% test (with 75/25 train/validation split)
5. Saves `vision_model.joblib` (the trained model)
6. Saves `vision_model.metrics.json` (accuracy/F1 scores)
7. Saves `vision_model_metadata.json` (model metadata + signature)

### Step 3: Verify Model Created

```bash
ls -lh mlbackend/vision_model.joblib
# Should show a file ~50-100 MB

# Check metrics
cat mlbackend/vision_model.metrics.json
```

Expected output:
```json
{
  "validation": {
    "accuracy": 0.85,
    "balanced_accuracy": 0.82,
    "macro_f1": 0.81,
    ...
  },
  "test": {
    "accuracy": 0.87,
    "balanced_accuracy": 0.84,
    "macro_f1": 0.83,
    ...
  }
}
```

### Step 4: Deploy

The backend will automatically load `vision_model.joblib` on startup:

```bash
cd mlbackend
python -m uvicorn main:app --reload
```

**Check status**:
```bash
curl http://localhost:8000/api/model-registry
# Should show "EXPERIMENTAL" for vision model instead of "UNAVAILABLE"
```

---

## Training Script Details

### Input

**File**: `mlbackend/train_vision_model.py`

**Expected Dataset Structure**:
```
datasets/PlantVillage/
├── class_name_1/
│   ├── image1.jpg
│   ├── image2.jpg
│   └── ...
├── class_name_2/
│   ├── image1.jpg
│   └── ...
└── ...
```

**Supported Image Formats**: JPG, PNG, JPEG, WEBP, BMP

### Hyperparameters

**Modifiable in `train_vision_model.py`**:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `--max-per-class` | 300 | Limit images per class (balances training time; 0 = unlimited) |
| `--data-dir` | auto-detect | Path to dataset root |
| `--manifest` | vision_manifest.csv | CSV with path, label, group_id (for stronger leakage control) |
| `--output` | vision_model.joblib | Output model filename |

**Fixed in code**:
- Image size: 128×128 pixels
- HOG orientations: 9
- Classifier: LinearSVC with class balancing
- Calibration: Platt scaling (sigmoid)
- CV splits: 3-fold on training set
- Random seed: 42 (for reproducibility)

### Output Files

**1. `vision_model.joblib`** (50-100 MB)
- Trained CalibratedClassifierCV model
- Feature extraction config
- Class labels
- Remedies mapping
- Minimum confidence threshold
- Training metadata

**2. `vision_model.metrics.json`**
- Validation metrics (accuracy, F1, precision, recall)
- Test metrics (on held-out 20%)
- Used to verify model quality

**3. `vision_model_metadata.json`**
- Model hash (SHA256)
- Dataset manifest hash
- Training date
- Algorithm details
- Class labels
- Signature (for integrity verification)

---

## Runtime: How Vision Model is Used

### 1. Backend Loads Model

**File**: `mlbackend/vision_ai_model.py`

On startup:
```python
artifact = joblib.load("vision_model.joblib")
model = artifact["model"]  # CalibratedClassifierCV
classes = artifact["classes"]  # List of disease names
min_confidence = artifact["minimum_confidence_pct"]  # 70.0
remedies = artifact["remedies"]  # Disease → treatment mapping
```

### 2. Frontend Sends Image

```javascript
// src/components/VisionDiagnosticModule.tsx
const formData = new FormData();
formData.append('image', imageFile);
const response = await fetch('/api/vision/diagnose', { 
  method: 'POST', 
  body: formData 
});
```

### 3. Backend Processes Image

**Endpoint**: `POST /api/vision/diagnose`

**Steps**:
1. **Image Validation**
   - Check size (minimum 160×160 pixels)
   - Check format (JPG, PNG, etc.)
   - Check content (not blank, not pure color)

2. **Feature Extraction** (identical to training)
   - Resize to 128×128
   - Extract HOG features
   - Extract RGB histogram
   - Concatenate features

3. **Model Inference**
   - `model.predict_proba(features)` → probabilities per class
   - Get max probability (confidence)

4. **Confidence Check**
   - If confidence < 70%: Return `NO_RELIABLE_RESULT` + actual confidence
   - If confidence ≥ 70%: Return diagnosis + confidence + remedy

5. **Response**
```json
{
  "diagnosis": "Tomato_Early_blight",
  "confidence_pct": 87.5,
  "severity": "MODERATE",
  "remedy": "Apply preventive copper or Mancozeb spray; prune lower yellowing foliage...",
  "provenance": "EXPERIMENTAL",
  "status": "EXPERIMENTAL_PREDICTION"
}
```

---

## Troubleshooting

### Issue 1: "No real images found in datasets/PlantVillage"

**Cause**: Dataset directory is empty or images are not in expected subdirectories

**Solution**:
```bash
# Check dataset exists
ls -R datasets/PlantVillage/ | head -20

# If empty, download from Kaggle
# https://www.kaggle.com/datasets/arjuntejaswi/plant-village

# Or specify custom path
python train_vision_model.py --data-dir /path/to/dataset
```

### Issue 2: "NameError: name 'Field' is not defined" (FIXED)

This was a bug in main.py. Already fixed in commit `d3c09b7`.

### Issue 3: "ModuleNotFoundError: No module named 'mlbackend.notification_engine'" (FIXED)

This was a missing module. Already stubbed in commit `54e6b97`.

### Issue 4: "[VISION] No real vision_model.joblib found; vision inference is UNAVAILABLE"

**This is EXPECTED** if you haven't trained the model yet.

**Solution**: Train the model (see Quick Start above)

### Issue 5: Training is very slow

**Cause**: Too many images per class (default 300)

**Solution**:
```bash
# Reduce images per class
python train_vision_model.py --max-per-class 100

# Or limit to subset
python train_vision_model.py --max-per-class 50
```

Training time: ~5-15 minutes on modern CPU (varies by image count)

### Issue 6: "train split is missing classes"

**Cause**: Dataset doesn't have enough images of all disease types

**Solution**:
- Ensure all disease class folders have images
- Use `--max-per-class 0` to use all available images
- Or download complete PlantVillage dataset

---

## Deployment Checklist

- [ ] PlantVillage dataset downloaded to `datasets/PlantVillage/`
- [ ] All 10 class directories have images
- [ ] Run `python train_vision_model.py` and training completes successfully
- [ ] `mlbackend/vision_model.joblib` file exists (50-100 MB)
- [ ] `mlbackend/vision_model.metrics.json` shows macro_f1 > 0.70
- [ ] Backend starts without "[VISION]" error message
- [ ] POST to `/api/vision/diagnose` with test image returns diagnosis

---

## Production Notes

**Current Status**: EXPERIMENTAL
- Model is NOT field-validated
- Training accuracy: ~85-90% (varies by dataset)
- Real-world accuracy: UNKNOWN (needs field testing)
- Minimum confidence threshold: 70% (prevents unreliable predictions)

**Before Production Use**:
1. Field validation on 50+ real farm images
2. Compare predictions against agronomist assessment
3. Retrain with field-collected data
4. Increase minimum confidence threshold if needed
5. Document performance on specific crop varieties

**Future Improvements** (Phase 4):
- Collect field images + ground truth labels
- Retrain with local crop varieties
- Increase dataset to 1000+ images per class
- Switch to deep learning (ResNet, EfficientNet)
- Deploy on-device (ONNX, TensorFlow Lite)

---

## Architecture

```
PlantVillage Dataset (Real Images)
         ↓
   Feature Extraction
   (HOG + RGB Histogram)
         ↓
   LinearSVC + Platt Calibration
   (sklearn.svm)
         ↓
   vision_model.joblib
   (50-100 MB serialized model)
         ↓
   Backend loads on startup
   (mlbackend/vision_ai_model.py)
         ↓
   Farmer uploads leaf image
   (POST /api/vision/diagnose)
         ↓
   Extract features (identical to training)
         ↓
   model.predict_proba(features)
   → confidence = max(probabilities)
         ↓
   If confidence >= 70%:
     → Return diagnosis + remedy
   Else:
     → Return NO_RELIABLE_RESULT
         ↓
   Frontend displays result
   (src/components/VisionDiagnosticModule.tsx)
```

---

## FAQ

**Q: Why 70% confidence threshold?**
A: Prevents unreliable predictions from being acted upon. Below 70%, disease identification is too uncertain for agricultural decision-making.

**Q: Can I use my own dataset?**
A: Yes! Organize images into folders by disease class and run:
```bash
python train_vision_model.py --data-dir /path/to/your/dataset
```

**Q: How long does training take?**
A: 5-15 minutes on modern CPU (2-4 core). Varies with:
- Number of images
- Image resolution
- Hardware speed

**Q: Can I train on GPU?**
A: Not by default. To enable GPU:
1. Install scikit-learn-gpu or use TensorFlow/PyTorch instead
2. Modify `train_vision_model.py` to use GPU backend
3. (Phase 4 improvement)

**Q: What if predictions are inaccurate?**
A: Possible causes:
- Image quality poor (blurry, wrong lighting)
- Disease not in training dataset
- Model needs field validation
- Need to retrain with local crop varieties

**Q: Is the model production-ready?**
A: Not yet. Status is EXPERIMENTAL because:
- Not field-validated against real outcomes
- Training dataset is generic (PlantVillage)
- Local crop varieties may perform differently
- Requires Phase 3.1 remediation + Phase 4 field testing

---

## Next Steps

1. **Immediate**: Train model (5-15 minutes)
   ```bash
   cd mlbackend
   python train_vision_model.py
   ```

2. **Test**: Send sample image to backend
   ```bash
   curl -X POST -F "image=@test_image.jpg" http://localhost:8000/api/vision/diagnose
   ```

3. **Monitor**: Check confidence scores and accuracy metrics
   ```bash
   cat mlbackend/vision_model.metrics.json
   ```

4. **Document**: Add vision model to deployment checklist
5. **Field Test**: Gather 50+ real farm images for validation (Phase 4)

---

**Document Created**: 2026-09-18
**Status**: Ready for Training & Deployment
