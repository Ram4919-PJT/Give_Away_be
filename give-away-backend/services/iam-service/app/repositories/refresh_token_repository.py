from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create(
        self,
        *,
        user_id: UUID,
        token: str,
        expires_at: datetime,
    ) -> RefreshToken:
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )

        self.db.add(refresh_token)
        await self.db.flush()
        await self.db.refresh(refresh_token)

        return refresh_token

    async def get_by_id(
        self,
        token_id: UUID,
    ) -> RefreshToken | None:
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.token_id == token_id)
            .options(
                selectinload(RefreshToken.user).selectinload(
                    lambda user: user.role
                )
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_valid_by_token(
        self,
        token: str,
    ) -> RefreshToken | None:
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.token == token,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > datetime.now(UTC),
            )
            .options(
                selectinload(RefreshToken.user).selectinload(
                    lambda user: user.role
                )
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_by_user(
        self,
        user_id: UUID,
    ) -> list[RefreshToken]:
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
            )
            .order_by(RefreshToken.created_at.desc())
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def revoke_by_id(
        self,
        token_id: UUID,
    ) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token_id == token_id)
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
            )
        )

        await self.db.execute(stmt)

    async def revoke_by_token(
        self,
        token: str,
    ) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token == token)
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
            )
        )

        await self.db.execute(stmt)

    async def revoke_all_for_user(
        self,
        user_id: UUID,
    ) -> None:
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
            )
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
            )
        )

        await self.db.execute(stmt)