import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ── Supabase ───────────────────────────────────────────────
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "agrisaathi-dev-jwt-secret-do-not-use-in-production")
    
    # ── MQTT Configuration ─────────────────────────────────────
    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "broker.hivemq.com")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
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
    CORS_ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.100:3000",
        "https://agrisaathi.vercel.app"
    ]
    ENFORCE_JWT_AUTH: bool = os.getenv("ENFORCE_JWT_AUTH", "false").lower() in ("true", "1", "yes")

    # ── Internal ───────────────────────────────────────────────
    MODEL_PATH: str = "model.joblib"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
