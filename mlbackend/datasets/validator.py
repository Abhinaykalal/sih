"""
AgriSaathi Dataset Validator & Split Generator
==============================================
Validates downloaded datasets, computes SHA-256 checksums, detects duplicate records,
generates missing-value and class distribution reports, and produces leak-free train/val/test splits.
"""

import os
import csv
import json
import hashlib
from typing import Dict, Any, List, Tuple, Optional

class DatasetValidator:
    @staticmethod
    def compute_sha256(file_path: str) -> str:
        """Computes SHA-256 checksum of a file."""
        if not os.path.exists(file_path):
            return "FILE_NOT_FOUND"
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    @staticmethod
    def validate_csv(
        file_path: str,
        required_columns: List[str],
        target_column: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates CSV file: checks required columns, detects duplicates,
        computes missing values and class distributions.
        """
        if not os.path.exists(file_path):
            return {
                "valid": False,
                "error": f"File does not exist: {file_path}",
                "record_count": 0,
                "duplicates_count": 0,
                "missing_values": {},
                "class_distribution": {},
                "checksum": "NONE"
            }

        checksum = DatasetValidator.compute_sha256(file_path)
        rows: List[Dict[str, str]] = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            missing_cols = [c for c in required_columns if c not in headers]
            if missing_cols:
                return {
                    "valid": False,
                    "error": f"Missing required columns: {missing_cols}",
                    "record_count": 0,
                    "checksum": checksum
                }
            for row in reader:
                rows.append(row)

        record_count = len(rows)
        # Duplicate detection using serialized tuple of values
        seen = set()
        duplicates_count = 0
        for r in rows:
            row_tuple = tuple(sorted(r.items()))
            if row_tuple in seen:
                duplicates_count += 1
            else:
                seen.add(row_tuple)

        # Missing values report
        missing_values: Dict[str, int] = {c: 0 for c in headers}
        for r in rows:
            for c in headers:
                val = r.get(c, "").strip()
                if val == "" or val.lower() in {"null", "none", "nan", "na"}:
                    missing_values[c] += 1

        # Class distribution report
        class_distribution: Dict[str, int] = {}
        if target_column and target_column in headers:
            for r in rows:
                lbl = r.get(target_column, "UNKNOWN").strip()
                class_distribution[lbl] = class_distribution.get(lbl, 0) + 1

        return {
            "valid": True,
            "record_count": record_count,
            "duplicates_count": duplicates_count,
            "missing_values": missing_values,
            "class_distribution": class_distribution,
            "checksum": checksum,
            "headers": headers
        }

    @staticmethod
    def create_csv_splits(
        file_path: str,
        splits_dir: str,
        dataset_prefix: str,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42
    ) -> Dict[str, str]:
        """Creates reproducible, disjoint train/val/test CSV splits."""
        import random
        os.makedirs(splits_dir, exist_ok=True)
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = list(csv.DictReader(f))
            if not reader:
                return {}
            headers = reader[0].keys()

        rng = random.Random(seed)
        shuffled = list(reader)
        rng.shuffle(shuffled)

        n = len(shuffled)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)

        splits = {
            "train": shuffled[:train_end],
            "validation": shuffled[train_end:val_end],
            "test": shuffled[val_end:]
        }

        output_paths = {}
        for split_name, split_rows in splits.items():
            path = os.path.join(splits_dir, f"{dataset_prefix}_{split_name}.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(split_rows)
            output_paths[split_name] = path

        # Write split metadata summary
        summary_path = os.path.join(splits_dir, f"{dataset_prefix}_split_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump({
                "dataset": dataset_prefix,
                "seed": seed,
                "total_records": n,
                "train_count": len(splits["train"]),
                "val_count": len(splits["validation"]),
                "test_count": len(splits["test"]),
                "ratios": {"train": train_ratio, "val": val_ratio, "test": test_ratio}
            }, f, indent=2)

        return output_paths
