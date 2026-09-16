"""
AgriSaathi Notification Service
Handles:
  1. Telegram Bot alerts (optional external bot alerts)
  2. In-App Canonical Notification Engine (provider-independent, offline-safe)
"""

import os
import requests
from pydantic import BaseModel
from typing import Optional
try:
    from .config import settings
except ImportError:
    from config import settings

try:
    from .internal_notifications import notification_service
except ImportError:
    try:
        from internal_notifications import notification_service
    except ImportError:
        notification_service = None


# ============================================================
# SCHEMAS
# ============================================================

class FarmerContact(BaseModel):
    phone: str                      # E.164 format: +91XXXXXXXXXX
    telegram_chat_id: Optional[str] = None
    name: str = "Farmer"
    lang: str = "hi"

class NotificationPayload(BaseModel):
    farmer: FarmerContact
    alert_type: str                 # "scheme", "disaster", "advisory", "weather"
    title: str
    message: str
    severity: str = "INFO"          # "INFO", "WARNING", "CRITICAL"


# ============================================================
# TELEGRAM BOT SERVICE (Optional external notification)
# ============================================================

def send_telegram_message(chat_id: str, message: str) -> dict:
    """
    Sends a message to a Telegram user via the AgriSaathi Bot.
    Requires TELEGRAM_BOT_TOKEN in environment / config.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN not configured"}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if data.get("ok"):
            return {"success": True, "message_id": data["result"]["message_id"]}
        else:
            return {"success": False, "error": data.get("description", "Unknown")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# IN-APP CANONICAL NOTIFICATION (Provider-Independent)
# ============================================================

def send_in_app_alert(to_phone: str, title: str, message: str, severity: str = "INFO") -> dict:
    """
    Records an in-app canonical alert for the mobile application.
    Replaces 3rd-party paid SMS with persistent, offline-syncable records.
    """
    if notification_service:
        rec = notification_service.create_notification(
            notification_type="SYSTEM_ALERT",
            title=title,
            message=message,
            severity=severity,
            metadata={"recipient_phone": to_phone}
        )
        return {"success": True, "notification_id": rec.id, "channel": "IN_APP"}
    return {"success": False, "error": "Internal notification service offline"}


# ============================================================
# UNIFIED DISPATCHER
# Sends via in-app canonical queue + optional Telegram
# ============================================================

def dispatch_alert(payload: NotificationPayload) -> dict:
    """
    Provider-independent alert dispatcher:
    - In-App: All severities (canonical SQLite queue)
    - Telegram: If telegram_chat_id is configured
    """
    results = {}

    SEVERITY_EMOJIS = {
        "scheme":   "🏛️",
        "disaster": "🚨",
        "advisory": "💡",
        "weather":  "🌦️"
    }
    emoji = SEVERITY_EMOJIS.get(payload.alert_type, "📢")

    # 1. Canonical In-App Notification (Always recorded)
    results["in_app"] = send_in_app_alert(
        to_phone=payload.farmer.phone,
        title=f"{emoji} {payload.title}",
        message=payload.message,
        severity=payload.severity
    )

    # 2. Optional Telegram alert if chat_id provided
    if payload.farmer.telegram_chat_id:
        tg_message = (
            f"<b>{emoji} AgriSaathi Alert — {payload.title}</b>\n\n"
            f"{payload.message}\n\n"
            f"<i>Severity: {payload.severity} | AgriSaathi AI</i>"
        )
        results["telegram"] = send_telegram_message(
            payload.farmer.telegram_chat_id,
            tg_message
        )

    return {
        "dispatched": True,
        "severity": payload.severity,
        "channels_attempted": list(results.keys()),
        "results": results
    }
