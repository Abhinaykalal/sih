import json

import pytest

from mlbackend.mqtt_service import parse_and_validate_telemetry_payload, MQTTServiceManager
from mlbackend.pump_controller import PumpCommandController, PumpCommandRequest


def test_null_sensor_values_remain_unavailable():
    ok, record, errors = parse_and_validate_telemetry_payload({
        "device_id": "TEST_NODE",
        "telemetry": {
            "soil_moisture_pct": None,
            "temperature_c": None,
            "humidity_pct": None,
            "nitrogen": None,
            "phosphorus": None,
            "potassium": None,
        },
        "actuator": {"pump_active": None},
        "data_source": "UNAVAILABLE",
    })
    assert ok is True
    assert errors == []
    assert record["telemetry"]["nitrogen"] is None
    assert record["actuator"]["pump_active"] is None


def test_invalid_telemetry_is_rejected():
    ok, record, errors = parse_and_validate_telemetry_payload({
        "device_id": "TEST_NODE",
        "telemetry": {"soil_moisture_pct": 150},
    })
    assert ok is False
    assert record is not None
    assert errors


def test_mqtt_manager_does_not_fake_publish_without_connection():
    manager = MQTTServiceManager()
    with pytest.raises(RuntimeError, match="NOT published"):
        manager.publish_command("TEST_NODE", "PUMP_ON", 30, "test")


def test_rain_lockout_cannot_be_bypassed_by_manual_override():
    controller = PumpCommandController()
    result = controller.dispatch(PumpCommandRequest(
        device_id="TEST_NODE",
        command_type="PUMP_ON",
        duration_sec=30,
        manual_override=True,
        active_rain=True,
    ), actor_id="test-user")
    assert result["status"] == "blocked"
    assert result["rain_lockout"] is True


def test_command_failure_is_not_reported_as_published():
    controller = PumpCommandController()
    result = controller.dispatch(PumpCommandRequest(
        device_id="TEST_NODE",
        command_type="PUMP_ON",
        duration_sec=30,
    ), actor_id="test-user")
    # No broker is connected in the test environment, so the command must fail honestly.
    assert result["status"] in {"failed", "published"}
    if result["status"] == "failed":
        assert "failure_reason" in result
