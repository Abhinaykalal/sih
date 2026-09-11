"""
AgriSaathi Vision Pipeline — Dataset Manifest & Provenance Schema
================================================================
Tracks dataset origin, licensing, integrity hashes, and class distributions.
Prevents unverified datasets from entering training pipelines.
"""

import os
import json
import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class DatasetSourceInfo(BaseModel):
    name: str
    source_url: str
    license: str
    citation: str
    expected_sample_count: int
    verified: bool = False

class DatasetManifest(BaseModel):
    dataset_name: str = "AgriSaathi Crop Pathology Benchmark"
    version: str = "1.0.0"
    created_at: str = "2026-09-11"
    sources: List[DatasetSourceInfo] = Field(default_factory=list)
    classes: List[str] = Field(default_factory=list)
    split_strategy: str = "Disjoint Plant/Session Level (70% Train, 15% Val, 15% Test)"
    file_hashes: Dict[str, str] = Field(default_factory=dict)
    total_images: int = 0
    is_test_fixture: bool = False
    validation_status: str = "PENDING_VERIFICATION"

def get_standard_manifest() -> DatasetManifest:
    """Returns official benchmark manifest schema for PlantVillage & ICAR datasets."""
    return DatasetManifest(
        dataset_name="AgriSaathi Paddy & Leaf Pathology Verified Set",
        version="1.0.0",
        sources=[
            DatasetSourceInfo(
                name="PlantVillage Open Crop Disease Dataset",
                source_url="https://github.com/spMohanty/PlantVillage-Dataset",
                license="CC BY-SA 4.0",
                citation="Hughes, D. & Salathe, M. (2015). An open access repository of images on plant health to enable the development of mobile disease diagnostics.",
                expected_sample_count=54306,
                verified=False
            ),
            DatasetSourceInfo(
                name="ICAR Field Diagnostic Pathology Library",
                source_url="https://icar-nrri.in/research",
                license="Government Open Data License - India (GODL)",
                citation="ICAR National Rice Research Institute, Cuttack.",
                expected_sample_count=3500,
                verified=False
            )
        ],
        classes=[
            "Rice Brown Spot (Bipolaris oryzae)",
            "Rice Blast (Magnaporthe oryzae)",
            "Bacterial Leaf Blight (Xanthomonas oryzae)",
            "Healthy Paddy Leaf",
            "Tomato Early Blight",
            "Tomato Late Blight",
            "Healthy Tomato Leaf"
        ],
        split_strategy="Plant and Session GroupKFold Disjoint Split (Zero Leakage)",
        is_test_fixture=False,
        validation_status="PENDING_IMAGE_DOWNLOAD"
    )

def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of an image file for integrity auditing."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()
