from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

COMM_SERVICE_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(COMM_SERVICE_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Communication Service"
    ENV: str = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8003

    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/communication_db"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800
    DATABASE_ECHO: bool = False

    JWT_SECRET_KEY: str = "dev-secret-key-minimum-32-characters-long"
    JWT_ALGORITHM: str = "HS256"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return value

    @property
    def cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return origins or ["*"]

    @property
    def cors_allow_credentials(self) -> bool:
        return "*" not in self.cors_origins


settings = Settings()
