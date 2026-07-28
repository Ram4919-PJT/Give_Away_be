from app.db.base import Base
from app.db.session import engine


from app.models.user import User
from app.models.role import Role
from app.models.refresh_token import RefreshToken
from app.models.login_audit import LoginAudit
from app.models.otp_verification import OtpVerification


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)