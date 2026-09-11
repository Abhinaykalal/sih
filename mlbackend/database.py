import sqlite3
import os
import time
from typing import Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(__file__), "farm_analytics.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Telemetry logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id INTEGER,
            soil_moisture REAL,
            soil_temp REAL,
            air_temp REAL,
            humidity REAL,
            ec_salinity REAL,
            pest_count INTEGER,
            timestamp INTEGER
        )
    """)
    
    # Zone states
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zone_states (
            zone_id INTEGER PRIMARY KEY,
            status TEXT,
            primary_risk TEXT,
            recommended_action TEXT,
            moisture REAL,
            temp REAL,
            updated_at INTEGER
        )
    """)
    
    # Offline sync queue
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS offline_sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            payload TEXT,
            created_at INTEGER,
            synced INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()

def log_telemetry(zone_id: int, soil_moisture: float, soil_temp: float, air_temp: float, humidity: float, ec: float, pest_count: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO telemetry (zone_id, soil_moisture, soil_temp, air_temp, humidity, ec_salinity, pest_count, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (zone_id, soil_moisture, soil_temp, air_temp, humidity, ec, pest_count, int(time.time())))
    conn.commit()
    conn.close()

def get_telemetry_history(zone_id: int = 1, limit: int = 30) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT zone_id, soil_moisture, soil_temp, air_temp, humidity, ec_salinity, pest_count, timestamp
        FROM telemetry WHERE zone_id = ? ORDER BY timestamp DESC LIMIT ?
    """, (zone_id, limit))
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for r in reversed(rows):
        result.append({
            "zone_id": r[0],
            "soil_moisture": r[1],
            "soil_temp": r[2],
            "air_temp": r[3],
            "humidity": r[4],
            "ec_salinity": r[5],
            "pest_count": r[6],
            "timestamp": r[7]
        })
    return result

def queue_offline_event(event_type: str, payload_json: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO offline_sync_queue (event_type, payload, created_at, synced)
        VALUES (?, ?, ?, 0)
    """, (event_type, payload_json, int(time.time())))
    conn.commit()
    conn.close()

def get_pending_sync_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM offline_sync_queue WHERE synced = 0")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_zones_recent_history(limit_per_zone: int = 15) -> Dict[str, List[Dict[str, Any]]]:
    """Returns structured time-series history for all 4 physical zones."""
    return {
        "zone_1": get_telemetry_history(zone_id=1, limit=limit_per_zone),
        "zone_2": get_telemetry_history(zone_id=2, limit=limit_per_zone),
        "zone_3": get_telemetry_history(zone_id=3, limit=limit_per_zone),
        "zone_4": get_telemetry_history(zone_id=4, limit=limit_per_zone),
    }

def seed_initial_telemetry_if_empty():
    """Seeds realistic historical time-series if SQLite database is empty."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM telemetry")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        now = int(time.time())
        # Seed 12 hourly intervals
        for i in range(12, 0, -1):
            t = now - (i * 3600)
            # Zone 1: Baseline paddy
            log_telemetry(zone_id=1, soil_moisture=46.0 - (i % 3), soil_temp=26.0, air_temp=30.0 + (i % 4), humidity=65.0, ec=1.1, pest_count=4)
            # Zone 2: Drying tomato (water stress trend: 32% down to 16%)
            m2 = round(max(14.0, 30.0 - (12 - i) * 1.2), 1)
            log_telemetry(zone_id=2, soil_moisture=m2, soil_temp=28.0, air_temp=34.0, humidity=50.0, ec=1.2, pest_count=6)
            # Zone 3: Cotton pest acceleration (4 -> 7 -> 13 -> 25)
            p3 = int(min(28, 4 + ((12 - i) ** 1.3)))
            log_telemetry(zone_id=3, soil_moisture=38.0, soil_temp=27.0, air_temp=33.0, humidity=70.0, ec=1.0, pest_count=p3)
            # Zone 4: Maize high humidity (80% up to 92%)
            h4 = round(min(95.0, 78.0 + ((12 - i) * 1.1)), 1)
            log_telemetry(zone_id=4, soil_moisture=42.0, soil_temp=25.0, air_temp=29.0, humidity=h4, ec=1.3, pest_count=8)

init_db()
seed_initial_telemetry_if_empty()
