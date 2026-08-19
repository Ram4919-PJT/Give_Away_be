from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core_app.core.security.jwt import TokenDecodeError, decode_access_token
from core_app.dependencies.auth import TokenUser

optional_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
) -> TokenUser | None:
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        return TokenUser(
            user_id=int(payload["sub"]),
            email=payload.get("email", ""),
            role=payload.get("role", ""),
        )
    except (TokenDecodeError, ValueError, TypeError, KeyError):
        return None
