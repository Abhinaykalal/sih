"""
AgriSaathi Vision Pipeline — End-to-End Pipeline Orchestrator
============================================================
Unifies dataset ingestion, disjoint splitting, foliar feature preprocessing,
ensemble model training, and honest metric evaluation.

Supports multiple dataset directories (PlantDoc + PlantVillage combined).

Execution:
    python -m mlbackend.vision.pipeline
    python -m mlbackend.vision.pipeline --dataset-dir datasets/raw/plantdoc datasets/raw/plantvillage
"""

import os
import sys
import json
import time
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

try:
    from .manifest import DatasetManifest, get_standard_manifest
    from .ingestion import ImageIngestionEngine
    from .split import disjoint_stratified_split
    from .preprocessing import extract_features_from_image_bytes
    from .training import train_vision_ensemble
    from .evaluation import evaluate_model_performance
    from .inference import run_vision_inference
    from .test_fixture import generate_and_train_test_fixture
except ImportError:
    from manifest import DatasetManifest, get_standard_manifest
    from ingestion import ImageIngestionEngine
    from split import disjoint_stratified_split
    from preprocessing import extract_features_from_image_bytes
    from training import train_vision_ensemble
    from evaluation import evaluate_model_performance
    from inference import run_vision_inference
    from test_fixture import generate_and_train_test_fixture


def _extract_features_batch(samples: List[Dict[str, Any]], tag: str = "") -> tuple:
    """Extract rich feature vectors from a batch of image files.
    
    Returns (X, y) where X is np.ndarray of 90 features and y is list of labels.
    """
    features = []
    labels = []
    skipped = 0

    total = len(samples)
    for i, sample in enumerate(samples):
        filepath = sample["filepath"]
        label = sample["label"]

        try:
            with open(filepath, "rb") as f:
                img_bytes = f.read()

            feat = extract_features_from_image_bytes(img_bytes)
            fv = feat.get("feature_vector")
            if fv and len(fv) > 0:
                features.append(fv)
            else:
                # Fallback to legacy 4 features
                features.append([
                    feat["greenness"],
                    feat["yellowing"],
                    feat["browning"],
                    feat["texture"]
                ])
            labels.append(label)
        except Exception as e:
            skipped += 1
            continue

        if (i + 1) % 500 == 0 or (i + 1) == total:
            print(f"  [{tag}] Processed {i+1}/{total} images (skipped: {skipped})")

    return np.array(features, dtype=np.float32), labels


def _check_for_images(directory: str) -> bool:
    """Check if a directory contains image files."""
    if not directory or not os.path.exists(directory):
        return False
    return any(
        f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        for _, _, files in os.walk(directory)
        for f in files
    )


def run_pipeline(
    dataset_dir: Optional[str] = None,
    dataset_dirs: Optional[List[str]] = None,
    output_model_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Runs the full vision training pipeline:
    1. Ingest images from one or more dataset directories (integrity + dedup)
    2. Disjoint stratified split (70/15/15)
    3. Extract foliar features from all splits
    4. Train calibrated voting ensemble
    5. Evaluate on held-out test set
    6. Save model artifact and metrics

    Args:
        dataset_dir: Single dataset directory (backward compatible)
        dataset_dirs: List of dataset directories to merge
        output_model_path: Output model path

    Falls back to test fixture if no real images are found.
    """
    if not output_model_path:
        output_model_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "vision_model.joblib"
        )

    # Build list of directories to scan
    dirs_to_scan = []
    if dataset_dirs:
        dirs_to_scan.extend(dataset_dirs)
    if dataset_dir:
        dirs_to_scan.append(dataset_dir)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_dirs = []
    for d in dirs_to_scan:
        abs_d = os.path.abspath(d)
        if abs_d not in seen:
            seen.add(abs_d)
            unique_dirs.append(d)
    dirs_to_scan = unique_dirs

    # Check which directories have images
    active_dirs = [d for d in dirs_to_scan if _check_for_images(d)]

    if not active_dirs:
        print("[Vision Pipeline] No real images found in any directory. Training TEST_ONLY fixture.")
        res = generate_and_train_test_fixture(output_path=output_model_path)
        return {
            "status": "COMPLETED_TEST_FIXTURE",
            "model_status": "TEST_ONLY",
            "warning": "Trained on synthetic test fixture. Not validated for field deployment.",
            "metrics": res.get("evaluation", {}),
            "output_path": output_model_path
        }

    # ===== PHASE 1: INGESTION =====
    print("\n" + "=" * 60)
    print("PHASE 1: IMAGE INGESTION & DEDUPLICATION")
    print("=" * 60)
    start_time = time.time()

    all_samples = []
    total_duplicates = 0
    total_corrupt = 0
    datasets_used = []

    for d in active_dirs:
        print(f"\n  Scanning: {d}")
        engine = ImageIngestionEngine(d)
        ingest_result = engine.ingest_directory(d)
        
        dir_name = os.path.basename(d)
        datasets_used.append(dir_name)
        
        print(f"    Valid:      {ingest_result['total_valid_images']}")
        print(f"    Duplicates: {ingest_result['duplicates_removed']}")
        print(f"    Corrupt:    {ingest_result['corrupt_removed']}")
        print(f"    Classes:    {len(ingest_result['classes_detected'])}")
        
        all_samples.extend(engine.images)
        total_duplicates += ingest_result['duplicates_removed']
        total_corrupt += ingest_result['corrupt_removed']

    # Cross-directory deduplication by hash
    seen_hashes = set()
    deduped_samples = []
    cross_dups = 0
    for s in all_samples:
        h = s["hash"]
        if h in seen_hashes:
            cross_dups += 1
            continue
        seen_hashes.add(h)
        deduped_samples.append(s)

    all_samples = deduped_samples
    total_images = len(all_samples)

    if cross_dups > 0:
        print(f"\n  Cross-dataset duplicates removed: {cross_dups}")

    classes_detected = sorted(list(set(s["label"] for s in all_samples)))
    print(f"\n  COMBINED TOTALS:")
    print(f"    Datasets:         {', '.join(datasets_used)}")
    print(f"    Total images:     {total_images}")
    print(f"    Total duplicates: {total_duplicates + cross_dups}")
    print(f"    Total corrupt:    {total_corrupt}")
    print(f"    Total classes:    {len(classes_detected)}")

    if total_images < 50:
        print(f"\n  WARNING: Only {total_images} images. Minimum 50 required.")
        print("  Falling back to test fixture.")
        res = generate_and_train_test_fixture(output_path=output_model_path)
        return {
            "status": "INSUFFICIENT_DATA",
            "model_status": "TEST_ONLY",
            "warning": f"Only {total_images} images found. Need at least 50.",
            "metrics": res.get("evaluation", {}),
            "output_path": output_model_path
        }

    # Filter classes with too few samples (< 5 images)
    class_counts = {}
    for s in all_samples:
        class_counts[s["label"]] = class_counts.get(s["label"], 0) + 1

    min_samples_per_class = 5
    valid_classes = {c for c, n in class_counts.items() if n >= min_samples_per_class}
    dropped_classes = {c for c, n in class_counts.items() if n < min_samples_per_class}

    if dropped_classes:
        print(f"\n  Dropping {len(dropped_classes)} classes with < {min_samples_per_class} samples:")
        for c in sorted(dropped_classes):
            print(f"    - {c} ({class_counts[c]} images)")

    filtered_samples = [s for s in all_samples if s["label"] in valid_classes]
    print(f"\n  Training classes: {len(valid_classes)} ({len(filtered_samples)} images)")
    for c in sorted(valid_classes):
        print(f"    - {c}: {class_counts[c]} images")

    ingest_time = time.time() - start_time
    print(f"\n  Ingestion completed in {ingest_time:.1f}s")

    # ===== PHASE 2: DISJOINT SPLIT =====
    print("\n" + "=" * 60)
    print("PHASE 2: DISJOINT STRATIFIED SPLIT (70/15/15)")
    print("=" * 60)

    train_samples, val_samples, test_samples = disjoint_stratified_split(
        filtered_samples, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42
    )

    print(f"  Train: {len(train_samples)} images")
    print(f"  Val:   {len(val_samples)} images")
    print(f"  Test:  {len(test_samples)} images")

    # Verify no leakage (no filepath overlap)
    train_paths = set(s["filepath"] for s in train_samples)
    val_paths = set(s["filepath"] for s in val_samples)
    test_paths = set(s["filepath"] for s in test_samples)

    leak_tv = train_paths & val_paths
    leak_tt = train_paths & test_paths
    leak_vt = val_paths & test_paths

    if leak_tv or leak_tt or leak_vt:
        print(f"  CRITICAL: Data leakage detected! train-val={len(leak_tv)}, train-test={len(leak_tt)}, val-test={len(leak_vt)}")
        raise RuntimeError("Data leakage detected in split. Aborting training.")
    else:
        print("  Leakage check: PASSED (zero overlap between splits)")

    # ===== PHASE 3: FEATURE EXTRACTION =====
    print("\n" + "=" * 60)
    print("PHASE 3: FOLIAR FEATURE EXTRACTION")
    print("=" * 60)
    start_time = time.time()

    print(f"\n  Extracting train features...")
    X_train, y_train = _extract_features_batch(train_samples, tag="TRAIN")

    print(f"\n  Extracting validation features...")
    X_val, y_val = _extract_features_batch(val_samples, tag="VAL")

    print(f"\n  Extracting test features...")
    X_test, y_test = _extract_features_batch(test_samples, tag="TEST")

    feat_time = time.time() - start_time
    print(f"\n  Feature extraction completed in {feat_time:.1f}s")
    print(f"  Train shape: {X_train.shape}, Val shape: {X_val.shape}, Test shape: {X_test.shape}")

    # ===== PHASE 4: TRAINING =====
    print("\n" + "=" * 60)
    print("PHASE 4: ENSEMBLE MODEL TRAINING")
    print("=" * 60)
    start_time = time.time()

    train_result = train_vision_ensemble(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        output_path=output_model_path
    )

    train_time = time.time() - start_time
    print(f"  Training completed in {train_time:.1f}s")
    print(f"  Samples trained: {train_result['samples_trained']}")
    print(f"  Classes: {train_result['classes_count']}")

    val_eval = train_result.get("evaluation", {})
    if val_eval:
        print(f"\n  Validation Metrics:")
        print(f"    Accuracy:    {val_eval.get('overall_accuracy', 'N/A')}")
        print(f"    Macro F1:    {val_eval.get('macro_f1', 'N/A')}")
        print(f"    Weighted F1: {val_eval.get('weighted_f1', 'N/A')}")

    # ===== PHASE 5: TEST SET EVALUATION =====
    print("\n" + "=" * 60)
    print("PHASE 5: HELD-OUT TEST SET EVALUATION")
    print("=" * 60)

    # Load the saved model to ensure we evaluate exactly what was persisted
    import joblib
    saved_package = joblib.load(output_model_path)
    model = saved_package["model"]
    scaler = saved_package.get("scaler")

    # Apply same scaling used during training
    X_test_eval = scaler.transform(X_test) if scaler is not None else X_test
    y_pred = model.predict(X_test_eval)
    test_classes = sorted(list(set(y_test + list(y_pred))))
    test_eval = evaluate_model_performance(y_test, list(y_pred), test_classes)

    print(f"\n  Test Set Results ({len(y_test)} samples):")
    print(f"    Overall Accuracy: {test_eval['overall_accuracy']}")
    print(f"    Macro F1:         {test_eval['macro_f1']}")
    print(f"    Weighted F1:      {test_eval['weighted_f1']}")
    print(f"\n  Per-Class Breakdown:")
    for cls, metrics in test_eval.get("per_class_metrics", {}).items():
        print(f"    {cls:45s}  P={metrics['precision']:.3f}  R={metrics['recall']:.3f}  F1={metrics['f1_score']:.3f}  n={metrics['support']}")

    print(f"\n  Confusion Matrix:")
    for row in test_eval.get("confusion_matrix", []):
        print(f"    {row}")

    # ===== SAVE RESULTS =====
    total_time = ingest_time + feat_time + train_time

    result = {
        "status": "COMPLETED_REAL_DATA",
        "model_status": "EXPERIMENTAL",
        "datasets_used": datasets_used,
        "total_images_ingested": total_images,
        "classes_trained": len(valid_classes),
        "classes_dropped": len(dropped_classes),
        "split": {
            "train": len(train_samples),
            "val": len(val_samples),
            "test": len(test_samples)
        },
        "leakage_check": "PASSED",
        "validation_metrics": val_eval,
        "test_metrics": test_eval,
        "training_time_seconds": round(total_time, 1),
        "output_path": output_model_path,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Model saved to: {output_model_path}")
    print(f"  Datasets:   {', '.join(datasets_used)}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Status: EXPERIMENTAL (requires field validation)")

    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AgriSaathi Vision Training Pipeline")
    parser.add_argument("--dataset-dir", nargs="+", default=None,
                        help="Path(s) to image dataset directories (PlantDoc, PlantVillage, etc.)")
    parser.add_argument("--output", default=None, help="Output model path")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    if args.dataset_dir:
        dataset_dirs = args.dataset_dir
    else:
        # Auto-detect available datasets
        dataset_dirs = []
        for name in ["plantdoc", "plantvillage"]:
            d = os.path.join(root, "datasets", "raw", name)
            if os.path.exists(d):
                dataset_dirs.append(d)
        
        if not dataset_dirs:
            dataset_dirs = [os.path.join(root, "datasets", "raw", "plantdoc")]

    result = run_pipeline(dataset_dirs=dataset_dirs, output_model_path=args.output)
    
    # Save full results JSON
    results_path = os.path.join(root, "models", "leaf_disease_vision", "pipeline_results.json")
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Full results saved to: {results_path}")
