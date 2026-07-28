from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, *, user_id: UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token=token_hash,
            expires_at=expires_at,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_valid_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.token == token_hash,
                RefreshToken.expires_at > datetime.now(UTC),
            )
            .options(
                selectinload(RefreshToken.user).selectinload("role")
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_id(self, token_id: UUID) -> None:
        await self.db.execute(delete(RefreshToken).where(RefreshToken.token_id == token_id))

    async def delete_by_hash(self, token_hash: str) -> None:
        await self.db.execute(delete(RefreshToken).where(RefreshToken.token == token_hash))

    async def delete_all_for_user(self, user_id: UUID) -> None:
        await self.db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))