import pytest
import os
import json
import uuid
import hashlib
from mlbackend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")
META_PATH = os.path.join(os.path.dirname(__file__), "crop_model_metadata.json")

RECOMMEND_URL = "/api/recommend"


def create_dummy_model():
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit([[0, 0, 0, 0, 0, 0, 0]], ["rice"])
    joblib.dump(model, MODEL_PATH)


def setup_valid_metadata():
    create_dummy_model()
    with open(MODEL_PATH, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()

    meta = {
        "model_version": str(uuid.uuid4()),
        "artifact": {
            "filename": "model.joblib",
            "sha256": sha256
        },
        "evaluation": {
            "metric": "accuracy",
            "value": 0.991,
            "test_samples": 500
        },
        "training": {
            "timestamp": "2026-09-17T05:30:00Z",
            "dataset_version": "crop-dataset-v1",
            "random_seed": 42
        }
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f)


def cleanup():
    if os.path.exists(MODEL_PATH):
        os.remove(MODEL_PATH)
    if os.path.exists(META_PATH):
        os.remove(META_PATH)


@pytest.fixture(autouse=True)
def run_around_tests():
    cleanup()
    yield
    cleanup()


def test_missing_metadata():
    create_dummy_model()
    # No metadata created — startup should load model as UNVERIFIED
    import mlbackend.main as main
    import importlib
    importlib.reload(main)

    assert main.crop_model_provenance["status"] == "UNVERIFIED"
    assert main.model is not None


def test_hash_mismatch_blocks_model():
    setup_valid_metadata()
    # Tamper with model artifact
    with open(MODEL_PATH, "ab") as f:
        f.write(b"tamper")

    import mlbackend.main as main
    import importlib
    importlib.reload(main)

    assert main.crop_model_provenance["status"] == "MODEL_INTEGRITY_FAILURE"
    assert main.model is None

    local_client = TestClient(main.app)
    payload = {"N": 90, "P": 42, "K": 43, "temperature": 20.8, "humidity": 82.0, "ph": 6.5, "rainfall": 202.9}
    response = local_client.post(RECOMMEND_URL, json=payload)
    data = response.json()
    assert data["provenance"] == "MODEL_INTEGRITY_FAILURE"
    assert any("tampered" in w for w in data["warnings"])
    assert data["test_accuracy"] is None


def test_valid_model_verified_provenance():
    setup_valid_metadata()

    import mlbackend.main as main
    import importlib
    importlib.reload(main)

    assert main.crop_model_provenance["status"] == "VERIFIED"
    assert main.model is not None

    local_client = TestClient(main.app)
    payload = {"N": 90, "P": 42, "K": 43, "temperature": 20.8, "humidity": 82.0, "ph": 6.5, "rainfall": 202.9}
    response = local_client.post(RECOMMEND_URL, json=payload)
    data = response.json()

    assert data["provenance"] == "VERIFIED"
    assert data["test_accuracy"] == 0.991
    assert data["artifact_hash"] is not None


def test_malformed_metadata_blocks_model():
    setup_valid_metadata()
    # Overwrite with malformed JSON
    with open(META_PATH, "w") as f:
        f.write("{ invalid json")

    import mlbackend.main as main
    import importlib
    importlib.reload(main)

    assert main.crop_model_provenance["status"] == "INVALID_METADATA"
    assert main.model is None

    local_client = TestClient(main.app)
    payload = {"N": 90, "P": 42, "K": 43, "temperature": 20.8, "humidity": 82.0, "ph": 6.5, "rainfall": 202.9}
    response = local_client.post(RECOMMEND_URL, json=payload)
    data = response.json()
    assert data["provenance"] == "INVALID_METADATA"
    assert any("metadata" in w.lower() for w in data["warnings"])
    assert data["test_accuracy"] is None
