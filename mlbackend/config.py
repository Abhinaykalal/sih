import os
from typing import List
from pydantic_settings import BaseSettings


def _csv_env(name: str, default: str = "") -> List[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


class Settings(BaseSettings):
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")

    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "8883"))
    MQTT_USERNAME: str = os.getenv("MQTT_USERNAME", "")
    MQTT_PASSWORD: str = os.getenv("MQTT_PASSWORD", "")
    MQTT_USE_TLS: bool = os.getenv("MQTT_USE_TLS", "true").lower() in ("true", "1", "yes")
    MQTT_CA_CERT: str = os.getenv("MQTT_CA_CERT", "")
    MQTT_CLIENT_CERT: str = os.getenv("MQTT_CLIENT_CERT", "")
    MQTT_CLIENT_KEY: str = os.getenv("MQTT_CLIENT_KEY", "")
    MQTT_WS_PORT: int = int(os.getenv("MQTT_WS_PORT", "8083"))
    MQTT_UPLINK_TOPIC: str = os.getenv("MQTT_UPLINK_TOPIC", "agrisaathi/nodes/{device_id}/telemetry")
    MQTT_DOWNLINK_TOPIC: str = os.getenv("MQTT_DOWNLINK_TOPIC", "agrisaathi/nodes/{device_id}/commands")
    MQTT_STATUS_TOPIC: str = os.getenv("MQTT_STATUS_TOPIC", "agrisaathi/nodes/{device_id}/status")

    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    CORS_ALLOWED_ORIGINS: List[str] = _csv_env(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    ENFORCE_JWT_AUTH: bool = os.getenv("ENFORCE_JWT_AUTH", "true").lower() in ("true", "1", "yes")
    DEV_MODE: bool = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")
    DEV_ALLOW_INSECURE_AUTH: bool = os.getenv("DEV_ALLOW_INSECURE_AUTH", "false").lower() in ("true", "1", "yes")

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    OLLAMA_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))

    MODEL_PATH: str = os.getenv("MODEL_PATH", "model.joblib")
    PORT: int = int(os.getenv("PORT", "8000"))

    class Config:
        env_file = ".env"
        extra = "allow"

    def __init__(self, **values):
        super().__init__(**values)
        if "*" in self.CORS_ALLOWED_ORIGINS:
            raise ValueError("CORS_ALLOWED_ORIGINS must not contain '*'.")
        if self.DEV_ALLOW_INSECURE_AUTH and not self.DEV_MODE:
            raise ValueError("DEV_ALLOW_INSECURE_AUTH requires DEV_MODE=true.")
        if self.MQTT_USE_TLS and self.MQTT_BROKER_PORT == 1883:
            raise ValueError("MQTT TLS is enabled but port 1883 is plaintext; configure a TLS broker port.")


settings = Settings()
