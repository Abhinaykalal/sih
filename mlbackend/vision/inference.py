"""Canonical vision inference with strict input/model validation.

This module intentionally NEVER fabricates a diagnosis when the image, model,
or model/input feature contract is unavailable or invalid.
"""

import io
import os
from typing import Any, Dict, Optional

import joblib
import numpy as np
from PIL import Image, ImageStat
from pydantic import BaseModel, Field

from .preprocessing import extract_features_from_image_bytes, get_feature_names

MODEL_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "vision_model.joblib"
)
EXPECTED_FEATURE_COUNT = len(get_feature_names())


class VisionPredictionOutput(BaseModel):
    status: str
    prediction: Optional[str] = None
    confidence: Optional[float] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    model_status: str = "UNAVAILABLE"
    provenance: str = "UNAVAILABLE"
    warning: Optional[str] = None
    evidence: list[str] = Field(default_factory=list)
    remedy: Optional[str] = None


def _reject(reason: str, warning: Optional[str] = None) -> Dict[str, Any]:
    return {
        "status": "NO_RELIABLE_RESULT",
        "prediction": None,
        "confidence": None,
        "model_name": None,
        "model_version": None,
        "model_status": "UNAVAILABLE",
        "provenance": "UNAVAILABLE",
        "warning": warning or reason,
        "evidence": [reason],
        "remedy": "Upload a clear, close-up photograph of a single crop leaf showing the affected area.",
    }


def _validate_image(image_bytes: bytes) -> tuple[Optional[Image.Image], Optional[Dict[str, Any]]]:
    if not image_bytes:
        return None, _reject("No image bytes were received.")
    if len(image_bytes) > 12 * 1024 * 1024:
        return None, _reject("Image exceeds the 12 MB analysis limit.")

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.load()
    except Exception:
        return None, _reject("The uploaded file is not a readable image.")

    width, height = img.size
    if width < 128 or height < 128:
        return None, _reject(
            f"Image resolution is too small ({width}x{height}); minimum is 128x128."
        )

    stat = ImageStat.Stat(img)
    channel_std = float(np.mean(stat.stddev))
    if channel_std < 3.0:
        return None, _reject("Image has insufficient visual variation and cannot be analyzed reliably.")

    return img, None


def _crop_likeness_gate(extracted: Dict[str, Any]) -> tuple[bool, str]:
    """Conservative pre-classification gate.

    This is a safety gate, not a claim of crop detection. A real leaf detector/OOD
    model should replace or augment it after a field-labelled dataset is available.
    """
    green = float(extracted.get("greenness", 0.0))
    yellow = float(extracted.get("yellowing", 0.0))
    brown = float(extracted.get("browning", 0.0))
    purple = float(extracted.get("feature_vector", [0] * EXPECTED_FEATURE_COUNT)[-1]) if extracted.get("feature_vector") else 0.0

    foliage_signal = green + yellow + brown + purple
    if foliage_signal < 0.06:
        return False, "The image does not contain enough foliage-like color signal for reliable leaf analysis."
    return True, "Foliage-like visual signal detected; disease classifier may be evaluated."


def _model_input_count(model: Any) -> Optional[int]:
    """Best-effort inspection of the persisted estimator's expected feature count."""
    for attr in ("n_features_in_",):
        value = getattr(model, attr, None)
        if value is not None:
            return int(value)

    # CalibratedClassifierCV stores fitted estimators in calibrated_classifiers_.
    calibrated = getattr(model, "calibrated_classifiers_", None)
    if calibrated:
        for fitted in calibrated:
            estimator = getattr(fitted, "estimator", None)
            value = getattr(estimator, "n_features_in_", None)
            if value is not None:
                return int(value)
    return None


def run_vision_inference(
    image_bytes: Optional[bytes] = None,
    features_dict: Optional[Dict[str, float]] = None,
    soil_moisture: Optional[float] = None,
    humidity: Optional[float] = None,
    model_path: str = MODEL_DEFAULT_PATH,
) -> Dict[str, Any]:
    """Run only a real persisted vision model with the exact training feature contract.

    Legacy six-feature/synthetic artifacts are rejected rather than silently used.
    No exception path is allowed to become a fabricated diagnosis.
    """
    if image_bytes is None and features_dict is None:
        return _reject("No image was supplied to the vision inference endpoint.")

    if image_bytes is not None:
        _, image_error = _validate_image(image_bytes)
        if image_error:
            return image_error
        extracted = extract_features_from_image_bytes(image_bytes)
    else:
        extracted = features_dict or {}

    feature_vector = extracted.get("feature_vector") if extracted else None
    if not isinstance(feature_vector, list) or len(feature_vector) != EXPECTED_FEATURE_COUNT:
        return _reject(
            f"Vision feature contract is invalid: expected {EXPECTED_FEATURE_COUNT} features."
        )

    if image_bytes is not None:
        foliage_ok, foliage_reason = _crop_likeness_gate(extracted)
        if not foliage_ok:
            return _reject(foliage_reason)
    else:
        foliage_reason = "Features supplied by an internal caller; image validation was not required."

    if not os.path.isfile(model_path):
        return _reject(
            "No verified vision model artifact is installed. Synthetic/test fixtures are not valid for user diagnosis."
        )

    try:
        package = joblib.load(model_path)
    except Exception as exc:
        return _reject(f"Vision model artifact could not be loaded: {exc}")

    if not isinstance(package, dict) or package.get("is_test_fixture", False):
        return _reject(
            "The installed vision artifact is marked TEST_ONLY and cannot be used for diagnosis."
        )

    model = package.get("model")
    if model is None:
        return _reject("Vision model artifact contains no classifier.")

    expected = package.get("n_features", EXPECTED_FEATURE_COUNT)
    if int(expected) != EXPECTED_FEATURE_COUNT:
        return _reject(
            f"Installed model expects {expected} features, but the canonical pipeline produces {EXPECTED_FEATURE_COUNT}."
        )

    model_input_count = _model_input_count(model)
    if model_input_count is not None and model_input_count != EXPECTED_FEATURE_COUNT:
        return _reject(
            f"Installed model expects {model_input_count} input features; canonical preprocessing produces {EXPECTED_FEATURE_COUNT}."
        )

    X = np.asarray([feature_vector], dtype=np.float32)

    try:
        prediction = str(model.predict(X)[0])
        probabilities = model.predict_proba(X)[0]
    except Exception as exc:
        return _reject(f"Vision inference failed without a reliable result: {exc}")

    confidence = float(np.max(probabilities))
    classes = list(getattr(model, "classes_", package.get("classes", [])))

    # Probability is model output, not a guarantee of real-world correctness.
    if confidence < 0.70:
        return {
            "status": "LOW_CONFIDENCE",
            "prediction": None,
            "confidence": round(confidence, 4),
            "model_name": "Leaf Pathology Vision Ensemble",
            "model_version": package.get("version", "unknown"),
            "model_status": "EXPERIMENTAL",
            "provenance": "MODEL_PREDICTION",
            "warning": "The model confidence is below the safe reporting threshold. No disease diagnosis is reported.",
            "evidence": [foliage_reason],
            "remedy": "Retake a clear close-up leaf photograph or have the crop inspected by an agronomist.",
        }

    alternatives = []
    if classes and len(classes) == len(probabilities):
        for idx in np.argsort(probabilities)[::-1][1:4]:
            alternatives.append({
                "prediction": str(classes[idx]),
                "probability": round(float(probabilities[idx]), 4),
            })

    remedies = package.get("remedies", {})
    return {
        "status": "PREDICTION_AVAILABLE",
        "prediction": prediction,
        "confidence": round(confidence, 4),
        "model_name": "Leaf Pathology Vision Ensemble",
        "model_version": package.get("version", "unknown"),
        "model_status": "EXPERIMENTAL",
        "provenance": "MODEL_PREDICTION",
        "warning": "Experimental model output; probability is not a guarantee of field-level diagnostic accuracy.",
        "evidence": [foliage_reason],
        "alternative_diagnoses": alternatives,
        "remedy": remedies.get(prediction),
    }
