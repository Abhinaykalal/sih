"""Dataset provenance and reproducible quality-report helpers.

This module deliberately refuses to manufacture dataset counts or model metrics.
Reports are derived from files that actually exist on disk. Missing manifests are
reported as NOT_AVAILABLE instead of being presented as validated evidence.
"""

import csv
import hashlib
import json
import os
from collections import Counter
from typing import Any, Dict, List, Optional

DATASET_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "datasets")
VISION_ROOT = os.path.join(DATASET_ROOT, "vision")
VISION_MANIFEST = os.path.join(VISION_ROOT, "vision_manifest.csv")


def init_dataset_structure() -> None:
    """Create local dataset directories without inventing metadata."""
    for directory in ("raw", "cleaned", "train", "validation", "test", "metadata"):
        os.makedirs(os.path.join(DATASET_ROOT, directory), exist_ok=True)


def _read_manifest(path: str = VISION_MANIFEST) -> Optional[List[Dict[str, str]]]:
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_dataset_quality_report(manifest_path: str = VISION_MANIFEST) -> Dict[str, Any]:
    """Return evidence-backed dataset status.

    A manifest with no rows is not treated as a validated dataset. The function
    reports observed labels and missing evidence rather than hard-coded metrics.
    """
    rows = _read_manifest(manifest_path)
    if rows is None:
        return {
            "status": "NOT_AVAILABLE",
            "evidence": "No vision_manifest.csv is present at the expected path.",
            "manifest_path": manifest_path,
            "total_samples": None,
            "classes_count": None,
            "class_distribution": {},
            "quality_metrics": {
                "corrupted_images_removed": None,
                "near_duplicates_removed": None,
                "leakage_risk_score": None,
            },
            "leakage_prevented": None,
        }

    labels = Counter()
    missing_files = 0
    hashes = Counter()
    group_values = set()
    duplicate_rows = 0

    for row in rows:
        label = (row.get("label") or row.get("class") or "UNKNOWN").strip()
        labels[label] += 1
        image_path = (row.get("path") or row.get("image_path") or "").strip()
        if image_path:
            absolute = image_path if os.path.isabs(image_path) else os.path.join(os.path.dirname(manifest_path), image_path)
            if os.path.isfile(absolute):
                file_hash = _sha256(absolute)
                hashes[file_hash] += 1
            else:
                missing_files += 1
        group = (row.get("plant_id") or row.get("session_id") or row.get("group_id") or "").strip()
        if group:
            group_values.add(group)

    duplicate_rows = sum(count - 1 for count in hashes.values() if count > 1)
    return {
        "status": "OBSERVED",
        "evidence": "Counts are computed from the supplied manifest; they are not benchmark claims.",
        "manifest_path": manifest_path,
        "total_samples": len(rows),
        "classes_count": len(labels),
        "class_distribution": dict(labels),
        "quality_metrics": {
            "missing_image_files": missing_files,
            "exact_duplicate_files_observed": duplicate_rows,
            "near_duplicates_removed": None,
            "leakage_risk_score": None,
        },
        "group_fields_observed": bool(group_values),
        "leakage_prevented": False if not group_values else None,
    }


def create_model_cards() -> str:
    """Create a conservative model card from observed artifact metadata.

    No accuracy, F1, latency, dataset size, license, or architecture is asserted
    unless the deployed artifact explicitly supplies that evidence.
    """
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "leaf_disease_ensemble")
    os.makedirs(models_dir, exist_ok=True)
    card_path = os.path.join(models_dir, "model_card.md")
    report = generate_dataset_quality_report()
    card = [
        "# Model Card — AgriSaathi Leaf Disease Vision",
        "",
        "## Evidence status",
        f"- Dataset status: `{report['status']}`",
        f"- Observed samples: `{report['total_samples']}`",
        f"- Observed classes: `{report['classes_count']}`",
        "- Architecture: not asserted here; see the deployed artifact metadata.",
        "- Accuracy / F1 / precision / recall: not reported unless reproduced from a held-out test run.",
        "- Field validation: not established by this repository alone.",
        "",
        "## Intended use",
        "Decision-support experimentation only. A model prediction must not be represented as a confirmed field diagnosis.",
        "",
        "## Reproducibility",
        "The repository must contain the dataset manifest, source provenance, split/group information, training code, and evaluation outputs before benchmark metrics are claimed.",
    ]
    with open(card_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(card) + "\n")
    return card_path


if __name__ == "__main__":
    init_dataset_structure()
    print(json.dumps(generate_dataset_quality_report(), indent=2))
