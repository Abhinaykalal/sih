"""
AgriSaathi Vision Pipeline — Ensemble Training Engine
=====================================================
Trains a Calibrated Voting Classifier on extracted plant pathology features.
Saves model artifact, remedies, and reproducible evaluation report.
"""

import os
import joblib
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.calibration import CalibratedClassifierCV

try:
    from .evaluation import evaluate_model_performance
except ImportError:
    from evaluation import evaluate_model_performance

REMEDIES_LIBRARY = {
    "Healthy Foliage": "Crop foliage is healthy. Maintain scheduled surveillance and standard irrigation.",
    "Water Stress Induced Chlorosis": "Severe moisture deficit (<20%). Irrigate immediately; do NOT apply nitrogen fertilizer until turgor recovers.",
    "Tomato Early Blight Fungal Spot": "Foliar pathogen detected. Apply copper oxychloride (2.5g/L) or neem oil (5ml/L) at dusk.",
    "Downy Mildew Fungal Infection": "Spore germination under high humidity. Apply bio-fungicide (Trichoderma viride @ 5g/L) within 24h.",
    "Nitrogen Deficiency Chlorosis": "Uniform pale yellowing with normal moisture. Apply Urea @ 25 kg/acre or liquid foliar bio-fertilizer.",
    "Potassium Marginal Scorch Deficiency": "Marginal scorching detected. Apply Muriate of Potash (MOP) @ 20 kg/acre.",
    "Phosphorus Bronze-Purpling Deficiency": "Anthocyanin purpling detected. Apply Single Super Phosphate (SSP) near root zone.",
    "Insect Foliage Pest Damage": "Active pest feeding observed. Deploy sticky traps and spray Azadirachtin (1500 ppm neem extract)."
}

def train_vision_ensemble(
    X_train: np.ndarray,
    y_train: List[str],
    X_val: Optional[np.ndarray] = None,
    y_val: Optional[List[str]] = None,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """Trains a production-grade ensemble vision classifier.
    
    Architecture:
    - RandomForest (300 trees, sqrt features) — robust baseline
    - ExtraTrees (300 trees) — adds diversity via random splits  
    - HistGradientBoosting (200 iterations) — handles large datasets fast
    - Soft voting with calibration for honest probabilities
    """
    from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline

    classes = sorted(list(set(y_train)))
    n_samples = len(X_train)
    n_features = X_train.shape[1] if len(X_train.shape) > 1 else 1

    print(f"  Training on {n_samples} samples, {n_features} features, {len(classes)} classes")

    # Scale features for gradient boosting performance
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val) if X_val is not None else None

    # Build strong ensemble
    rf = RandomForestClassifier(
        n_estimators=300, max_features="sqrt", min_samples_leaf=2,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    et = ExtraTreesClassifier(
        n_estimators=300, max_features="sqrt", min_samples_leaf=2,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    hgb = HistGradientBoostingClassifier(
        max_iter=200, max_depth=8, learning_rate=0.1,
        min_samples_leaf=5, random_state=42
    )

    ensemble = VotingClassifier(
        estimators=[('rf', rf), ('et', et), ('hgb', hgb)],
        voting='soft', n_jobs=-1
    )

    # Calibration with cross-validation
    cv_folds = min(5, max(2, n_samples // (len(classes) * 3)))
    print(f"  Ensemble: RF(300) + ExtraTrees(300) + HistGBM(200), CV={cv_folds}")

    calibrated = CalibratedClassifierCV(estimator=ensemble, cv=cv_folds)
    calibrated.fit(X_train_scaled, y_train)

    eval_report = {}
    if X_val_scaled is not None and y_val is not None and len(y_val) > 0:
        y_pred = calibrated.predict(X_val_scaled)
        eval_report = evaluate_model_performance(y_val, list(y_pred), classes)

    package = {
        "model": calibrated,
        "scaler": scaler,
        "remedies": REMEDIES_LIBRARY,
        "classes": classes,
        "n_features": n_features,
        "version": "3.0.0-PlantDoc-PlantVillage",
        "is_test_fixture": n_samples < 100,
        "evaluation": eval_report
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        joblib.dump(package, output_path)

    return {
        "status": "TRAINED",
        "samples_trained": n_samples,
        "classes_count": len(classes),
        "n_features": n_features,
        "evaluation": eval_report,
        "is_test_fixture": n_samples < 100
    }
