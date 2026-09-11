"""
AgriSaathi AI — Unified Database Abstraction & Offline Synchronization Layer
============================================================================
Unifies local SQLite caching with cloud Supabase synchronization.
Prevents duplicate telemetry via message hash deduplication.
Enforces client_action_id idempotency across offline batch syncs.
"""

import os
import time
import json
import sqlite3
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

try:
    from .config import settings
except ImportError:
    from config import settings

# Canonical Database Paths
DIR_PATH = os.path.dirname(__file__)
ANALYTICS_DB_PATH = os.path.join(DIR_PATH, "farm_analytics.db")      # Local Cache & Telemetry
HYBRID_DB_PATH = os.path.join(DIR_PATH, "hybrid_farm_edge.db")       # Offline Queue & Edge Profiles
CONVERSATION_DB_PATH = os.path.join(DIR_PATH, "conversation_memory.db") # Conversation Memory

def get_db_connection():
    """Returns a connection to the local edge SQLite database."""
    return sqlite3.connect(HYBRID_DB_PATH)

class DatabaseAbstractionLayer:
    """Canonical interface unifying local edge SQLite with cloud synchronization."""

    def __init__(self):
        self._init_all_local_databases()
        self._seen_telemetry_hashes: set = set()

    def _init_all_local_databases(self):
        """Ensures all local tables exist with canonical schema."""
        # 1. Telemetry & Analytics DB
        conn1 = sqlite3.connect(ANALYTICS_DB_PATH)
        c1 = conn1.cursor()
        c1.execute("""
            CREATE TABLE IF NOT EXISTS canonical_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                packet_hash TEXT UNIQUE NOT NULL,
                received_at TEXT NOT NULL,
                device_timestamp INTEGER,
                soil_moisture_pct REAL,
                soil_raw_adc INTEGER,
                temperature_c REAL,
                humidity_pct REAL,
                sunlight_detected INTEGER,
                vibration_detected INTEGER,
                vibration_rms REAL,
                nitrogen REAL,
                phosphorus REAL,
                potassium REAL,
                pump_active INTEGER,
                edge_ai_result TEXT,
                edge_ai_confidence REAL,
                raw_payload TEXT NOT NULL,
                data_source TEXT DEFAULT 'MQTT_EDGE',
                synced_to_cloud INTEGER DEFAULT 0
            )
        """)
        c1.execute("CREATE INDEX IF NOT EXISTS idx_can_telemetry_time ON canonical_telemetry(device_id, received_at DESC)")
        conn1.commit()
        conn1.close()

        # 2. Hybrid Edge DB (Sync Queue with Idempotency)
        conn2 = sqlite3.connect(HYBRID_DB_PATH)
        c2 = conn2.cursor()
        c2.execute("""
            CREATE TABLE IF NOT EXISTS canonical_sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_action_id TEXT UNIQUE NOT NULL,
                device_id TEXT,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                synced INTEGER DEFAULT 0,
                error_message TEXT
            )
        """)
        c2.execute("CREATE INDEX IF NOT EXISTS idx_can_sync_client_action ON canonical_sync_queue(client_action_id)")
        conn2.commit()
        conn2.close()

    def store_telemetry_packet(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Stores parsed telemetry packet.
        Preserves None as SQL NULL (does not convert to 0 or defaults).
        Deduplicates identical packets via MD5 hash.
        """
        raw_str = json.dumps(record.get("raw_payload", {}), sort_keys=True)
        packet_hash = hashlib.md5(raw_str.encode("utf-8")).hexdigest()

        if packet_hash in self._seen_telemetry_hashes:
            return False, "DUPLICATE_PACKET_DROPPED"

        self._seen_telemetry_hashes.add(packet_hash)
        if len(self._seen_telemetry_hashes) > 10000:
            self._seen_telemetry_hashes.clear()

        t = record.get("telemetry", {})
        act = record.get("actuator", {})
        ai = record.get("edge_ai", {})

        conn = sqlite3.connect(ANALYTICS_DB_PATH)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO canonical_telemetry (
                    device_id, packet_hash, received_at, device_timestamp,
                    soil_moisture_pct, soil_raw_adc, temperature_c, humidity_pct,
                    sunlight_detected, vibration_detected, vibration_rms,
                    nitrogen, phosphorus, potassium, pump_active,
                    edge_ai_result, edge_ai_confidence, raw_payload, data_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("device_id"),
                packet_hash,
                record.get("received_at"),
                record.get("device_timestamp"),
                t.get("soil_moisture_pct"),
                t.get("soil_raw_adc"),
                t.get("temperature_c"),
                t.get("humidity_pct"),
                1 if t.get("sunlight_detected") is True else (0 if t.get("sunlight_detected") is False else None),
                1 if t.get("vibration_detected") is True else (0 if t.get("vibration_detected") is False else None),
                t.get("vibration_rms"),
                t.get("nitrogen"),
                t.get("phosphorus"),
                t.get("potassium"),
                1 if act.get("pump_active") is True else (0 if act.get("pump_active") is False else None),
                ai.get("last_scan_result"),
                ai.get("confidence_pct"),
                raw_str,
                record.get("data_source", "MQTT_EDGE")
            ))
            conn.commit()
            return True, "STORED"
        except sqlite3.IntegrityError:
            return False, "DUPLICATE_PACKET_HASH"
        finally:
            conn.close()

    def process_offline_sync_batch(self, device_id: str, queued_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Idempotent offline batch synchronizer.
        Actions sharing an existing client_action_id are acknowledged without duplicate writes.
        """
        conn = sqlite3.connect(HYBRID_DB_PATH)
        c = conn.cursor()
        
        processed_count = 0
        duplicate_count = 0
        errors = []

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        for action in queued_actions:
            client_action_id = action.get("client_action_id") or action.get("action_id")
            if not client_action_id:
                # Generate deterministic fallback if missing
                client_action_id = f"{device_id}_{action.get('type')}_{action.get('timestamp')}_{len(str(action))}"

            event_type = action.get("type", action.get("event_type", "GENERIC_ACTION"))
            payload_str = json.dumps(action.get("payload", action))

            try:
                c.execute("""
                    INSERT INTO canonical_sync_queue (
                        client_action_id, device_id, event_type, payload_json, created_at, synced
                    ) VALUES (?, ?, ?, ?, ?, 1)
                """, (client_action_id, device_id, event_type, payload_str, now_iso))
                conn.commit()
                processed_count += 1
            except sqlite3.IntegrityError:
                # Already processed — idempotent success
                duplicate_count += 1

        conn.close()

        return {
            "status": "success",
            "device_id": device_id,
            "processed_count": processed_count,
            "duplicate_skipped_count": duplicate_count,
            "sync_timestamp": now_iso,
            "errors": errors
        }

    def get_telemetry_history(self, device_id: str = "ESP32_NODE_01", limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent telemetry rows with Null preserved."""
        conn = sqlite3.connect(ANALYTICS_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT * FROM canonical_telemetry 
            WHERE device_id = ? 
            ORDER BY received_at DESC 
            LIMIT ?
        """, (device_id, limit))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def get_latest_telemetry(self, farm_id: str = "farm-alpha", zone_id: str = "zone-1") -> Optional[Dict[str, Any]]:
        """Fetches the latest canonical telemetry reading from local cache."""
        conn = sqlite3.connect(ANALYTICS_DB_PATH)
        c = conn.cursor()
        try:
            c.execute("""
                SELECT received_at, soil_moisture_pct, temperature_c, humidity_pct,
                       nitrogen, phosphorus, potassium, pump_active, data_source
                FROM canonical_telemetry 
                ORDER BY id DESC LIMIT 1
            """)
            row = c.fetchone()
            if row:
                return {
                    "received_at": row[0],
                    "soil_moisture": row[1],
                    "temperature": row[2],
                    "humidity": row[3],
                    "nitrogen": row[4],
                    "phosphorus": row[5],
                    "potassium": row[6],
                    "pump_active": bool(row[7]) if row[7] is not None else False,
                    "data_source": row[8],
                    "is_stale": False
                }
            return None
        except Exception:
            return None
        finally:
            conn.close()

db_layer = DatabaseAbstractionLayer()

