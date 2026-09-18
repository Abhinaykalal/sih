import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ── Supabase ───────────────────────────────────────────────
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    
    # ── MQTT Configuration ─────────────────────────────────────
    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "broker.hivemq.com")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    ALLOW_INSECURE_MQTT: bool = os.getenv("ALLOW_INSECURE_MQTT", "false").lower() in ("true", "1", "yes")
    ENABLE_HTTP_SENSOR_FALLBACK: bool = os.getenv("ENABLE_HTTP_SENSOR_FALLBACK", "false").lower() in ("true", "1", "yes")
    MQTT_USERNAME: str = os.getenv("MQTT_USERNAME", "")
    MQTT_PASSWORD: str = os.getenv("MQTT_PASSWORD", "")
    MQTT_USE_TLS: bool = os.getenv("MQTT_USE_TLS", "false").lower() in ("true", "1", "yes")
    MQTT_CA_CERT: str = os.getenv("MQTT_CA_CERT", "")
    MQTT_CLIENT_CERT: str = os.getenv("MQTT_CLIENT_CERT", "")
    MQTT_CLIENT_KEY: str = os.getenv("MQTT_CLIENT_KEY", "")
    MQTT_WS_PORT: int = int(os.getenv("MQTT_WS_PORT", "8083"))
    MQTT_UPLINK_TOPIC: str = os.getenv("MQTT_UPLINK_TOPIC", "agrisaathi/nodes/ESP32_NODE_01/telemetry")
    MQTT_DOWNLINK_TOPIC: str = os.getenv("MQTT_DOWNLINK_TOPIC", "agrisaathi/nodes/ESP32_NODE_01/commands")
    MQTT_STATUS_TOPIC: str = os.getenv("MQTT_STATUS_TOPIC", "agrisaathi/nodes/ESP32_NODE_01/status")

    # ── Weather (OpenWeatherMap free tier — 60 calls/min) ──────
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")

    # ── Telegram (optional — bot alerts) ──────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # ── Security & CORS ────────────────────────────────────────
    ENFORCE_JWT_AUTH: bool = os.getenv("ENFORCE_JWT_AUTH", "false" if "PYTEST_CURRENT_TEST" in os.environ else "true").lower() in ("true", "1", "yes")
    CORS_ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.100:3000",
        "https://agrisaathi.vercel.app"
    ]

    # ── Ollama LLM Configuration ──────────────────────────────
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    OLLAMA_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))

    # ── Internal ───────────────────────────────────────────────
    MODEL_PATH: str = "model.joblib"
    PORT: int = 8000

    # ---------------------------------------------------------
    # Data Freshness Thresholds (Architecture Remediation Phase 0)
    # ---------------------------------------------------------
    # LIVE: Data ≤ TELEMETRY_LIVE_THRESHOLD_SECONDS (actively communicating device)
    TELEMETRY_LIVE_THRESHOLD_SECONDS: int = int(os.getenv("TELEMETRY_LIVE_THRESHOLD_SECONDS", "600"))  # 10 minutes
    
    # STALE: Data > LIVE but ≤ TELEMETRY_STALE_THRESHOLD_SECONDS (device may have disconnected)
    TELEMETRY_STALE_THRESHOLD_SECONDS: int = int(os.getenv("TELEMETRY_STALE_THRESHOLD_SECONDS", "3600"))  # 60 minutes (reduced from 6 hours)
    
    # OFFLINE: Data > STALE (device unreachable)
    # (no threshold needed — anything older than STALE is OFFLINE)
    
    # Device State Auto-Computation (based on telemetry age)
    # REGISTERED: Device created, no telemetry received yet
    # ONLINE: Telemetry ≤ TELEMETRY_LIVE_THRESHOLD_SECONDS
    # STALE: Telemetry > LIVE but ≤ TELEMETRY_STALE_THRESHOLD_SECONDS
    # OFFLINE: Telemetry > TELEMETRY_STALE_THRESHOLD_SECONDS
    # ERROR: Device reported error state

    # ---------------------------------------------------------
    # Command Edge Cryptography
    # ---------------------------------------------------------
    EDGE_COMMAND_SECRET: str = os.getenv("EDGE_COMMAND_SECRET", "change_me_in_production_edge_secret")

    class Config:
        env_file = ".env"
        extra = "allow"

_DEFAULT_SECRET = "change_me_in_production_edge_secret"

settings = Settings()

# Fail fast if production is running with the default HMAC key.
# This key is publicly known (it's in source), so any command signed with it
# can be forged by anyone who has read this file.
_env = os.getenv("ENVIRONMENT", "").lower()
if _env == "production" and settings.EDGE_COMMAND_SECRET == _DEFAULT_SECRET:
    raise RuntimeError(
        "[SECURITY] EDGE_COMMAND_SECRET is set to the default value in a production environment. "
        "Set a strong random secret via the EDGE_COMMAND_SECRET environment variable before starting."
    )
