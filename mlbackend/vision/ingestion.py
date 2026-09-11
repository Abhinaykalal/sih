"""
AgriSaathi Vision Pipeline — Image Ingestion & Deduplication
===========================================================
Scans dataset directories, removes corrupt/empty files, detects MD5 duplicates,
and builds an audited image index without fabricating data.
"""

import os
import hashlib
from typing import Dict, Any, List, Tuple
from PIL import Image

class ImageIngestionEngine:
    """Manages verified image ingestion from disk."""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.images: List[Dict[str, Any]] = []
        self.duplicates_removed = 0
        self.corrupt_removed = 0

    def ingest_directory(self, target_dir: str) -> Dict[str, Any]:
        """Ingests all images in target_dir, checking duplicates and integrity."""
        seen_hashes = set()
        indexed = []

        if not os.path.exists(target_dir):
            return {
                "status": "DIR_NOT_FOUND",
                "total_valid_images": 0,
                "message": f"Target directory {target_dir} does not exist. Awaiting download."
            }

        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    path = os.path.join(root, file)
                    
                    # 1. Integrity check
                    try:
                        with Image.open(path) as img:
                            img.verify()
                    except Exception:
                        self.corrupt_removed += 1
                        continue

                    # 2. Hash-based deduplication
                    with open(path, "rb") as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()

                    if file_hash in seen_hashes:
                        self.duplicates_removed += 1
                        continue
                    
                    seen_hashes.add(file_hash)
                    label = os.path.basename(root)
                    indexed.append({
                        "filepath": path,
                        "filename": file,
                        "label": label,
                        "hash": file_hash
                    })

        self.images = indexed
        return {
            "status": "SUCCESS",
            "total_valid_images": len(indexed),
            "duplicates_removed": self.duplicates_removed,
            "corrupt_removed": self.corrupt_removed,
            "classes_detected": list(set(img["label"] for img in indexed))
        }
