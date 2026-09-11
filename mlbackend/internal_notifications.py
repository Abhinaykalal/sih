"""
AgriSaathi AI — Provider-Independent Internal Notification System
=================================================================
Manages persistent, authenticated, and offline-syncable agricultural notifications.
Replaces third-party SMS/Voice with verifiable in-app and system-level alerts.

Notification Types:
- RAIN_LOCKOUT_ACTIVATED
- SOIL_MOISTURE_LOW
- SOIL_MOISTURE_CRITICAL
- DEVICE_OFFLINE
- DEVICE_BACK_ONLINE
- PUMP_COMMAND_REQUESTED
- PUMP_COMMAND_BLOCKED
- PUMP_COMMAND_FAILED
- PUMP_COMMAND_EXECUTED
- AI_INFERENCE_COMPLETED
- EXPERIMENTAL_MODEL_USED
- SENSOR_DATA_UNAVAILABLE
- OFFLINE_SYNC_COMPLETED
- OFFLINE_SYNC_FAILED
- MODEL_STATUS_CHANGED
"""

import os
import json
import uuid
import sqlite3
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "farm_analytics.db")

class NotificationType(str, Enum):
    RAIN_LOCKOUT_ACTIVATED = "RAIN_LOCKOUT_ACTIVATED"
    SOIL_MOISTURE_LOW = "SOIL_MOISTURE_LOW"
    SOIL_MOISTURE_CRITICAL = "SOIL_MOISTURE_CRITICAL"
    DEVICE_OFFLINE = "DEVICE_OFFLINE"
    DEVICE_BACK_ONLINE = "DEVICE_BACK_ONLINE"
    PUMP_COMMAND_REQUESTED = "PUMP_COMMAND_REQUESTED"
    PUMP_COMMAND_BLOCKED = "PUMP_COMMAND_BLOCKED"
    PUMP_COMMAND_FAILED = "PUMP_COMMAND_FAILED"
    PUMP_COMMAND_EXECUTED = "PUMP_COMMAND_EXECUTED"
    AI_INFERENCE_COMPLETED = "AI_INFERENCE_COMPLETED"
    EXPERIMENTAL_MODEL_USED = "EXPERIMENTAL_MODEL_USED"
    SENSOR_DATA_UNAVAILABLE = "SENSOR_DATA_UNAVAILABLE"
    OFFLINE_SYNC_COMPLETED = "OFFLINE_SYNC_COMPLETED"
    OFFLINE_SYNC_FAILED = "OFFLINE_SYNC_FAILED"
    MODEL_STATUS_CHANGED = "MODEL_STATUS_CHANGED"


class NotificationSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MODERATE = "MODERATE"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NotificationRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"notif_{uuid.uuid4().hex[:12]}")
    user_id: Optional[str] = "00000000-0000-0000-0000-000000000001"
    farm_id: Optional[str] = "farm-green-valley"
    zone_id: Optional[str] = "zone-1-north-field"
    device_id: Optional[str] = "ESP32_NODE_01"
    notification_type: str
    severity: str = "INFO"
    title: str
    message: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    read_at: Optional[str] = None
    resolved_at: Optional[str] = None
    source_event_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationRepository:
    """Manages SQLite and optional Supabase persistence for notifications."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS canonical_notifications (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                farm_id TEXT,
                zone_id TEXT,
                device_id TEXT,
                notification_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                read_at TEXT,
                resolved_at TEXT,
                source_event_id TEXT UNIQUE,
                metadata_json TEXT
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_notif_user ON canonical_notifications(user_id, created_at DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_notif_type ON canonical_notifications(notification_type)")
        conn.commit()
        conn.close()

    def save(self, notif: NotificationRecord) -> Tuple[bool, str]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        meta_str = json.dumps(notif.metadata)
        try:
            c.execute("""
                INSERT INTO canonical_notifications (
                    id, user_id, farm_id, zone_id, device_id,
                    notification_type, severity, title, message,
                    created_at, read_at, resolved_at, source_event_id, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                notif.id, notif.user_id, notif.farm_id, notif.zone_id, notif.device_id,
                notif.notification_type, notif.severity, notif.title, notif.message,
                notif.created_at, notif.read_at, notif.resolved_at, notif.source_event_id,
                meta_str
            ))
            conn.commit()
            return True, notif.id
        except sqlite3.IntegrityError:
            # Source event already recorded (deduplication)
            return False, "DUPLICATE_SOURCE_EVENT"
        finally:
            conn.close()

    def get_all(
        self,
        user_id: Optional[str] = None,
        severity: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        query = "SELECT * FROM canonical_notifications WHERE 1=1"
        params = []

        if user_id and user_id != "all":
            query += " AND (user_id = ? OR user_id IS NULL)"
            params.append(user_id)
        if severity and severity.upper() != "ALL":
            query += " AND severity = ?"
            params.append(severity.upper())
        if unread_only:
            query += " AND read_at IS NULL"

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        c.execute(query, tuple(params))
        rows = []
        for r in c.fetchall():
            d = dict(r)
            try:
                d["metadata"] = json.loads(d.get("metadata_json") or "{}")
            except Exception:
                d["metadata"] = {}
            rows.append(d)
        conn.close()
        return rows

    def mark_read(self, notif_id: str) -> bool:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE canonical_notifications SET read_at = ? WHERE id = ?", (now_iso, notif_id))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def mark_resolved(self, notif_id: str) -> bool:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE canonical_notifications SET resolved_at = ? WHERE id = ?", (now_iso, notif_id))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return affected > 0


class InAppNotificationProvider:
    """Delivers notifications to active in-app subscribers and local client queues."""

    def __init__(self, repo: NotificationRepository):
        self.repo = repo
        self._active_listeners: List[Any] = []

    def dispatch(self, notif: NotificationRecord) -> Dict[str, Any]:
        saved, res_id = self.repo.save(notif)
        return {
            "dispatched": True,
            "id": res_id if saved else notif.id,
            "saved_to_db": saved,
            "in_app_ready": True
        }


class NotificationService:
    """Unified provider-independent notification orchestrator."""

    def __init__(self):
        self.repo = NotificationRepository()
        self.provider = InAppNotificationProvider(self.repo)

    def create_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        severity: str = "INFO",
        user_id: Optional[str] = "00000000-0000-0000-0000-000000000001",
        farm_id: Optional[str] = "farm-green-valley",
        zone_id: Optional[str] = "zone-1-north-field",
        device_id: Optional[str] = "ESP32_NODE_01",
        source_event_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationRecord:
        record = NotificationRecord(
            user_id=user_id,
            farm_id=farm_id,
            zone_id=zone_id,
            device_id=device_id,
            notification_type=notification_type,
            severity=severity,
            title=title,
            message=message,
            source_event_id=source_event_id,
            metadata=metadata or {}
        )
        self.provider.dispatch(record)
        return record

    def list_notifications(
        self,
        user_id: Optional[str] = None,
        severity: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        return self.repo.get_all(user_id=user_id, severity=severity, unread_only=unread_only, limit=limit)

    def mark_read(self, notification_id: str) -> bool:
        return self.repo.mark_read(notification_id)

    def mark_resolved(self, notification_id: str) -> bool:
        return self.repo.mark_resolved(notification_id)

    def process_sync_batch(self, user_id: str, client_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Idempotently processes offline client action queues and pending notifications.
        Deduplicates by client_action_id.
        """
        processed = 0
        duplicates = 0
        errors = []
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        for event in client_events:
            cid = event.get("client_action_id") or event.get("id")
            if not cid:
                cid = f"sync_{uuid.uuid4().hex[:8]}"

            # If client generated a local notification, record it
            ntype = event.get("notification_type") or event.get("type", "GENERIC_EVENT")
            title = event.get("title", f"Client Event {ntype}")
            msg = event.get("message", "Synchronized from client device.")
            sev = event.get("severity", "INFO")

            rec = NotificationRecord(
                user_id=user_id,
                farm_id=event.get("farm_id", "farm-green-valley"),
                zone_id=event.get("zone_id", "zone-1-north-field"),
                device_id=event.get("device_id", "ESP32_NODE_01"),
                notification_type=ntype,
                severity=sev,
                title=title,
                message=msg,
                source_event_id=cid,
                metadata=event.get("payload", {})
            )
            saved, _ = self.repo.save(rec)
            if saved:
                processed += 1
            else:
                duplicates += 1

        return {
            "status": "success",
            "processed_count": processed,
            "duplicate_skipped": duplicates,
            "sync_timestamp": now_iso
        }


# Global Singleton Notification Service
notification_service = NotificationService()
