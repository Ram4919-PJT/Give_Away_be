"""Create tables from ORM models.

Prefer Alembic migrations in production:
    alembic upgrade head
"""

from app.db.base import Base
from app.db.session import engine
from app.models.login_audit import LoginAudit
from app.models.otp_verification import OtpVerification
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User

__all__ = ["User", "Role", "RefreshToken", "LoginAudit", "OtpVerification"]


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
