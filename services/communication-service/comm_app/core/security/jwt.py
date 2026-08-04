from jose import JWTError, jwt

from comm_app.config import settings


class TokenDecodeError(Exception):
    pass


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            raise TokenDecodeError("Invalid token type")
        return payload
    except JWTError as exc:
        raise TokenDecodeError("Invalid or expired token") from exc
