from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CORE_SERVICE_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(CORE_SERVICE_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Core Management Service"
    ENV: str = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8002

    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/core_mgmt_db"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800
    DATABASE_ECHO: bool = False

    JWT_SECRET_KEY: str = "dev-secret-key-minimum-32-characters-long"
    JWT_ALGORITHM: str = "HS256"

    GATEWAY_INTERNAL_URL: str = "http://127.0.0.1:8000"
    INTERNAL_NOTIFICATION_KEY: str = "dev-internal-notification-key-change-in-prod"
    NOTIFICATIONS_ENABLED: bool = True
    ADMIN_NOTIFY_USER_ID: int = 1
    USER_APP_URL: str = "http://localhost:5173"
    ADMIN_PORTAL_URL: str = "http://localhost:5174"

    NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"
    NOMINATIM_USER_AGENT: str = "GiveAway/1.0 (contact@giveaway.org)"
    NOMINATIM_MIN_INTERVAL_SEC: float = 1.1
    NOMINATIM_COUNTRY_CODES: str = "in"
    GEOCODING_TIMEOUT_SEC: float = 12.0

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_CURRENCY: str = "INR"
    PAYMENT_DEV_MODE: bool = True

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    UPLOAD_DIR: str = str(CORE_SERVICE_ROOT.parent.parent / "uploads")
    UPLOAD_URL_PREFIX: str = "/uploads"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS: str = ".jpg,.jpeg,.png,.webp,.pdf"

    # Receiver KYC
    KYC_PROVIDER: str = "MANUAL"
    ALLOW_MOCK_KYC: bool = False
    BANK_VERIFICATION_PROVIDER: str = "MANUAL"
    KYC_HIGH_VALUE_THRESHOLD: float = 100_000.0
    KYC_MEDIUM_VALUE_THRESHOLD: float = 50_000.0
    KYC_MOBILE_OTP_EXPIRE_MINUTES: int = 10
    KYC_MOBILE_OTP_MAX_ATTEMPTS: int = 5
    KYC_MOBILE_OTP_RESEND_COOLDOWN_SEC: int = 60

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

    @property
    def upload_dir(self) -> Path:
        return Path(self.UPLOAD_DIR)

    @property
    def allowed_upload_extensions(self) -> set[str]:
        return {ext.strip().lower() for ext in self.ALLOWED_UPLOAD_EXTENSIONS.split(",") if ext.strip()}


settings = Settings()
