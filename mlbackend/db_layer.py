"""
AgriSaathi AI — Unified Database Abstraction & Offline Synchronization Layer
============================================================================
Unifies local SQLite caching with cloud Supabase synchronization.
Prevents duplicate telemetry via message hash deduplication.
Enforces client_action_id idempotency across offline batch syncs.

NOTE ON CLOUD SYNC:
Cloud sync (Supabase) is not yet implemented. The `synced_to_cloud` flag exists 
in schema but no Supabase upload worker is wired. `canonical_sync_queue` stores 
records locally for audit but does NOT guarantee cloud delivery. Any Supabase 
integration requires a background worker with its own idempotency key and 
exponential backoff.
"""

import os
import time
import json
import sqlite3
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

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
                error_message TEXT,
                record_class TEXT DEFAULT 'TELEMETRY',
                expires_at TEXT,
                sync_status TEXT DEFAULT 'PENDING',
                conflict_policy TEXT DEFAULT 'LAST_WRITE_WINS',
                retry_count INTEGER DEFAULT 0
            )
        """)
        
        # Schema Migrations (Add new columns if they don't exist)
        try:
            c2.execute("ALTER TABLE canonical_sync_queue ADD COLUMN record_class TEXT DEFAULT 'TELEMETRY'")
            c2.execute("ALTER TABLE canonical_sync_queue ADD COLUMN expires_at TEXT")
            c2.execute("ALTER TABLE canonical_sync_queue ADD COLUMN sync_status TEXT DEFAULT 'PENDING'")
            c2.execute("ALTER TABLE canonical_sync_queue ADD COLUMN conflict_policy TEXT DEFAULT 'LAST_WRITE_WINS'")
            c2.execute("ALTER TABLE canonical_sync_queue ADD COLUMN retry_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Columns already exist

        c2.execute("CREATE INDEX IF NOT EXISTS idx_can_sync_client_action ON canonical_sync_queue(client_action_id)")
        
        c2.execute("""
            CREATE TABLE IF NOT EXISTS pump_commands (
                command_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                command_type TEXT NOT NULL,
                status TEXT NOT NULL,
                rain_lockout INTEGER NOT NULL,
                reason TEXT,
                duration_sec INTEGER,
                created_at TEXT NOT NULL,
                published_at TEXT,
                acknowledged_at TEXT,
                executed_at TEXT,
                failure_reason TEXT,
                idempotency_key TEXT,
                requested_by TEXT,
                acknowledgement_payload TEXT
            )
        """)
        c2.execute("""
            CREATE TABLE IF NOT EXISTS command_idempotency (
                idempotency_key TEXT PRIMARY KEY,
                command_id TEXT NOT NULL
            )
        """)
        c2.execute("""
            CREATE TABLE IF NOT EXISTS device_lifecycle (
                device_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_seen_at TEXT,
                last_online_at TEXT,
                last_offline_at TEXT,
                capabilities_json TEXT
            )
        """)
        c2.execute("""
            CREATE TABLE IF NOT EXISTS device_registry (
                device_id TEXT PRIMARY KEY,
                command_secret TEXT NOT NULL,
                key_id TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                last_sequence INTEGER NOT NULL DEFAULT 0,
                firmware_version TEXT,
                configuration TEXT
            )
        """)
        
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
        Commands are strictly gated by a 60-second TTL to prevent stale actuation.
        """
        conn = sqlite3.connect(HYBRID_DB_PATH)
        c = conn.cursor()
        
        processed_count = 0
        duplicate_count = 0
        expired_count = 0
        results = []

        now = datetime.now(timezone.utc)
        now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        for action in queued_actions:
            client_action_id = action.get("client_action_id") or action.get("action_id")
            
            # 1. Determine Record Class
            event_type = action.get("type", action.get("event_type", "GENERIC_ACTION"))
            record_class = "COMMAND" if "command" in event_type.lower() or action.get("command") else "TELEMETRY"
            
            if not client_action_id:
                if record_class == "COMMAND":
                    # Commands strictly require client_action_id for idempotency
                    results.append({"client_action_id": None, "status": "REJECTED_MISSING_ID", "record_class": record_class})
                    continue
                # Telemetry can fallback
                client_action_id = f"{device_id}_{event_type}_{action.get('timestamp')}_{len(str(action))}"

            payload_str = json.dumps(action.get("payload", action))
            queued_at_str = action.get("timestamp") or action.get("created_at") or now_iso
            
            # Parse queued_at safely
            try:
                queued_at = datetime.fromisoformat(queued_at_str.replace("Z", "+00:00"))
            except ValueError:
                queued_at = now
                
            # Defend against client clock spoofing (future-dated timebomb attacks)
            # If the client claims a timestamp in the future, clamp it to server's `now`.
            if queued_at > now:
                queued_at = now
            
            # 2. Policy Evaluation
            expires_at = None
            sync_status = "PENDING"
            conflict_policy = "LAST_WRITE_WINS"
            
            if record_class == "COMMAND":
                # Strict 60-second TTL for commands
                expires_at_dt = queued_at + timedelta(seconds=60)
                expires_at = expires_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                conflict_policy = "REJECT_IF_EXPIRED"
                
                if now > expires_at_dt:
                    sync_status = "EXPIRED"
                    results.append({
                        "client_action_id": client_action_id,
                        "status": "REJECTED_STALE_COMMAND",
                        "record_class": record_class,
                        "reason": f"Command age exceeded 60s TTL. Queued at {queued_at_str}."
                    })
                    expired_count += 1
                else:
                    sync_status = "SYNCED"
                    results.append({"client_action_id": client_action_id, "status": "SYNCED", "record_class": record_class})
                    processed_count += 1
            else:
                # Telemetry
                sync_status = "SYNCED"
                results.append({"client_action_id": client_action_id, "status": "SYNCED", "record_class": record_class})
                processed_count += 1

            # 3. Store in canonical sync queue
            try:
                c.execute("""
                    INSERT INTO canonical_sync_queue (
                        client_action_id, device_id, event_type, payload_json, created_at,
                        record_class, expires_at, sync_status, conflict_policy, synced
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (client_action_id, device_id, event_type, payload_str, now_iso, 
                      record_class, expires_at, sync_status, conflict_policy))
                conn.commit()
            except sqlite3.IntegrityError:
                # Already processed — idempotent success
                if sync_status == "SYNCED":
                    processed_count -= 1 # Adjust count since we didn't actually process it newly
                    duplicate_count += 1
                
                # We could update the result to indicate DUPLICATE, but for idempotency SYNCED is correct for the client
                for res in results:
                    if res["client_action_id"] == client_action_id and res["status"] == "SYNCED":
                        res["status"] = "SYNCED_DUPLICATE"

        conn.close()

        return {
            "status": "success",
            "device_id": device_id,
            "processed_count": processed_count,
            "duplicate_skipped_count": duplicate_count,
            "expired_count": expired_count,
            "sync_timestamp": now_iso,
            "results": results
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

    # --- Commands DB API ---
    
    def check_idempotency(self, idempotency_key: str) -> Optional[str]:
        conn = sqlite3.connect(HYBRID_DB_PATH)
        c = conn.cursor()
        c.execute("SELECT command_id FROM command_idempotency WHERE idempotency_key = ?", (idempotency_key,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

    def set_idempotency(self, idempotency_key: str, command_id: str):
        conn = sqlite3.connect(HYBRID_DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO command_idempotency (idempotency_key, command_id) VALUES (?, ?)", (idempotency_key, command_id))
        conn.commit()
        conn.close()

    def store_command(self, record: Dict[str, Any]):
        conn = sqlite3.connect(HYBRID_DB_PATH)
        c = conn.cursor()
        ack_payload = json.dumps(record.get("acknowledgement_payload")) if record.get("acknowledgement_payload") else None
        
        c.execute("""
            INSERT OR REPLACE INTO pump_commands (
                command_id, device_id, command_type, status, rain_lockout, reason, duration_sec,
                created_at, published_at, acknowledged_at, executed_at, failure_reason,
                idempotency_key, requested_by, acknowledgement_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get("command_id"), record.get("device_id"), record.get("command_type"), record.get("status"),
            1 if record.get("rain_lockout") else 0, record.get("reason"), record.get("duration_sec"),
            record.get("created_at"), record.get("published_at"), record.get("acknowledged_at"),
            record.get("executed_at"), record.get("failure_reason"), record.get("idempotency_key"),
            record.get("requested_by"), ack_payload
        ))
        conn.commit()
        conn.close()

    def get_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(HYBRID_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM pump_commands WHERE command_id = ?", (command_id,))
        row = c.fetchone()
        conn.close()
        if not row: return None
        d = dict(row)
        d["rain_lockout"] = bool(d["rain_lockout"])
        if d["acknowledgement_payload"]:
            d["acknowledgement_payload"] = json.loads(d["acknowledgement_payload"])
        return d

    def update_command_status(self, command_id: str, updates: Dict[str, Any]):
        conn = sqlite3.connect(HYBRID_DB_PATH)
        c = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [command_id]
        c.execute(f"UPDATE pump_commands SET {set_clause} WHERE command_id = ?", values)
        conn.commit()
        conn.close()

    def get_commands_history(self, device_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(HYBRID_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if device_id:
            c.execute("SELECT * FROM pump_commands WHERE device_id = ? ORDER BY created_at DESC LIMIT ?", (device_id, limit))
        else:
            c.execute("SELECT * FROM pump_commands ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        for d in rows:
            d["rain_lockout"] = bool(d["rain_lockout"])
            if d.get("acknowledgement_payload"):
                try: d["acknowledgement_payload"] = json.loads(d["acknowledgement_payload"])
                except: pass
        return rows

    def update_device_lifecycle(self, device_id: str, status: str, last_seen_at: str, is_online: bool = False, capabilities_json: str = "{}"):
        """Updates the device lifecycle status."""
        conn = sqlite3.connect(HYBRID_DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT status, last_online_at, last_offline_at FROM device_lifecycle WHERE device_id = ?", (device_id,))
        row = c.fetchone()
        
        last_online_at = last_seen_at if is_online else (row[1] if row else None)
        last_offline_at = last_seen_at if not is_online else (row[2] if row else None)
        
        c.execute("""
            INSERT INTO device_lifecycle (device_id, status, last_seen_at, last_online_at, last_offline_at, capabilities_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                status = excluded.status,
                last_seen_at = excluded.last_seen_at,
                last_online_at = excluded.last_online_at,
                last_offline_at = excluded.last_offline_at,
                capabilities_json = CASE WHEN excluded.capabilities_json != '{}' THEN excluded.capabilities_json ELSE device_lifecycle.capabilities_json END
        """, (device_id, status, last_seen_at, last_online_at, last_offline_at, capabilities_json))
        conn.commit()
        conn.close()

    def get_device_lifecycle(self, device_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(HYBRID_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM device_lifecycle WHERE device_id = ?", (device_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            res = dict(row)
            try:
                res["capabilities"] = json.loads(res.get("capabilities_json", "{}"))
            except Exception:
                res["capabilities"] = {}
                
            # Compute last_seen_seconds_ago
            if res.get("last_seen_at"):
                try:
                    dt = datetime.strptime(res["last_seen_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    res["last_seen_seconds_ago"] = max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
                except Exception:
                    res["last_seen_seconds_ago"] = 0
            else:
                res["last_seen_seconds_ago"] = 0
            return res
        return None

    # Device Registry Methods
    def register_device_secret(self, device_id: str, command_secret: str, key_id: str = "v1"):
        """Registers a device secret for command authentication."""
        conn = sqlite3.connect(HYBRID_DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO device_registry (device_id, command_secret, key_id)
            VALUES (?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                command_secret = excluded.command_secret,
                key_id = excluded.key_id
        """, (device_id, command_secret, key_id))
        conn.commit()
        conn.close()

    def get_device_registry(self, device_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(HYBRID_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM device_registry WHERE device_id = ?", (device_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def advance_device_sequence(self, device_id: str, sequence: int) -> bool:
        """Atomically advances the sequence number if the new sequence is greater."""
        conn = sqlite3.connect(HYBRID_DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE device_registry SET last_sequence = ? WHERE device_id = ? AND ? > last_sequence", (sequence, device_id, sequence))
        updated = c.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    # --- Legacy API Compatibility Methods (Migrated from database.py and hybrid_db.py) ---
    def get_pending_sync_count(self) -> int:
        """Counts how many commands/telemetry packets are pending cloud sync."""
        conn = sqlite3.connect(HYBRID_DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM canonical_sync_queue WHERE sync_status = 'PENDING'")
        count = c.fetchone()[0]
        conn.close()
        return count

    def get_all_zones_recent_history(self, limit_per_zone: int = 15) -> Dict[str, List[Dict[str, Any]]]:
        """Returns structured time-series history for all physical zones (Legacy wrapper)."""
        # Note: In the canonical telemetry table, we don't have zone_id. We only have device_id.
        # This is a mock to support legacy callers like the risk engine which expect 4 zones.
        # In a real migration, the caller should be updated, but for now we'll synthesize it.
        history = self.get_telemetry_history(limit=limit_per_zone)
        return {
            "zone_1": history,
            "zone_2": history,
            "zone_3": history,
            "zone_4": history,
        }

    def get_db_stats(self) -> Dict[str, Any]:
        """Returns statistics for the hybrid database (Legacy wrapper)."""
        conn1 = sqlite3.connect(ANALYTICS_DB_PATH)
        c1 = conn1.cursor()
        c1.execute("SELECT COUNT(*) FROM canonical_telemetry")
        total_logs = c1.fetchone()[0]
        conn1.close()

        conn2 = sqlite3.connect(HYBRID_DB_PATH)
        c2 = conn2.cursor()
        c2.execute("SELECT COUNT(*) FROM canonical_sync_queue WHERE sync_status = 'PENDING'")
        pending_sync = c2.fetchone()[0]
        c2.execute("SELECT COUNT(*) FROM canonical_sync_queue WHERE sync_status = 'SYNCED'")
        synced_count = c2.fetchone()[0]
        conn2.close()

        return {
            "database_type": "Hybrid Edge-Cloud Database (Canonical)",
            "total_telemetry_records": total_logs,
            "pending_cloud_syncs": pending_sync,
            "completed_cloud_syncs": synced_count,
            "local_storage_file": "hybrid_farm_edge.db"
        }

    def get_pending_sync_events(self) -> List[Dict[str, Any]]:
        """Gets all pending sync events for the cloud worker (Legacy wrapper)."""
        conn = sqlite3.connect(HYBRID_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT id as sync_id, event_type, payload_json, created_at FROM canonical_sync_queue WHERE sync_status = 'PENDING'")
        rows = c.fetchall()
        conn.close()
        
        result = []
        for r in rows:
            result.append({
                "sync_id": r["sync_id"],
                "event_type": r["event_type"],
                "payload": json.loads(r["payload_json"]),
                "created_at": r["created_at"]
            })
        return result

    def mark_events_synced(self, sync_ids: List[int]):
        """Marks specific events as synced by the cloud worker (Legacy wrapper)."""
        conn = sqlite3.connect(HYBRID_DB_PATH)
        c = conn.cursor()
        for sid in sync_ids:
            c.execute("UPDATE canonical_sync_queue SET sync_status = 'SYNCED', synced = 1 WHERE id = ?", (sid,))
        conn.commit()
        conn.close()

db_layer = DatabaseAbstractionLayer()

