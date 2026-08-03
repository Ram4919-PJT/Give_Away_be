from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import LoginAuditStatus
from app.models.login_audit import LoginAudit
from app.repositories.base import BaseRepository


class LoginAuditRepository(BaseRepository[LoginAudit]):
    model = LoginAudit

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(
        self,
        *,
        user_id: UUID | None,
        ip_address: str | None,
        status: LoginAuditStatus,
        user_agent: str | None = None,
    ) -> LoginAudit:
        audit = LoginAudit(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
        )
        return await super().create(audit)

    async def get_by_id(self, audit_id: UUID) -> LoginAudit | None:
        stmt = select(LoginAudit).where(LoginAudit.audit_id == audit_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> list[LoginAudit]:
        stmt = (
            select(LoginAudit)
            .order_by(LoginAudit.login_time.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_login_history(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[LoginAudit]:
        stmt = (
            select(LoginAudit)
            .where(LoginAudit.user_id == user_id)
            .order_by(LoginAudit.login_time.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_failed_attempts_since(self, user_id: UUID, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(LoginAudit)
            .where(
                LoginAudit.user_id == user_id,
                LoginAudit.status == LoginAuditStatus.FAILED,
                LoginAudit.login_time >= since,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete_older_than(self, before: datetime) -> int:
        stmt = delete(LoginAudit).where(LoginAudit.login_time < before)
        result = await self.session.execute(stmt)
        return result.rowcount or 0
