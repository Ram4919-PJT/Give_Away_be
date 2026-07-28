from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.jwt import create_access_token
from app.core.security.refresh import (
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expires_at,
)
from app.models.enums import RoleName
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.schemas.auth import TokenResponse


class TokenService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.refresh_repo = RefreshTokenRepository(db)

    async def create_token_pair(self, user: User, role_name: RoleName) -> TokenResponse:
        access_token = create_access_token(
            user_id=user.user_id,
            email=user.email,
            role=role_name,
        )

        plain_refresh = generate_refresh_token()
        await self.refresh_repo.create(
            user_id=user.user_id,
            token_hash=hash_refresh_token(plain_refresh),
            expires_at=refresh_token_expires_at(),
        )
        await self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=plain_refresh,
        )

    async def refresh_tokens(self, plain_refresh: str) -> TokenResponse:
        stored = await self.refresh_repo.get_valid_by_hash(
            hash_refresh_token(plain_refresh)
        )
        if not stored:
            raise ValueError("Invalid or expired refresh token")

        user = stored.user
        role_name = RoleName(user.role.role_name)

        # rotate refresh token
        await self.refresh_repo.delete_by_id(stored.token_id)

        return await self.create_token_pair(user, role_name)

    async def revoke_refresh_token(self, plain_refresh: str) -> None:
        await self.refresh_repo.delete_by_hash(hash_refresh_token(plain_refresh))
        await self.db.commit()

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        await self.refresh_repo.delete_all_for_user(user_id)
        await self.db.commit()