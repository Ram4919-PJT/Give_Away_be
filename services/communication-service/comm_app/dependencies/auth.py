from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from comm_app.core.security.jwt import TokenDecodeError, decode_access_token

bearer_scheme = HTTPBearer(auto_error=True)


@dataclass(frozen=True)
class TokenUser:
    user_id: int
    email: str
    role: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenUser:
    try:
        payload = decode_access_token(credentials.credentials)
        return TokenUser(
            user_id=int(payload["sub"]),
            email=payload.get("email", ""),
            role=payload.get("role", ""),
        )
    except (TokenDecodeError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc


def require_roles(*roles: str):
    allowed = set(roles)

    async def checker(user: TokenUser = Depends(get_current_user)) -> TokenUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return checker
