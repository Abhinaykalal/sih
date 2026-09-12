"""Safe vision inference boundary for AgriSaathi.

This module intentionally does NOT train a model at API startup and never fabricates a
prediction when the real vision artifact is missing, incompatible, or the image is not
suitable for leaf analysis.
"""

import io
import os
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
from PIL import Image, ImageOps

MODEL_PATH = os.path.join(os.path.dirname(__file__), "vision_model.joblib")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MIN_IMAGE_SIDE = 128
MODEL_STATUS = "EXPERIMENTAL"


def _largest_component_fraction(mask: np.ndarray) -> float:
    """Return largest 8-connected component as a fraction of image pixels."""
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
    """Validate that an uploaded image is plausibly a usable crop-leaf photo.

    This is a conservative computer-vision gate, not a disease classifier. It exists so
    an arbitrary screenshot/object cannot be forced through a disease classifier.
    """
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
                "reason": f"Image is too small ({width}x{height}); use a clearer leaf photo.",
            }

        # Work at a small deterministic resolution for the gate.
        arr = np.asarray(img.resize((96, 96)), dtype=np.float32) / 255.0
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        maxc = arr.max(axis=2)
        minc = arr.min(axis=2)
        saturation = np.divide(maxc - minc, np.maximum(maxc, 1e-6))

        # Broad plant-like chromatic mask. This intentionally accepts green, yellow,
        # and brown foliage rather than requiring green leaves only.
        green = (g > r * 1.03) & (g > b * 1.03) & (g > 0.16)
        yellow = (r > 0.35) & (g > 0.35) & (b < 0.45) & (np.abs(r - g) < 0.28)
        brown = (r > b * 1.12) & (g > b * 0.90) & (r < 0.78) & (g < 0.68) & (r > 0.12)
        plant_mask = (green | yellow | brown) & (saturation > 0.12)

        plant_ratio = float(np.mean(plant_mask))
        largest_component = _largest_component_fraction(plant_mask)

        # A screenshot/display commonly has lots of neutral pixels and thin text/edge
        # structure but no substantial contiguous plant-colored region.
        gray = 0.299 * r + 0.587 * g + 0.114 * b
        gx = np.abs(np.diff(gray, axis=1))
        gy = np.abs(np.diff(gray, axis=0))
        edge_density = float(np.mean(np.concatenate([gx.ravel(), gy.ravel()]) > 0.20))
        neutral_ratio = float(np.mean(saturation < 0.10))

        # Conservative gate: require a meaningful plant-colored region and a connected
        # region large enough to plausibly be a leaf. Thresholds are intentionally not
        # presented as accuracy metrics and must be tuned against a labeled gate set.
        if plant_ratio < 0.12 or largest_component < 0.06:
            return {
                "valid": False,
                "status": "NOT_A_LEAF",
                "reason": "The uploaded image does not contain a sufficiently large, contiguous leaf-like region.",
                "quality": {
                    "plant_ratio": round(plant_ratio, 4),
                    "largest_component_ratio": round(largest_component, 4),
                    "edge_density": round(edge_density, 4),
                    "neutral_ratio": round(neutral_ratio, 4),
                },
            }

        return {
            "valid": True,
            "status": "LEAF_IMAGE_ACCEPTED",
            "quality": {
                "plant_ratio": round(plant_ratio, 4),
                "largest_component_ratio": round(largest_component, 4),
                "edge_density": round(edge_density, 4),
                "neutral_ratio": round(neutral_ratio, 4),
            },
        }
    except Exception as exc:
        return {"valid": False, "status": "INVALID_IMAGE", "reason": f"Image could not be decoded: {exc}"}


def extract_leaf_features_from_image(image_bytes: bytes) -> Dict[str, float]:
    """Extract deterministic visual features used by the legacy experimental artifact."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((160, 160))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]

    green_mask = (g > r * 1.05) & (g > b * 1.05) & (g > 0.20)
    yellow_mask = (r > 0.40) & (g > 0.40) & (b < 0.35) & (np.abs(r - g) < 0.25)
    brown_mask = (r > b * 1.2) & (g > b) & (r < 0.65) & (g < 0.55) & (r > 0.15)
    gray = 0.299 * r + 0.587 * g + 0.114 * b

    return {
        "greenness": round(float(np.mean(green_mask)), 3),
        "yellowing": round(float(np.mean(yellow_mask)), 3),
        "browning": round(float(np.mean(brown_mask)), 3),
        "texture": round(float(np.clip(np.std(gray) * 2.5, 0.05, 0.98)), 3),
    }


class LocalVisionAIModel:
    def __init__(self) -> None:
        self.model_data: Optional[Dict[str, Any]] = None
        self.load_model()

    def load_model(self) -> None:
        """Load only an audited artifact. Never auto-train or create a fallback model."""
        if not os.path.exists(MODEL_PATH):
            print("[VISION] No vision_model.joblib found; vision inference is UNAVAILABLE.")
            return
        try:
            data = joblib.load(MODEL_PATH)
            if not isinstance(data, dict) or "model" not in data:
                raise ValueError("Invalid vision artifact format: expected a dict containing 'model'.")

            # Reject the old synthetic artifact generated by train_vision_model.py.
            version = str(data.get("version", ""))
            metric = str(data.get("accuracy_metric", ""))
            if "NutrientPathology-QualcommEdge" in version or "99.9%" in metric:
                raise ValueError("Synthetic legacy vision artifact rejected; retrain on real image data.")

            self.model_data = data
            print("[VISION] Audited vision artifact loaded; status=EXPERIMENTAL.")
        except Exception as exc:
            self.model_data = None
            print(f"[VISION] Artifact rejected: {exc}")

    def diagnose(
        self,
        greenness: Optional[float] = None,
        yellowing: Optional[float] = None,
        browning: Optional[float] = None,
        texture: Optional[float] = None,
        soil_moisture: Optional[float] = None,
        humidity: Optional[float] = None,
        image_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        if image_bytes is None:
            return {
                "status": "INVALID_IMAGE",
                "provenance": "UNAVAILABLE",
                "diagnosis": None,
                "confidence_pct": None,
                "action": "Upload a clear close-up photo of a crop leaf.",
            }

        validation = validate_leaf_image(image_bytes)
        if not validation["valid"]:
            return {
                "status": validation["status"],
                "provenance": "UNAVAILABLE",
                "diagnosis": None,
                "confidence_pct": None,
                "action": "Upload a clear close-up photo containing a single crop leaf.",
                "reason": validation.get("reason"),
                "quality": validation.get("quality"),
            }

        features = extract_leaf_features_from_image(image_bytes)

        if self.model_data is None:
            return {
                "status": "MODEL_UNAVAILABLE",
                "provenance": "UNAVAILABLE",
                "diagnosis": None,
                "confidence_pct": None,
                "action": "Leaf vision model is not deployed. Do not use this result for diagnosis.",
                "model_name": "AgriSaathi Leaf Disease Vision",
                "model_version": None,
                "features": features,
            }

        try:
            model = self.model_data["model"]
            expected_features = getattr(model, "n_features_in_", None)
            # The legacy artifact may be 6-feature or 4-feature. Never silently feed the
            # wrong schema; fail closed instead.
            if expected_features not in (4, 6):
                raise ValueError(f"Unsupported vision artifact feature count: {expected_features}")

            visual = [features["greenness"], features["yellowing"], features["browning"], features["texture"]]
            if expected_features == 6:
                if soil_moisture is None or humidity is None:
                    return {
                        "status": "CONFIGURATION_REQUIRED",
                        "provenance": "UNAVAILABLE",
                        "diagnosis": None,
                        "confidence_pct": None,
                        "action": "Verified soil moisture and humidity are required by this model.",
                        "features": features,
                    }
                vector = visual + [float(soil_moisture), float(humidity)]
            else:
                vector = visual

            x = np.asarray([vector], dtype=np.float32)
            prediction = model.predict(x)[0]
            probabilities = model.predict_proba(x)[0] if hasattr(model, "predict_proba") else None
            confidence = round(float(np.max(probabilities)) * 100, 1) if probabilities is not None else None
            threshold = float(self.model_data.get("minimum_confidence_pct", 70.0))
            if confidence is None or confidence < threshold:
                return {
                    "status": "NO_RELIABLE_RESULT",
                    "provenance": "EXPERIMENTAL",
                    "diagnosis": None,
                    "confidence_pct": confidence,
                    "action": "The model is not confident enough to provide a disease diagnosis. Retake the photo with the leaf filling the frame.",
                    "model_name": self.model_data.get("model_name", "AgriSaathi Leaf Disease Vision"),
                    "model_version": self.model_data.get("version"),
                    "features": features,
                }

            remedies = self.model_data.get("remedies", {})
            return {
                "status": "EXPERIMENTAL_PREDICTION",
                "provenance": "EXPERIMENTAL",
                "diagnosis": str(prediction),
                "confidence_pct": confidence,
                "action": remedies.get(str(prediction), "Consult a qualified agronomist before treatment."),
                "model_name": self.model_data.get("model_name", "AgriSaathi Leaf Disease Vision"),
                "model_version": self.model_data.get("version"),
                "features": features,
                "warning": "Experimental model; field validation is required.",
            }
        except Exception as exc:
            return {
                "status": "MODEL_INCOMPATIBLE",
                "provenance": "UNAVAILABLE",
                "diagnosis": None,
                "confidence_pct": None,
                "action": "The deployed vision artifact is incompatible with the inference pipeline.",
                "error": str(exc),
                "features": features,
            }


local_vision_ai = LocalVisionAIModel()
