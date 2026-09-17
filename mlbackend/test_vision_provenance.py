import os
import json
import hashlib
import joblib
import tempfile
from unittest import mock
from datetime import datetime, timezone
import pytest

from mlbackend.vision_ai_model import LocalVisionAIModel, ARTIFACT_TYPE
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import base64

# Generate a real ephemeral key pair for the test session
_TEST_PRIVATE_KEY = ed25519.Ed25519PrivateKey.generate()
_TEST_PUBLIC_KEY = _TEST_PRIVATE_KEY.public_key()
_TEST_PRIVATE_HEX = _TEST_PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PrivateFormat.Raw,
    encryption_algorithm=serialization.NoEncryption()
).hex()
_TEST_PUBLIC_HEX = _TEST_PUBLIC_KEY.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
).hex()

def setup_mock_env(td):
    # Set the environment variables for crypto_utils
    os.environ["MODEL_SIGNING_PRIVATE_KEY"] = _TEST_PRIVATE_HEX
    os.environ["MODEL_VERIFICATION_PUBLIC_KEYS"] = json.dumps({"v1": _TEST_PUBLIC_HEX})
    os.environ.pop("ENVIRONMENT", None) # Ensure not production by default
    
    model_path = os.path.join(td, "vision_model.joblib")
    meta_path = os.path.join(td, "vision_model_metadata.json")
    manifest_path = os.path.join(td, "vision_manifest.csv")
    
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "model": "dummy_model",
        "classes": ["A", "B"],
        "feature_config": {"feature_length": 123},
        "metrics": {"acc": 1.0}
    }
    joblib.dump(artifact, model_path)
    
    with open(model_path, "rb") as f:
        artifact_hash = hashlib.sha256(f.read()).hexdigest()
        
    with open(manifest_path, "w") as f:
        f.write("image_id,label\n1,A\n")
        
    with open(manifest_path, "rb") as f:
        manifest_hash = hashlib.sha256(f.read()).hexdigest()
        
    payload = {
        "model_version": "v1.0.0-test",
        "artifact": {"sha256": artifact_hash},
        "dataset": {"manifest_sha256": manifest_hash},
        "training_date": datetime.now(timezone.utc).isoformat(),
        "algorithm": "TestAlg",
        "feature_extraction_config": {"feature_length": 123},
        "class_labels": ["A", "B"]
    }
    
    # We must sign the payload using the same canonical method as crypto_utils
    from mlbackend.crypto_utils import sign_metadata
    signature = sign_metadata(payload, key_id="v1")
    metadata = {
        "payload": payload,
        "signature": signature
    }
    
    with open(meta_path, "w") as f:
        json.dump(metadata, f)
        
    return model_path, meta_path, manifest_path, artifact, metadata

def get_patched_model(model_path, meta_path, manifest_path):
    with mock.patch("mlbackend.vision_ai_model.MODEL_PATH", model_path):
        with mock.patch("os.path.join") as mock_join:
            def side_effect(*args):
                if "vision_manifest.csv" in args[-1]: return manifest_path
                if "vision_model_metadata.json" in args[-1]: return meta_path
                return os.path.join_orig(*args)
            os.path.join_orig = os.path.join
            mock_join.side_effect = side_effect
            
            return LocalVisionAIModel()

def test_valid_provenance():
    with tempfile.TemporaryDirectory() as td:
        model_path, meta_path, manifest_path, artifact, metadata = setup_mock_env(td)
        model = get_patched_model(model_path, meta_path, manifest_path)
        assert model.model_data is not None
        assert model.provenance == "VERIFIED"

def test_missing_metadata():
    with tempfile.TemporaryDirectory() as td:
        model_path, meta_path, manifest_path, artifact, metadata = setup_mock_env(td)
        os.remove(meta_path)
        model = get_patched_model(model_path, meta_path, manifest_path)
        assert model.model_data is not None
        assert model.provenance == "UNVERIFIED"

def test_invalid_signature():
    with tempfile.TemporaryDirectory() as td:
        model_path, meta_path, manifest_path, artifact, metadata = setup_mock_env(td)
        
        # Tamper with the payload without resigning
        metadata["payload"]["model_version"] = "v2.0.0-malicious"
        with open(meta_path, "w") as f:
            json.dump(metadata, f)
            
        model = get_patched_model(model_path, meta_path, manifest_path)
        assert model.model_data is None # AUTHENTICITY_FAILURE

def test_missing_signature():
    with tempfile.TemporaryDirectory() as td:
        model_path, meta_path, manifest_path, artifact, metadata = setup_mock_env(td)
        
        # Remove signature wrapper
        with open(meta_path, "w") as f:
            json.dump(metadata["payload"], f)
            
        model = get_patched_model(model_path, meta_path, manifest_path)
        assert model.model_data is not None
        assert model.provenance == "UNVERIFIED"

def test_missing_signature_production():
    with tempfile.TemporaryDirectory() as td:
        model_path, meta_path, manifest_path, artifact, metadata = setup_mock_env(td)
        
        # Enable production
        os.environ["ENVIRONMENT"] = "production"
        
        # Remove signature wrapper
        with open(meta_path, "w") as f:
            json.dump(metadata["payload"], f)
            
        model = get_patched_model(model_path, meta_path, manifest_path)
        assert model.model_data is None # AUTHENTICITY_FAILURE in production
        os.environ.pop("ENVIRONMENT", None)

def test_modified_model_artifact():
    with tempfile.TemporaryDirectory() as td:
        model_path, meta_path, manifest_path, artifact, metadata = setup_mock_env(td)
        
        artifact["classes"] = ["C", "D"]
        joblib.dump(artifact, model_path)
        
        model = get_patched_model(model_path, meta_path, manifest_path)
        assert model.model_data is None # MODEL_INTEGRITY_FAILURE

def test_modified_manifest():
    with tempfile.TemporaryDirectory() as td:
        model_path, meta_path, manifest_path, artifact, metadata = setup_mock_env(td)
        
        with open(manifest_path, "w") as f:
            f.write("image_id,label\n1,B\n")
            
        model = get_patched_model(model_path, meta_path, manifest_path)
        assert model.model_data is None # DATASET_INTEGRITY_FAILURE

def test_invalid_metadata():
    with tempfile.TemporaryDirectory() as td:
        model_path, meta_path, manifest_path, artifact, metadata = setup_mock_env(td)
        
        with open(meta_path, "w") as f:
            f.write("{ INVALID JSON")
            
        model = get_patched_model(model_path, meta_path, manifest_path)
        assert model.model_data is None # INVALID_METADATA

def test_missing_model():
    with mock.patch("os.path.exists", return_value=False):
        model = LocalVisionAIModel()
        assert model.model_data is None
        
        # Ensure diagnose returns strict MODEL_UNAVAILABLE structure, no fake prediction
        with mock.patch("mlbackend.vision_ai_model.validate_leaf_image", return_value={"valid": True, "status": "LEAF_IMAGE_ACCEPTED"}):
            res = model.diagnose(image_bytes=b"dummybytes")
            assert res["status"] == "MODEL_UNAVAILABLE"
            assert res["diagnosis"] is None
            assert res["confidence_pct"] is None
            assert res["provenance"] == "UNAVAILABLE"
