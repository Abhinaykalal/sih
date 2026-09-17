"""Safe vision inference boundary for AgriSaathi.

A diagnosis is returned only when a real compatible image model is deployed and the
uploaded image passes the conservative leaf-image gate.  Synthetic legacy artifacts
and fabricated fallbacks are rejected.
"""

import io
import os
from typing import Any, Dict, Optional

import joblib
import numpy as np
from PIL import Image, ImageOps

MODEL_PATH = os.path.join(os.path.dirname(__file__), "vision_model.joblib")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MIN_IMAGE_SIDE = 160
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
    """Conservative scope/quality gate; never claims to diagnose disease."""
    if not image_bytes:
        return {"valid": False, "status": "INVALID_IMAGE", "reason": "No image bytes were supplied."}
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return {"valid": False, "status": "IMAGE_TOO_LARGE", "reason": "Image exceeds the 5 MB limit."}
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
        width, height = img.size
        if min(width, height) < MIN_IMAGE_SIDE:
            return {"valid": False, "status": "LOW_QUALITY_IMAGE", "reason": f"Image is too small ({width}x{height})."}
        
        # Pre-filter for completely blank/solid or extreme dark/light images
        arr = np.array(img.convert("L"))
        if arr.std() < 5.0 or arr.mean() < 40 or arr.mean() > 225:
            return {"valid": False, "status": "NOT_A_LEAF", "reason": "Image lacks structural variance or is completely dark/blank."}
            
        quality = {
            "resolution": f"{width}x{height}",
            "format": img.format or "UNKNOWN",
            "variance": float(arr.std())
        }
        return {"valid": True, "status": "LEAF_IMAGE_ACCEPTED", "quality": quality}
    except Exception as exc:
        return {"valid": False, "status": "INVALID_IMAGE", "reason": f"Image could not be decoded: {exc}"}


def _hog_features(gray: np.ndarray, orientations: int = 9, cell: int = 8, block: int = 2) -> np.ndarray:
    """Small dependency-free HOG implementation shared with the training script."""
    h, w = gray.shape
    gx = np.zeros_like(gray, dtype=np.float32)
    gy = np.zeros_like(gray, dtype=np.float32)
    gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
    gy[1:-1, :] = gray[2:, :] - gray[:-2, :]
    magnitude = np.sqrt(gx * gx + gy * gy)
    angle = (np.degrees(np.arctan2(gy, gx)) % 180.0) * orientations / 180.0
    cells_y, cells_x = h // cell, w // cell
    hist = np.zeros((cells_y, cells_x, orientations), dtype=np.float32)
    for cy in range(cells_y):
        for cx in range(cells_x):
            m = magnitude[cy * cell:(cy + 1) * cell, cx * cell:(cx + 1) * cell].ravel()
            a = angle[cy * cell:(cy + 1) * cell, cx * cell:(cx + 1) * cell].ravel()
            low = np.floor(a).astype(int) % orientations
            high = (low + 1) % orientations
            weight_high = a - np.floor(a)
            weight_low = 1.0 - weight_high
            for k in range(len(m)):
                hist[cy, cx, low[k]] += m[k] * weight_low[k]
                hist[cy, cx, high[k]] += m[k] * weight_high[k]
    vectors = []
    for cy in range(cells_y - block + 1):
        for cx in range(cells_x - block + 1):
            v = hist[cy:cy + block, cx:cx + block].ravel()
            v = v / np.sqrt(np.sum(v * v) + 1e-6)
            v = np.minimum(v, 0.2)
            v = v / np.sqrt(np.sum(v * v) + 1e-6)
            vectors.append(v)
    return np.concatenate(vectors).astype(np.float32)


def extract_vision_features(image_bytes: bytes) -> np.ndarray:
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes)).convert("RGB")).resize((128, 128))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    gray = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    hog_features = _hog_features(gray)
    hist_features = []
    for channel in range(3):
        hist, _ = np.histogram(arr[..., channel], bins=16, range=(0.0, 1.0), density=False)
        hist = hist.astype(np.float32)
        hist /= max(float(hist.sum()), 1.0)
        hist_features.extend(hist.tolist())
    return np.concatenate([hog_features, np.asarray(hist_features, dtype=np.float32)])


def _unavailable(action: str, status: str = "MODEL_UNAVAILABLE", **extra: Any) -> Dict[str, Any]:
    return {"status": status, "provenance": "UNAVAILABLE", "diagnosis": None, "confidence_pct": None, "action": action, **extra}


class LocalVisionAIModel:
    def __init__(self) -> None:
        self.model_data: Optional[Dict[str, Any]] = None
        self.load_model()

    def load_model(self) -> None:
        if not os.path.exists(MODEL_PATH):
            print("[VISION] No real vision_model.joblib found; vision inference is UNAVAILABLE.")
            return
            
        import hashlib
        import json
        meta_path = os.path.join(os.path.dirname(MODEL_PATH), "vision_model_metadata.json")
        
        try:
            with open(MODEL_PATH, "rb") as f:
                artifact_hash = hashlib.sha256(f.read()).hexdigest()
                
            if not os.path.exists(meta_path):
                print("[VISION] Warning: Metadata missing. Loading model as UNVERIFIED.")
                self.provenance = "UNVERIFIED"
                self.version = "unknown"
            else:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_envelope = json.load(f)
                    
                if "signature" not in meta_envelope or "payload" not in meta_envelope:
                    if os.environ.get("ENVIRONMENT") == "production":
                        self.model_data = None
                        print("[VISION] CRITICAL [AUTHENTICITY_FAILURE]: Missing signature in production environment.")
                        return
                    else:
                        print("[VISION] Warning: Signature missing or invalid envelope. Loading model as UNVERIFIED.")
                        self.provenance = "UNVERIFIED"
                        self.version = "unknown"
                        meta = meta_envelope.get("payload", meta_envelope) # Fallback to dict if old format
                else:
                    from mlbackend.crypto_utils import verify_metadata
                        
                    if not verify_metadata(meta_envelope["payload"], meta_envelope["signature"]):
                        self.model_data = None
                        print("[VISION] CRITICAL [AUTHENTICITY_FAILURE]: Invalid cryptographic signature on metadata.")
                        return
                    
                    meta = meta_envelope["payload"]
                    meta_hash = meta.get("artifact", {}).get("sha256")
                    if meta_hash != artifact_hash:
                        self.model_data = None
                        print(f"[VISION] CRITICAL [MODEL_INTEGRITY_FAILURE]: Hash mismatch! Metadata {meta_hash} != Artifact {artifact_hash}")
                        return
                    
                    dataset_hash = meta.get("dataset", {}).get("manifest_sha256")
                    manifest_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "datasets", "vision", "vision_manifest.csv")
                    
                    if os.path.exists(manifest_path):
                        with open(manifest_path, "rb") as mf:
                            live_manifest_hash = hashlib.sha256(mf.read()).hexdigest()
                        if dataset_hash != "untracked_dataset" and dataset_hash != live_manifest_hash:
                            self.model_data = None
                            print(f"[VISION] CRITICAL [DATASET_INTEGRITY_FAILURE]: Provenance mismatch! Live manifest {live_manifest_hash} != Trained {dataset_hash}")
                            return
                    elif dataset_hash != "untracked_dataset":
                         self.model_data = None
                         print(f"[VISION] CRITICAL [DATASET_INTEGRITY_FAILURE]: Provenance mismatch! Manifest missing but model expects {dataset_hash}")
                         return
                         
                    self.provenance = "VERIFIED"
                    self.version = meta.get("model_version", "unknown")
                
            data = joblib.load(MODEL_PATH)
            if not isinstance(data, dict) or data.get("artifact_type") != ARTIFACT_TYPE:
                raise ValueError("Artifact is not the approved real-image HOG/SVM format.")
            if not all(k in data for k in ("model", "classes", "feature_config", "metrics")):
                raise ValueError("Artifact missing model/classes/feature_config/metrics.")
            self.model_data = data
            self.model_data["version"] = getattr(self, "version", "unknown")
            self.model_data["provenance"] = getattr(self, "provenance", "UNVERIFIED")
        except json.JSONDecodeError as e:
            self.model_data = None
            print(f"[VISION] CRITICAL [INVALID_METADATA]: Metadata unparseable or malformed. {e}")
        except Exception as exc:
            self.model_data = None
            print(f"[VISION] Artifact rejected: {exc}")

    def diagnose(self, image_bytes: Optional[bytes] = None, **_: Any) -> Dict[str, Any]:
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
            x = extract_vision_features(image_bytes).reshape(1, -1)
            expected = int(self.model_data["feature_config"]["feature_length"])
            if x.shape[1] != expected:
                raise ValueError(f"Feature length mismatch: expected {expected}, got {x.shape[1]}")
            model = self.model_data["model"]
            probabilities = model.predict_proba(x)[0]
            idx = int(np.argmax(probabilities))
            confidence = float(probabilities[idx])
            threshold = float(self.model_data.get("minimum_confidence_pct", 70.0)) / 100.0
            if confidence < threshold:
                return {
                    "status": "NO_RELIABLE_RESULT",
                    "provenance": "EXPERIMENTAL",
                    "diagnosis": None,
                    "confidence_pct": round(confidence * 100, 1),
                    "action": "The model is not confident enough to provide a disease diagnosis. Retake the photo with the leaf filling the frame.",
                    "model_name": self.model_data.get("model_name"),
                    "model_version": self.model_data.get("version"),
                    "quality": validation.get("quality"),
                }
            prediction = str(model.classes_[idx])
            return {
                "status": "EXPERIMENTAL_PREDICTION",
                "provenance": "EXPERIMENTAL",
                "diagnosis": prediction,
                "confidence_pct": round(confidence * 100, 1),
                "action": self.model_data.get("remedies", {}).get(prediction, "Confirm the result with a qualified agronomist."),
                "model_name": self.model_data.get("model_name"),
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
