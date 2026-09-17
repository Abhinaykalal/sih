import pytest
import json
from unittest.mock import MagicMock, patch
from mlbackend.mqtt_service import MQTTServiceManager, parse_and_validate_telemetry_payload
from mlbackend.db_layer import db_layer
from mlbackend.config import settings

@pytest.fixture
def mock_mqtt_manager():
    with patch("paho.mqtt.client.Client") as mock_client:
        manager = MQTTServiceManager()
        manager.client = mock_client()
        yield manager

def test_parse_invalid_payload():
    """Test rejection of malformed or invalid telemetry."""
    ok, record, errors = parse_and_validate_telemetry_payload("not json")
    assert not ok
    assert "JSON parse failure" in errors[0]

    ok, record, errors = parse_and_validate_telemetry_payload({"device_id": None})
    assert not ok
    assert "Missing or invalid 'device_id'" in errors[0]

    ok, record, errors = parse_and_validate_telemetry_payload({"device_id": "ESP32_NODE_01", "telemetry": {"soil_moisture_pct": 150}})
    assert ok  # Packet is parsed, but warning generated
    assert record["ingestion_status"] == "WARNING_OUT_OF_RANGE"
    assert record["telemetry"]["soil_moisture_pct"] is None
    assert any("out of range" in err for err in errors)

def test_mqtt_duplicate_deduplication():
    """Test that db_layer correctly drops duplicate payloads using hashing."""
    payload = {
        "device_id": "ESP32_NODE_01",
        "telemetry": {"soil_moisture_pct": 50}
    }
    ok, record, _ = parse_and_validate_telemetry_payload(payload)
    
    # First insert should succeed
    success1, msg1 = db_layer.store_telemetry_packet(record)
    
    # Second identical insert should be dropped
    success2, msg2 = db_layer.store_telemetry_packet(record)
    assert success2 is False
    assert "DUPLICATE" in msg2

def test_mqtt_reconnect_subscription(mock_mqtt_manager):
    """Test that on_connect properly resubscribes to QoS 1 topics."""
    # Simulate a connect event
    mock_mqtt_manager.on_connect(mock_mqtt_manager.client, None, None, 0)
    
    assert mock_mqtt_manager.connected is True
    # Ensure subscribe was called
    mock_mqtt_manager.client.subscribe.assert_any_call("agrisaathi/nodes/+/telemetry", qos=1)
    mock_mqtt_manager.client.subscribe.assert_any_call("agrisaathi/nodes/+/status", qos=1)

def test_mqtt_disconnect_state(mock_mqtt_manager):
    """Test that disconnect flag is handled correctly."""
    mock_mqtt_manager.connected = True
    mock_mqtt_manager.on_disconnect(mock_mqtt_manager.client, None, 1)
    assert not mock_mqtt_manager.connected

def test_publish_command_qos(mock_mqtt_manager):
    """Test that commands are published with QoS 1 and NOT marked as executed yet."""
    mock_mqtt_manager.connected = True
    res = mock_mqtt_manager.publish_command("ESP32_NODE_01", "PUMP_ON", 60, "Test")
    
    assert res["status"] == "published"
    
    # Check that it actually invoked paho publish with QoS 1
    mock_mqtt_manager.client.publish.assert_called_once()
    args, kwargs = mock_mqtt_manager.client.publish.call_args
    assert args[0] == "agrisaathi/nodes/ESP32_NODE_01/commands"
    assert kwargs.get("qos") == 1
    
    # Verify in DB layer it is marked 'published', not 'executed'
    cmd_record = db_layer.get_command(res["command_id"])
    assert cmd_record is not None
    assert cmd_record["status"] == "published"
    assert cmd_record["executed_at"] is None

def test_handle_status_message(mock_mqtt_manager):
    """Test device lifecycle updates accurately in SQLite."""
    mock_mqtt_manager.handle_status_message("TEST_DEVICE_01", '{"status": "online"}')
    
    lifecycle = mock_mqtt_manager.get_device_lifecycle("TEST_DEVICE_01")
    assert lifecycle is not None
    assert lifecycle["status"] == "online"

    mock_mqtt_manager.handle_status_message("TEST_DEVICE_01", 'offline')
    lifecycle = mock_mqtt_manager.get_device_lifecycle("TEST_DEVICE_01")
    assert lifecycle["status"] == "offline"
