"""
AGRISENTINEL HYBRID DATABASE ENGINE (BUILT FROM SCRATCH)
-------------------------------------------------------
Combines Edge Local Storage (SQLite) + Cloud Sync Protocol into an Offline-First Hybrid Database.
- Zero-latency local reads/writes on edge hardware.
- Automatic background store-and-sync when internet is restored.
"""

import sqlite3
import os
import json
import time
import requests
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "hybrid_farm_edge.db")

class HybridDatabase:
    def __init__(self):
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(DB_PATH)

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Local Farmer Profiles & Farm Zones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmer_profiles (
                farmer_id TEXT PRIMARY KEY,
                name TEXT,
                phone TEXT,
                state TEXT,
                district TEXT,
                created_at INTEGER
            )
        """)

        # Edge Sensor Telemetry Logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_id INTEGER,
                soil_moisture REAL,
                air_temp REAL,
                humidity REAL,
                ec_salinity REAL,
                pest_count INTEGER,
                timestamp INTEGER
            )
        """)

        # Hybrid Offline Sync Queue Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                payload_json TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at INTEGER,
                synced_at INTEGER
            )
        """)

        conn.commit()
        conn.close()

    def log_telemetry(self, zone_id: int, moisture: float, temp: float, humidity: float, ec: float, pests: int):
        """Writes telemetry to local SQLite edge storage with zero latency."""
        now = int(time.time())
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO telemetry_logs (zone_id, soil_moisture, air_temp, humidity, ec_salinity, pest_count, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (zone_id, moisture, temp, humidity, ec, pests, now))

        # Queue event for cloud sync
        payload = json.dumps({
            "zone_id": zone_id,
            "soil_moisture": moisture,
            "air_temp": temp,
            "humidity": humidity,
            "ec_salinity": ec,
            "pest_count": pests,
            "timestamp": now
        })
        cursor.execute("""
            INSERT INTO sync_queue (event_type, payload_json, status, created_at)
            VALUES ('TELEMETRY_LOG', ?, 'PENDING', ?)
        """, (payload, now))

        conn.commit()
        conn.close()

    def get_pending_sync_events(self) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, event_type, payload_json, created_at FROM sync_queue WHERE status = 'PENDING'")
        rows = cursor.fetchall()
        conn.close()

        result = []
        for r in rows:
            result.append({
                "sync_id": r[0],
                "event_type": r[1],
                "payload": json.loads(r[2]),
                "created_at": r[3]
            })
        return result

    def mark_events_synced(self, sync_ids: List[int]):
        now = int(time.time())
        conn = self.get_connection()
        cursor = conn.cursor()
        for sid in sync_ids:
            cursor.execute("UPDATE sync_queue SET status = 'SYNCED', synced_at = ? WHERE id = ?", (now, sid))
        conn.commit()
        conn.close()

    def get_db_stats(self) -> Dict[str, Any]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM telemetry_logs")
        total_logs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sync_queue WHERE status = 'PENDING'")
        pending_sync = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sync_queue WHERE status = 'SYNCED'")
        synced_count = cursor.fetchone()[0]
        conn.close()

        return {
            "database_type": "Hybrid Edge-Cloud Database (Built from Scratch)",
            "total_telemetry_records": total_logs,
            "pending_cloud_syncs": pending_sync,
            "completed_cloud_syncs": synced_count,
            "local_storage_file": "hybrid_farm_edge.db"
        }

# Global Hybrid DB Instance
hybrid_db = HybridDatabase()
