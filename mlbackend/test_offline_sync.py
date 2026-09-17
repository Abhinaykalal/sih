import pytest
from datetime import datetime, timezone, timedelta
import json
import sqlite3
from mlbackend.db_layer import db_layer, HYBRID_DB_PATH
from fastapi.testclient import TestClient
from mlbackend.main import app

client = TestClient(app)

def test_telemetry_sync_accepted():
    """Telemetry records are accepted without TTL expiration and stored as SYNCED."""
    action_id = "test_telemetry_" + str(datetime.now().timestamp())
    payload = {
        "queuedActions": [
            {
                "client_action_id": action_id,
                "type": "TELEMETRY",
                "payload": {"soilMoisture": 42.0},
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        ],
        "deviceId": "ESP32_NODE_01"
    }

    res = client.post("/api/offline-sync", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["processed_count"] == 1
    assert data["expired_count"] == 0
    assert data["results"][0]["status"] == "SYNCED"
    assert data["results"][0]["record_class"] == "TELEMETRY"

def test_command_sync_within_ttl():
    """Command within 60-second TTL is accepted and SYNCED."""
    action_id = "test_command_valid_" + str(datetime.now().timestamp())
    # Command queued just 10 seconds ago
    queued_time = (datetime.now(timezone.utc) - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    payload = {
        "queuedActions": [
            {
                "client_action_id": action_id,
                "type": "COMMAND_PUMP",
                "payload": {"action": "ON"},
                "timestamp": queued_time
            }
        ],
        "deviceId": "ESP32_NODE_01"
    }

    res = client.post("/api/offline-sync", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["processed_count"] == 1
    assert data["expired_count"] == 0
    assert data["results"][0]["status"] == "SYNCED"
    assert data["results"][0]["record_class"] == "COMMAND"

def test_command_sync_expired():
    """Command older than 60 seconds is rejected and marked EXPIRED."""
    action_id = "test_command_stale_" + str(datetime.now().timestamp())
    # Command queued 2 minutes ago (> 60s TTL)
    queued_time = (datetime.now(timezone.utc) - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    payload = {
        "queuedActions": [
            {
                "client_action_id": action_id,
                "type": "COMMAND_PUMP",
                "payload": {"action": "ON"},
                "timestamp": queued_time
            }
        ],
        "deviceId": "ESP32_NODE_01"
    }

    res = client.post("/api/offline-sync", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["processed_count"] == 0
    assert data["expired_count"] == 1
    assert data["results"][0]["status"] == "REJECTED_STALE_COMMAND"
    
    # Verify in DB
    conn = sqlite3.connect(HYBRID_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT sync_status FROM canonical_sync_queue WHERE client_action_id = ?", (action_id,))
    row = c.fetchone()
    conn.close()
    
    assert row is not None
    assert row[0] == "EXPIRED"

def test_missing_client_action_id_command_rejected():
    """A command without a client_action_id fails pre-flight validation (422 Unprocessable Entity)."""
    payload = {
        "queuedActions": [
            {
                # Missing client_action_id
                "type": "COMMAND_PUMP",
                "payload": {"action": "OFF"},
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        ],
        "deviceId": "ESP32_NODE_01"
    }

    res = client.post("/api/offline-sync", json=payload)
    assert res.status_code == 422
    assert "MUST contain a unique 'client_action_id'" in res.json()["detail"]

def test_idempotent_replay():
    """Replaying the same sync payload is idempotent; does not write twice."""
    action_id = "test_idempotent_" + str(datetime.now().timestamp())
    payload = {
        "queuedActions": [
            {
                "client_action_id": action_id,
                "type": "TELEMETRY",
                "payload": {"humidity": 80.0},
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        ],
        "deviceId": "ESP32_NODE_01"
    }

    # First attempt
    res1 = client.post("/api/offline-sync", json=payload)
    assert res1.json()["processed_count"] == 1

    # Second attempt
    res2 = client.post("/api/offline-sync", json=payload)
    data = res2.json()
    assert data["processed_count"] == 0
    assert data["duplicate_skipped_count"] == 1
    assert data["results"][0]["status"] == "SYNCED_DUPLICATE"

def test_telemetry_and_command_same_batch():
    """A mixed batch correctly processes telemetry while rejecting stale commands."""
    action_id_tel = "test_mixed_tel_" + str(datetime.now().timestamp())
    action_id_cmd = "test_mixed_cmd_" + str(datetime.now().timestamp())
    
    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    payload = {
        "queuedActions": [
            {
                "client_action_id": action_id_tel,
                "type": "TELEMETRY",
                "payload": {"soilMoisture": 30.0},
                "timestamp": stale_time
            },
            {
                "client_action_id": action_id_cmd,
                "type": "COMMAND_PUMP",
                "payload": {"action": "ON"},
                "timestamp": stale_time
            }
        ],
        "deviceId": "ESP32_NODE_01"
    }

    res = client.post("/api/offline-sync", json=payload)
    data = res.json()
    assert res.status_code == 200
    assert data["processed_count"] == 1  # The telemetry
    assert data["expired_count"] == 1    # The stale command
    
    status_map = {r["client_action_id"]: r["status"] for r in data["results"]}
    assert status_map[action_id_tel] == "SYNCED"
    assert status_map[action_id_cmd] == "REJECTED_STALE_COMMAND"
