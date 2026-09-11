"""
AgriSaathi Vision Pipeline — Test-Only Fixture Dataset & Model Generator
========================================================================
Creates a reproducible test fixture for CI/CD and automated test validation.
Clearly marks the trained artifact as: TEST_ONLY (never claimed as production).
"""

import os
import numpy as np
from typing import Dict, Any

try:
    from .training import train_vision_ensemble
except ImportError:
    from training import train_vision_ensemble

def generate_and_train_test_fixture(output_path: str) -> Dict[str, Any]:
    """Generates synthetic test fixture samples and trains a clearly-marked test artifact."""
    
    # 30 controlled test vectors: [Greenness, Yellowing, Browning, Texture, Soil Moisture, Air Humidity]
    X_fixture = np.array([
        # Healthy
        [0.85, 0.05, 0.02, 0.10, 45.0, 60.0],
        [0.82, 0.08, 0.04, 0.12, 42.0, 58.0],
        [0.88, 0.04, 0.02, 0.08, 48.0, 65.0],
        [0.80, 0.10, 0.03, 0.15, 40.0, 55.0],
        # Water Stress
        [0.22, 0.68, 0.10, 0.40, 14.0, 45.0],
        [0.25, 0.62, 0.12, 0.42, 17.0, 50.0],
        [0.20, 0.70, 0.08, 0.38, 12.0, 40.0],
        [0.28, 0.58, 0.14, 0.35, 18.0, 48.0],
        # Early Blight
        [0.18, 0.22, 0.60, 0.82, 35.0, 92.0],
        [0.15, 0.20, 0.65, 0.85, 38.0, 90.0],
        [0.20, 0.25, 0.55, 0.78, 32.0, 88.0],
        [0.16, 0.24, 0.62, 0.80, 36.0, 94.0],
        # Downy Mildew
        [0.12, 0.25, 0.68, 0.88, 40.0, 95.0],
        [0.10, 0.28, 0.65, 0.90, 42.0, 94.0],
        [0.14, 0.22, 0.70, 0.85, 38.0, 92.0],
        # Nitrogen Deficiency
        [0.32, 0.58, 0.08, 0.30, 32.0, 62.0],
        [0.35, 0.55, 0.06, 0.28, 35.0, 65.0],
        [0.30, 0.60, 0.09, 0.32, 30.0, 60.0]
    ])

    y_fixture = [
        "Healthy Foliage", "Healthy Foliage", "Healthy Foliage", "Healthy Foliage",
        "Water Stress Induced Chlorosis", "Water Stress Induced Chlorosis", "Water Stress Induced Chlorosis", "Water Stress Induced Chlorosis",
        "Tomato Early Blight Fungal Spot", "Tomato Early Blight Fungal Spot", "Tomato Early Blight Fungal Spot", "Tomato Early Blight Fungal Spot",
        "Downy Mildew Fungal Infection", "Downy Mildew Fungal Infection", "Downy Mildew Fungal Infection",
        "Nitrogen Deficiency Chlorosis", "Nitrogen Deficiency Chlorosis", "Nitrogen Deficiency Chlorosis"
    ]

    return train_vision_ensemble(
        X_train=X_fixture,
        y_train=y_fixture,
        X_val=X_fixture[:4],
        y_val=y_fixture[:4],
        output_path=output_path
    )
