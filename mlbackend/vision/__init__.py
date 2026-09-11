"""
AgriSaathi Vision AI Package
============================
Modules:
- manifest: Dataset provenance and integrity auditing
- ingestion: Scans disk and removes corrupt / duplicate files
- split: GroupKFold leakage-safe splitting (70/15/15)
- preprocessing: Calibrated color and texture extraction
- training: Calibrated VotingClassifier ensemble
- evaluation: Honest confusion matrix and per-class metrics
- inference: Unclamped transparent prediction engine
- test_fixture: CI/CD test dataset and artifact generator
"""

from .manifest import DatasetManifest, get_standard_manifest
from .ingestion import ImageIngestionEngine
from .split import disjoint_stratified_split
from .preprocessing import extract_features_from_image_bytes
from .training import train_vision_ensemble
from .evaluation import evaluate_model_performance
from .inference import run_vision_inference, VisionPredictionOutput
from .test_fixture import generate_and_train_test_fixture
