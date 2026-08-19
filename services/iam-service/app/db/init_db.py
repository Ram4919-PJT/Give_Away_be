"""Create tables from ORM models (test-only).

Production and development schema must be managed with Alembic:

    cd services/iam-service
    alembic upgrade head

To use create_all in isolated tests, set IAM_ALLOW_CREATE_ALL_FOR_TESTS=1.
"""

from __future__ import annotations

import os

from app.db.base import Base
from app.db.session import engine
from app.models.login_audit import LoginAudit
from app.models.otp_verification import OtpVerification
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User

__all__ = ["User", "Role", "RefreshToken", "LoginAudit", "OtpVerification"]

_ALLOW_CREATE_ALL_ENV = "IAM_ALLOW_CREATE_ALL_FOR_TESTS"


def _create_all_guard() -> None:
    if os.environ.get(_ALLOW_CREATE_ALL_ENV) != "1":
        raise RuntimeError(
            "init_db() is disabled for schema management. "
            "Use Alembic migrations instead: alembic upgrade head. "
            f"Set {_ALLOW_CREATE_ALL_ENV}=1 only in isolated test fixtures."
        )


async def init_db() -> None:
    _create_all_guard()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
