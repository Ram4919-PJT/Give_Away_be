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

  
    async def create_audit(self, audit: LoginAudit) -> LoginAudit:
        """
        Persist a login audit record.
        """
        return await self.create(audit)


    async def get_by_id(self, audit_id: UUID) -> LoginAudit | None:
        """
        Retrieve a login audit by its primary key.
        """
        stmt = (
            select(LoginAudit)
            .where(LoginAudit.audit_id == audit_id)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_by_user(
        self,
        user_id: UUID,
    ) -> LoginAudit | None:
        """
        Retrieve the most recent login attempt for a user.
        """
        stmt = (
            select(LoginAudit)
            .where(LoginAudit.user_id == user_id)
            .order_by(LoginAudit.login_time.desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_login_history(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[LoginAudit]:
        """
        Retrieve login history for a user.
        """
        stmt = (
            select(LoginAudit)
            .where(LoginAudit.user_id == user_id)
            .order_by(LoginAudit.login_time.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_failed_attempts(
        self,
        user_id: UUID,
    ) -> list[LoginAudit]:
        """
        Retrieve all failed login attempts for a user.
        """
        stmt = (
            select(LoginAudit)
            .where(
                LoginAudit.user_id == user_id,
                LoginAudit.status == LoginAuditStatus.FAILED,
            )
            .order_by(LoginAudit.login_time.desc())
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_failed_attempts_since(
        self,
        user_id: UUID,
        since: datetime,
    ) -> int:
        """
        Count failed login attempts after a given timestamp.

        Useful for:
        - Account lockout
        - Brute-force protection
        - Rate limiting
        """
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

    async def list_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[LoginAudit]:
        """
        Retrieve all login audit records.
        """
        stmt = (
            select(LoginAudit)
            .order_by(LoginAudit.login_time.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_id(
        self,
        audit_id: UUID,
    ) -> bool:
        """
        Delete a login audit by ID.
        """
        audit = await self.get_by_id(audit_id)

        if audit is None:
            return False

        await self.delete(audit)
        return True

    async def delete_older_than(
        self,
        before: datetime,
    ) -> int:
        """
        Delete audit records older than the specified date.

        Intended for scheduled cleanup jobs.
        """
        stmt = (
            delete(LoginAudit)
            .where(LoginAudit.login_time < before)
        )

        result = await self.session.execute(stmt)
        return result.rowcount or 0