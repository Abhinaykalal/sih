"""Train AgriSaathi's experimental leaf-disease CV model from REAL images.

Expected dataset layout:
    datasets/vision/images/rice__healthy/*.jpg
    datasets/vision/images/rice__blast/*.jpg
    datasets/vision/images/tomato__early_blight/*.jpg

For stronger leakage protection, provide datasets/vision/vision_manifest.csv with
columns path,label,group_id. This script never creates synthetic training rows and
never writes a fake accuracy claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
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
    "Pepper__bell___Bacterial_spot": "Apply copper-based bactericide sprays; prune lower infected leaves and avoid overhead irrigation.",
    "Pepper__bell___healthy": "Plant is healthy. Maintain standard nutrient and moisture monitoring.",
    "Potato___Early_blight": "Apply Chlorothalonil or Mancozeb fungicide; remove infected lower foliage and practice crop rotation.",
    "Potato___Late_blight": "Immediately apply systemic fungicides (Metalaxyl or Mancozeb); destroy heavily blighted plants to prevent spore dispersal.",
    "Potato___healthy": "Plant is healthy. Maintain regular preventive scouting.",
    "Tomato_Bacterial_spot": "Apply copper bactericide + Mancozeb mixture; disinfect farming tools and avoid working in wet foliage.",
    "Tomato_Early_blight": "Apply preventive copper or Mancozeb spray; prune lower yellowing foliage and increase plant spacing for airflow.",
    "Tomato_Late_blight": "Apply systemic fungicide immediately (Cymoxanil/Mancozeb); minimize leaf wetness duration and ensure field drainage.",
    "Tomato_Leaf_Mold": "Improve greenhouse/field ventilation to reduce relative humidity below 85%; apply preventive bio-fungicides.",
    "Tomato_Septoria_leaf_spot": "Remove diseased lower leaves, apply organic copper or Chlorothalonil fungicide, and mulch soil to prevent soil-splash.",
    "": "Do not treat from the model result alone. Confirm the result with a qualified agronomist."
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


def hog_features(gray: np.ndarray, orientations: int = 9, cell: int = 8, block: int = 2) -> np.ndarray:
    """Dependency-free HOG implementation used identically at train and inference time."""
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
            frac = a - np.floor(a)
            for i in range(len(m)):
                hist[cy, cx, low[i]] += m[i] * (1.0 - frac[i])
                hist[cy, cx, high[i]] += m[i] * frac[i]
    vectors: List[np.ndarray] = []
    for cy in range(cells_y - block + 1):
        for cx in range(cells_x - block + 1):
            v = hist[cy:cy + block, cx:cx + block].ravel()
            v = v / np.sqrt(np.sum(v * v) + 1e-6)
            v = np.minimum(v, 0.2)
            v = v / np.sqrt(np.sum(v * v) + 1e-6)
            vectors.append(v)
    return np.concatenate(vectors).astype(np.float32)


def extract_features(path: Path) -> np.ndarray:
    img = ImageOps.exif_transpose(Image.open(path).convert("RGB")).resize((128, 128))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    gray = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    features = [hog_features(gray)]
    for channel in range(3):
        hist, _ = np.histogram(arr[..., channel], bins=16, range=(0.0, 1.0), density=False)
        hist = hist.astype(np.float32)
        hist /= max(float(hist.sum()), 1.0)
        features.append(hist)
    return np.concatenate(features)


def load_records(data_dir: Path, manifest_path: Path | None, max_per_class: int | None = None) -> List[Dict[str, str]]:
    records: List[Dict[str, str]] = []
    if manifest_path and manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if not {"path", "label", "group_id"}.issubset(set(reader.fieldnames or [])):
                raise ValueError("vision_manifest.csv must contain path,label,group_id")
            for row in reader:
                path = Path(row["path"])
                if not path.is_absolute():
                    path = data_dir.parent.parent / path
                if path.exists() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    records.append({"path": str(path), "label": row["label"], "group_id": row["group_id"]})
    else:
        for class_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
            class_files = [
                path for path in sorted(class_dir.rglob("*"))
                if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
            ]
            if max_per_class and len(class_files) > max_per_class:
                random.seed(SEED)
                class_files = random.sample(class_files, max_per_class)
            for path in class_files:
                records.append({"path": str(path), "label": class_dir.name, "group_id": sha256_file(path)})
    if not records:
        raise RuntimeError(f"No real images found in {data_dir}. Add a labeled image dataset before training.")
    return records


def split_records(records: List[Dict[str, str]]) -> Tuple[List[int], List[int], List[int]]:
    labels = np.asarray([r["label"] for r in records])
    groups = np.asarray([r["group_id"] for r in records])
    indices = np.arange(len(records))
    first = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=SEED)
    train_val, test = next(first.split(indices, labels, groups))
    second = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=SEED)
    train_rel, val_rel = next(second.split(train_val, labels[train_val], groups[train_val]))
    train, val = train_val[train_rel], train_val[val_rel]
    all_classes = set(labels)
    for name, split in (("train", train), ("validation", val), ("test", test)):
        missing = sorted(all_classes - set(labels[split]))
        if missing:
            raise RuntimeError(f"{name} split is missing classes {missing}. Add more real images/groups.")
    return train.tolist(), val.tolist(), test.tolist()


def evaluate(model, x: np.ndarray, y: np.ndarray) -> Dict[str, float]:
    pred = model.predict(x)
    return {
        "accuracy": round(float(accuracy_score(y, pred)), 6),
        "balanced_accuracy": round(float(balanced_accuracy_score(y, pred)), 6),
        "macro_precision": round(float(precision_score(y, pred, average="macro", zero_division=0)), 6),
        "macro_recall": round(float(recall_score(y, pred, average="macro", zero_division=0)), 6),
        "macro_f1": round(float(f1_score(y, pred, average="macro", zero_division=0)), 6),
    }


def find_default_data_dir() -> Path:
    candidates = [
        DEFAULT_DATA_DIR,
        Path(__file__).resolve().parents[1] / "datasets" / "PlantVillage",
        Path(__file__).resolve().parents[1] / "datasets" / "plantvillage dataset" / "color",
        Path(__file__).resolve().parents[1] / "datasets" / "plantvillage dataset",
        Path(__file__).resolve().parents[1] / "datasets" / "raw" / "plantvillage",
        Path(__file__).resolve().parents[1] / "datasets" / "raw" / "plantdoc",
    ]
    for c in candidates:
        if c.exists() and any(p.is_dir() for p in c.iterdir()):
            return c
    return DEFAULT_DATA_DIR


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=MODEL_PATH)
    parser.add_argument("--max-per-class", type=int, default=300, help="Max images per class for balanced fast training (0 for unlimited)")
    args = parser.parse_args()
    set_seed()
    
    data_dir = args.data_dir or find_default_data_dir()
    if not data_dir.exists():
        raise SystemExit(f"REAL DATASET REQUIRED: {data_dir} does not exist. Training was not run.")
    print(f"Loading real image dataset from: {data_dir}")
    manifest = args.manifest if args.manifest.exists() else None
    max_count = args.max_per_class if args.max_per_class > 0 else None
    records = load_records(data_dir, manifest, max_per_class=max_count)
    labels = sorted({r["label"] for r in records})
    print(f"Loaded {len(records)} total images across {len(labels)} classes: {labels}")
    if len(labels) < 2:
        raise SystemExit("At least two real image classes are required.")
    train_idx, val_idx, test_idx = split_records(records)
    print(f"Splits -> Train: {len(train_idx)}, Val: {len(val_idx)}, Test: {len(test_idx)}")
    
    print("Extracting HOG & RGB histogram foliar features...")
    features_list = []
    for idx, r in enumerate(records):
        features_list.append(extract_features(Path(r["path"])))
        if (idx + 1) % 500 == 0 or (idx + 1) == len(records):
            print(f"  Processed {idx + 1}/{len(records)} images...")
    X = np.stack(features_list)
    y = np.asarray([r["label"] for r in records])
    
    print("Fitting CalibratedClassifierCV (LinearSVC)...")
    model = CalibratedClassifierCV(
        LinearSVC(C=1.0, class_weight="balanced", random_state=SEED, max_iter=10000),
        cv=3,
        method="sigmoid",
    )
    model.fit(X[train_idx], y[train_idx])
    metrics = {"validation": evaluate(model, X[val_idx], y[val_idx]), "test": evaluate(model, X[test_idx], y[test_idx])}
    artifact = {
        "artifact_type": "agrisaathi_vision_hog_svm_v1",
        "model_name": "AgriSaathi Leaf Disease Vision (real-image HOG + calibrated LinearSVC)",
        "version": "vision-hog-svm-1.0.0",
        "model": model,
        "classes": labels,
        "feature_config": {**FEATURE_CONFIG, "feature_length": int(X.shape[1])},
        "dataset": {
            "image_count": len(records),
            "class_count": len(labels),
            "manifest": str(manifest) if manifest else None,
            "split_strategy": "grouped 80/20 test then 75/25 train/validation; SHA256 grouping when no manifest is supplied",
        },
        "metrics": metrics,
        "minimum_confidence_pct": 70.0,
        "remedies": REMEDIES,
        "training_seed": SEED,
        "status": "EXPERIMENTAL",
        "limitations": [
            "Classical CV baseline; not field validated.",
            "Plant/session group_id should be supplied in the manifest for stronger leakage control.",
            "External unseen-farm/camera validation is required before production use.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, args.output)
    args.output.with_suffix(".metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("\nTraining complete! Metrics on held-out evaluation data:")
    print(json.dumps(metrics, indent=2))
    print(f"\nSaved REAL-IMAGE vision artifact: {args.output}")


if __name__ == "__main__":
    main()
