from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.config import settings
from app.models.enums import RoleName


class TokenDecodeError(Exception):
    pass


def create_access_token(
    *,
    user_id: int,
    email: str,
    role: RoleName | str,
) -> str:
    now = datetime.now(UTC)
    role_value = role.value if isinstance(role, RoleName) else str(role)
    payload = {
        "sub": str(int(user_id)),
        "email": email,
        "role": role_value,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            raise TokenDecodeError("Invalid token type")
        # Normalize sub so callers can safely int()-cast bigint user ids.
        if "sub" in payload:
            payload["sub"] = str(payload["sub"])
        return payload
    except JWTError as exc:
        raise TokenDecodeError(f"Invalid or expired token: {exc}") from exc