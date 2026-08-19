from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GATEWAY_HOST: str = "0.0.0.0"
    GATEWAY_PORT: int = 8000
    GATEWAY_RELOAD: bool = True

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True

    REDIS_LOGIN_RATE_LIMIT: int = 5
    REDIS_LOGIN_RATE_WINDOW: int = 900
    REDIS_OTP_RATE_LIMIT: int = 3
    REDIS_OTP_RATE_WINDOW: int = 600

    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:5174,"
        "http://127.0.0.1:5174,"
        "http://localhost:8081,"
        "http://127.0.0.1:8081"
    )

    @property
    def cors_origins(self) -> list[str]:
        origins = [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]
        return origins or ["*"]

    @property
    def cors_allow_credentials(self) -> bool:
        return "*" not in self.cors_origins


settings = GatewaySettings()
