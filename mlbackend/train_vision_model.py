"""Train AgriSaathi's experimental leaf-disease CV model from REAL images.

Expected dataset layout:

    datasets/vision/images/
        rice__healthy/*.jpg
        rice__blast/*.jpg
        rice__brown_spot/*.jpg
        tomato__early_blight/*.jpg
        ...

The folder name is the class label. ``crop__disease`` is recommended so crop context
is explicit in the artifact. For stronger leakage protection, provide
``datasets/vision/vision_manifest.csv`` with columns ``path,label,group_id``.  Images
with the same group_id (for example the same plant/session) are kept in one split.

This script deliberately fails if the real image dataset is absent. It never creates
synthetic training rows and never writes a fake high-accuracy model.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
from PIL import Image, ImageOps
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.svm import LinearSVC
from skimage.feature import hog

MODEL_PATH = Path(__file__).with_name("vision_model.joblib")
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "datasets" / "vision" / "images"
DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "datasets" / "vision" / "vision_manifest.csv"
SEED = 42
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

FEATURE_CONFIG = {
    "image_size": [128, 128],
    "hog_orientations": 9,
    "hog_pixels_per_cell": [8, 8],
    "hog_cells_per_block": [2, 2],
    "rgb_hist_bins": 16,
}

REMEDIES = {
    "": "Do not treat from the model result alone. Confirm the diagnosis with a qualified agronomist.",
}


def set_seed() -> None:
    random.seed(SEED)
    np.random.seed(SEED)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def extract_features(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    img = ImageOps.exif_transpose(img).resize(tuple(FEATURE_CONFIG["image_size"]))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    gray = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]

    hog_features = hog(
        gray,
        orientations=FEATURE_CONFIG["hog_orientations"],
        pixels_per_cell=tuple(FEATURE_CONFIG["hog_pixels_per_cell"]),
        cells_per_block=tuple(FEATURE_CONFIG["hog_cells_per_block"]),
        block_norm="L2-Hys",
        feature_vector=True,
    ).astype(np.float32)

    hist_features: List[float] = []
    bins = int(FEATURE_CONFIG["rgb_hist_bins"])
    for channel in range(3):
        hist, _ = np.histogram(arr[..., channel], bins=bins, range=(0.0, 1.0), density=True)
        hist = hist.astype(np.float32)
        hist /= max(float(hist.sum()), 1.0)
        hist_features.extend(hist.tolist())

    return np.concatenate([hog_features, np.asarray(hist_features, dtype=np.float32)])


def load_records(data_dir: Path, manifest_path: Path | None) -> List[Dict[str, str]]:
    records: List[Dict[str, str]] = []
    if manifest_path and manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            required = {"path", "label", "group_id"}
            if not required.issubset(set(reader.fieldnames or [])):
                raise ValueError("vision_manifest.csv must contain path,label,group_id")
            for row in reader:
                path = Path(row["path"])
                if not path.is_absolute():
                    path = data_dir.parent.parent / path
                if path.suffix.lower() in SUPPORTED_EXTENSIONS and path.exists():
                    records.append({"path": str(path), "label": row["label"], "group_id": row["group_id"]})
    else:
        for class_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
            label = class_dir.name
            for path in sorted(class_dir.rglob("*")):
                if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    # Exact-file hash prevents identical files from crossing splits.
                    # A manifest group_id is still recommended for near-duplicate/session leakage.
                    records.append({
                        "path": str(path),
                        "label": label,
                        "group_id": sha256_file(path),
                    })

    if not records:
        raise RuntimeError(
            f"No real images found in {data_dir}. Add a labeled image dataset before training."
        )
    return records


def split_records(records: List[Dict[str, str]]) -> Tuple[List[int], List[int], List[int]]:
    labels = np.asarray([r["label"] for r in records])
    groups = np.asarray([r["group_id"] for r in records])
    indices = np.arange(len(records))

    first = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=SEED)
    train_val_idx, test_idx = next(first.split(indices, labels, groups))

    second = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=SEED)
    train_rel, val_rel = next(second.split(train_val_idx, labels[train_val_idx], groups[train_val_idx]))
    train_idx = train_val_idx[train_rel]
    val_idx = train_val_idx[val_rel]

    all_classes = set(labels)
    for name, split in (("train", train_idx), ("validation", val_idx), ("test", test_idx)):
        missing = sorted(all_classes - set(labels[split]))
        if missing:
            raise RuntimeError(
                f"{name} split is missing classes {missing}. Add more real images/groups before training."
            )
    return train_idx.tolist(), val_idx.tolist(), test_idx.tolist()


def evaluate(model, x: np.ndarray, y: np.ndarray) -> Dict[str, float]:
    pred = model.predict(x)
    return {
        "accuracy": round(float(accuracy_score(y, pred)), 6),
        "balanced_accuracy": round(float(balanced_accuracy_score(y, pred)), 6),
        "macro_precision": round(float(precision_score(y, pred, average="macro", zero_division=0)), 6),
        "macro_recall": round(float(recall_score(y, pred, average="macro", zero_division=0)), 6),
        "macro_f1": round(float(f1_score(y, pred, average="macro", zero_division=0)), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=MODEL_PATH)
    args = parser.parse_args()

    set_seed()
    if not args.data_dir.exists():
        raise SystemExit(
            f"REAL DATASET REQUIRED: {args.data_dir} does not exist. Training was not run."
        )

    manifest = args.manifest if args.manifest.exists() else None
    records = load_records(args.data_dir, manifest)
    labels = sorted({r["label"] for r in records})
    if len(labels) < 2:
        raise SystemExit("At least two real image classes are required.")

    train_idx, val_idx, test_idx = split_records(records)
    print(f"Dataset: {len(records)} images / {len(labels)} classes")
    print(f"Split: train={len(train_idx)}, validation={len(val_idx)}, test={len(test_idx)}")

    cache: Dict[str, np.ndarray] = {}
    for record in records:
        path = record["path"]
        cache[path] = extract_features(Path(path))

    X = np.stack([cache[r["path"]] for r in records])
    y = np.asarray([r["label"] for r in records])

    # Linear SVM over actual image features, followed by held-out calibration.
    base = LinearSVC(C=1.0, class_weight="balanced", random_state=SEED, max_iter=10000)
    calibrated = CalibratedClassifierCV(base, cv=3, method="sigmoid")
    calibrated.fit(X[train_idx], y[train_idx])

    val_metrics = evaluate(calibrated, X[val_idx], y[val_idx])
    test_metrics = evaluate(calibrated, X[test_idx], y[test_idx])

    artifact = {
        "artifact_type": "agrisaathi_vision_hog_svm_v1",
        "model_name": "AgriSaathi Leaf Disease Vision (HOG + calibrated LinearSVC)",
        "version": "vision-hog-svm-1.0.0",
        "model": calibrated,
        "classes": labels,
        "feature_config": {**FEATURE_CONFIG, "feature_length": int(X.shape[1])},
        "dataset": {
            "root": str(args.data_dir),
            "manifest": str(manifest) if manifest else None,
            "image_count": len(records),
            "class_count": len(labels),
            "split_strategy": "grouped 80/20 test then 75/25 train/validation; exact-image SHA256 grouping without manifest",
        },
        "metrics": {
            "validation": val_metrics,
            "test": test_metrics,
        },
        "minimum_confidence_pct": 70.0,
        "remedies": REMEDIES,
        "training_seed": SEED,
        "status": "EXPERIMENTAL",
        "limitations": [
            "This is a classical CV baseline, not a field-validated clinical/agronomic diagnosis system.",
            "A manifest with plant/session group_id is required for strong leakage control.",
            "External field validation on unseen farms/cameras is required before production use.",
            "Confidence is calibrated on the training workflow but is not a guarantee of field correctness.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, args.output)

    metrics_path = args.output.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(artifact["metrics"], indent=2), encoding="utf-8")
    print(json.dumps(artifact["metrics"], indent=2))
    print(f"Saved REAL-IMAGE vision artifact: {args.output}")


if __name__ == "__main__":
    main()
