"""Safe vision inference boundary for AgriSaathi.

The API must never turn an arbitrary image into a disease diagnosis.  A prediction is
only possible when a real, compatible vision artifact is deployed and the uploaded
image passes the conservative leaf-image gate.

The supported artifact is produced by ``train_vision_model.py`` and uses HOG + colour
features from the actual image.  The previous synthetic four/six-number feature model
is deliberately rejected.
"""

import io
import os
from typing import Any, Dict, Optional

import joblib
import numpy as np
from PIL import Image, ImageOps
from skimage.feature import hog

MODEL_PATH = os.path.join(os.path.dirname(__file__), "vision_model.joblib")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MIN_IMAGE_SIDE = 160
MODEL_STATUS = "EXPERIMENTAL"
ARTIFACT_TYPE = "agrisaathi_vision_hog_svm_v1"


def _largest_component_fraction(mask: np.ndarray) -> float:
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    largest = 0
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or visited[y, x]:
                continue
            stack = [(y, x)]
            visited[y, x] = True
            size = 0
            while stack:
                cy, cx = stack.pop()
                size += 1
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            stack.append((ny, nx))
            largest = max(largest, size)
    return largest / float(h * w)


def validate_leaf_image(image_bytes: bytes) -> Dict[str, Any]:
    """Conservative scope/quality gate; this is not a disease classifier."""
    if not image_bytes:
        return {"valid": False, "status": "INVALID_IMAGE", "reason": "No image bytes were supplied."}
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return {"valid": False, "status": "IMAGE_TOO_LARGE", "reason": "Image exceeds the 5 MB limit."}

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img).convert("RGB")
        width, height = img.size
        if min(width, height) < MIN_IMAGE_SIDE:
            return {
                "valid": False,
                "status": "LOW_QUALITY_IMAGE",
                "reason": f"Image is too small ({width}x{height}); use a clear leaf photo.",
            }

        arr = np.asarray(img.resize((128, 128)), dtype=np.float32) / 255.0
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        maxc = arr.max(axis=2)
        minc = arr.min(axis=2)
        saturation = np.divide(maxc - minc, np.maximum(maxc, 1e-6))

        # Accept common green/yellow/brown foliage.  Do not claim this is a trained
        # leaf detector; it is only a fail-closed precondition for the classifier.
        green = (g > r * 1.03) & (g > b * 1.03) & (g > 0.16)
        yellow = (r > 0.35) & (g > 0.35) & (b < 0.45) & (np.abs(r - g) < 0.28)
        brown = (r > b * 1.12) & (g > b * 0.90) & (r < 0.78) & (g < 0.68) & (r > 0.12)
        plant_mask = (green | yellow | brown) & (saturation > 0.12)

        plant_ratio = float(np.mean(plant_mask))
        largest_component = _largest_component_fraction(plant_mask)
        gray = 0.299 * r + 0.587 * g + 0.114 * b
        gx = np.abs(np.diff(gray, axis=1))
        gy = np.abs(np.diff(gray, axis=0))
        edge_density = float(np.mean(np.concatenate([gx.ravel(), gy.ravel()]) > 0.20))
        neutral_ratio = float(np.mean(saturation < 0.10))

        quality = {
            "plant_ratio": round(plant_ratio, 4),
            "largest_component_ratio": round(largest_component, 4),
            "edge_density": round(edge_density, 4),
            "neutral_ratio": round(neutral_ratio, 4),
        }

        if plant_ratio < 0.12 or largest_component < 0.06:
            return {
                "valid": False,
                "status": "NOT_A_LEAF",
                "reason": "The image does not contain a sufficiently large contiguous leaf-like region.",
                "quality": quality,
            }

        return {"valid": True, "status": "LEAF_IMAGE_ACCEPTED", "quality": quality}
    except Exception as exc:
        return {"valid": False, "status": "INVALID_IMAGE", "reason": f"Image could not be decoded: {exc}"}


def extract_vision_features(image_bytes: bytes) -> np.ndarray:
    """Extract the exact HOG + RGB histogram vector used by the training script."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = ImageOps.exif_transpose(img).resize((128, 128))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    gray = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    hog_features = hog(
        gray,
        orientations=9,
        pixels_per_cell=(8, 8),
        cells_per_block=(2, 2),
        block_norm="L2-Hys",
        feature_vector=True,
    ).astype(np.float32)
    hist_features = []
    for channel in range(3):
        hist, _ = np.histogram(arr[..., channel], bins=16, range=(0.0, 1.0), density=True)
        hist_features.extend((hist / max(float(hist.sum()), 1.0)).astype(np.float32))
    return np.concatenate([hog_features, np.asarray(hist_features, dtype=np.float32)])


def _unavailable(action: str, status: str = "MODEL_UNAVAILABLE", **extra: Any) -> Dict[str, Any]:
    return {
        "status": status,
        "provenance": "UNAVAILABLE",
        "diagnosis": None,
        "confidence_pct": None,
        "action": action,
        **extra,
    }


class LocalVisionAIModel:
    def __init__(self) -> None:
        self.model_data: Optional[Dict[str, Any]] = None
        self.load_model()

    def load_model(self) -> None:
        """Load only the real-image artifact format; never create/train a fallback."""
        if not os.path.exists(MODEL_PATH):
            print("[VISION] No vision_model.joblib found; vision inference is UNAVAILABLE.")
            return
        try:
            data = joblib.load(MODEL_PATH)
            if not isinstance(data, dict) or data.get("artifact_type") != ARTIFACT_TYPE:
                raise ValueError("Vision artifact is not the approved real-image HOG/SVM format.")
            if "model" not in data or "classes" not in data or "feature_config" not in data:
                raise ValueError("Vision artifact is missing model/classes/feature_config.")
            self.model_data = data
            print("[VISION] Real-image vision artifact loaded; status=EXPERIMENTAL.")
        except Exception as exc:
            self.model_data = None
            print(f"[VISION] Artifact rejected: {exc}")

    def diagnose(
        self,
        soil_moisture: Optional[float] = None,
        humidity: Optional[float] = None,
        image_bytes: Optional[bytes] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        # Sensor values are intentionally ignored: disease vision must be based on the
        # uploaded image. This prevents fake/default NPK/moisture values from becoming
        # part of the visual diagnosis.
        if image_bytes is None:
            return _unavailable("Upload a clear close-up photo of a crop leaf.", "INVALID_IMAGE")

        validation = validate_leaf_image(image_bytes)
        if not validation["valid"]:
            return _unavailable(
                "Upload a clear close-up photo containing a single crop leaf.",
                validation["status"],
                reason=validation.get("reason"),
                quality=validation.get("quality"),
            )

        if self.model_data is None:
            return _unavailable(
                "The leaf vision model is not deployed. No diagnosis was made.",
                "MODEL_UNAVAILABLE",
                model_name="AgriSaathi Leaf Disease Vision",
                model_version=None,
                quality=validation.get("quality"),
            )

        try:
            feature_config = self.model_data["feature_config"]
            expected_length = int(feature_config["feature_length"])
            x = extract_vision_features(image_bytes).reshape(1, -1)
            if x.shape[1] != expected_length:
                raise ValueError(f"Feature length mismatch: expected {expected_length}, got {x.shape[1]}")

            model = self.model_data["model"]
            probabilities = model.predict_proba(x)[0]
            idx = int(np.argmax(probabilities))
            prediction = str(model.classes_[idx])
            confidence = float(probabilities[idx])
            threshold = float(self.model_data.get("minimum_confidence_pct", 70.0)) / 100.0

            if confidence < threshold:
                return {
                    "status": "NO_RELIABLE_RESULT",
                    "provenance": "EXPERIMENTAL",
                    "diagnosis": None,
                    "confidence_pct": round(confidence * 100, 1),
                    "action": "The model is not confident enough to provide a disease diagnosis. Retake the photo with the leaf filling the frame.",
                    "model_name": self.model_data.get("model_name", "AgriSaathi Leaf Disease Vision"),
                    "model_version": self.model_data.get("version"),
                    "quality": validation.get("quality"),
                }

            remedies = self.model_data.get("remedies", {})
            return {
                "status": "EXPERIMENTAL_PREDICTION",
                "provenance": "EXPERIMENTAL",
                "diagnosis": prediction,
                "confidence_pct": round(confidence * 100, 1),
                "action": remedies.get(prediction, "Consult a qualified agronomist before treatment."),
                "model_name": self.model_data.get("model_name", "AgriSaathi Leaf Disease Vision"),
                "model_version": self.model_data.get("version"),
                "quality": validation.get("quality"),
                "warning": "Experimental model; field validation is required before relying on this result.",
            }
        except Exception as exc:
            return _unavailable(
                "The deployed vision artifact is incompatible with the inference pipeline. No diagnosis was made.",
                "MODEL_INCOMPATIBLE",
                error=str(exc),
                quality=validation.get("quality"),
            )


local_vision_ai = LocalVisionAIModel()
