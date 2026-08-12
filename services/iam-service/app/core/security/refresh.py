import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from app.config import settings


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_token_expires_at() -> datetime:
    # Models use TIMESTAMP WITHOUT TIME ZONE; store naive UTC.
    return datetime.now(UTC).replace(tzinfo=None) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )