import pytest
import hmac
import hashlib
import time
from unittest.mock import patch, MagicMock
from mlbackend.pump_controller import PumpCommandController, PumpCommandRequest
from mlbackend.db_layer import db_layer
from mlbackend.config import settings

@pytest.fixture
def mock_db():
    # Setup test device registry
    db_layer.register_device_secret("TEST_NODE", "test_secret_123", "v1")
    yield db_layer

def test_canonical_signature_generation(mock_db):
    """Test that the backend correctly generates canonical HMAC-SHA256 signatures."""
    controller = PumpCommandController()
    
    req = PumpCommandRequest(
        device_id="TEST_NODE",
        command_type="PUMP_ON",
        duration_sec=600
    )
    
    with patch("mlbackend.pump_controller.mqtt_manager") as mock_mqtt:
        result = controller.dispatch(req, actor_id="test_user")
        
        assert result["status"] == "published"
        
        # Verify MQTT publish
        mock_mqtt.client.publish.assert_called_once()
        args, kwargs = mock_mqtt.client.publish.call_args
        
        topic = args[0]
        import json
        payload = json.loads(args[1])
        
        assert topic == "agrisaathi/nodes/TEST_NODE/commands"
        assert payload["device_id"] == "TEST_NODE"
        assert payload["key_id"] == "v1"
        assert payload["command"] == "PUMP_ON"
        assert "sequence" in payload
        assert "nonce" in payload
        assert "signature" in payload
        
        # Recompute signature
        canonical = f"TEST_NODE|v1|{payload['sequence']}|{payload['timestamp']}|{payload['nonce']}|PUMP_ON|600"
        expected_sig = hmac.new(
            b"test_secret_123",
            canonical.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        assert payload["signature"] == expected_sig

def test_ack_cryptographic_verification(mock_db):
    """Test that the backend correctly verifies ACK signatures."""
    controller = PumpCommandController()
    
    sequence = int(time.time() * 1000)
    timestamp = sequence
    
    ack_payload = {
        "device_id": "TEST_NODE",
        "key_id": "v1",
        "sequence": sequence,
        "status": "ACTUATION_ACCEPTED",
        "relay_state": True,
        "timestamp": timestamp
    }
    
    # Generate valid signature
    canonical = f"TEST_NODE|v1|{sequence}|ACTUATION_ACCEPTED|1|{timestamp}"
    valid_sig = hmac.new(
        b"test_secret_123",
        canonical.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    ack_payload["signature"] = valid_sig
    
    # Needs a valid command ID to acknowledge
    cmd_record = {
        "command_id": "cmd_test123",
        "device_id": "TEST_NODE",
        "command_type": "PUMP_ON",
        "status": "published",
        "rain_lockout": 0,
        "reason": "Test",
        "created_at": "2026-01-01T00:00:00Z"
    }
    db_layer.store_command(cmd_record)
    
    assert controller.acknowledge_command("cmd_test123", ack_payload) == True
    
    # Verify sequence advanced
    reg = db_layer.get_device_registry("TEST_NODE")
    assert reg["last_sequence"] == sequence

def test_ack_rejection_invalid_signature(mock_db):
    """Test that the backend rejects tampered ACKs."""
    controller = PumpCommandController()
    
    ack_payload = {
        "device_id": "TEST_NODE",
        "key_id": "v1",
        "sequence": 12345,
        "status": "ACTUATION_ACCEPTED",
        "relay_state": True,
        "timestamp": 1234567890,
        "signature": "invalid_signature_hash"
    }
    
    cmd_record = {
        "command_id": "cmd_test124",
        "device_id": "TEST_NODE",
        "command_type": "PUMP_ON",
        "status": "published",
        "rain_lockout": 0,
        "reason": "Test",
        "created_at": "2026-01-01T00:00:00Z"
    }
    db_layer.store_command(cmd_record)
    
    assert controller.acknowledge_command("cmd_test124", ack_payload) == False
    
    # Verify command status didn't change
    cmd = db_layer.get_command("cmd_test124")
    assert cmd["status"] == "published"
