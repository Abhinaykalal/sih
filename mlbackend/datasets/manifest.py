"""
AgriSaathi Dataset Manifest Generator
=====================================
Generates standardized manifest JSON records conforming strictly to the AgriSaathi schema:
{
  "dataset_name": "...",
  "source_url": "...",
  "license": "...",
  "downloaded_at": "...",
  "checksum": "...",
  "record_count": 0,
  "class_count": 0,
  "split_strategy": "...",
  "status": "VERIFIED|PARTIAL|BLOCKED|TEST_ONLY",
  "limitations": []
}
"""

import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

MANIFESTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "datasets",
    "manifests"
)

class DatasetManifestGenerator:
    @staticmethod
    def create_manifest(
        dataset_name: str,
        source_url: str,
        license_name: str,
        checksum: str,
        record_count: int,
        class_count: int,
        split_strategy: str,
        status: str,
        limitations: List[str],
        downloaded_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a standardized manifest dictionary."""
        valid_statuses = {"VERIFIED", "PARTIAL", "BLOCKED", "TEST_ONLY"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status '{status}'. Must be one of {valid_statuses}")

        timestamp = downloaded_at or datetime.now(timezone.utc).isoformat()
        manifest = {
            "dataset_name": dataset_name,
            "source_url": source_url,
            "license": license_name,
            "downloaded_at": timestamp,
            "checksum": checksum,
            "record_count": int(record_count),
            "class_count": int(class_count),
            "split_strategy": split_strategy,
            "status": status,
            "limitations": limitations
        }
        return manifest

    @staticmethod
    def save_manifest(manifest: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Saves manifest to datasets/manifests/ directory."""
        os.makedirs(MANIFESTS_DIR, exist_ok=True)
        if not output_path:
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', manifest["dataset_name"].lower())
            safe_name = re.sub(r'_+', '_', safe_name).strip('_')
            output_path = os.path.join(MANIFESTS_DIR, f"{safe_name}.json")
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        
        return output_path
