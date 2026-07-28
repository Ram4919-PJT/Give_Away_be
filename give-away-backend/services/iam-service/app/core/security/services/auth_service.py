from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.password import verify_password
from app.models.enums import LoginAuditStatus, RoleName, UserStatus
from app.repositories.login_audit_repository import LoginAuditRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.token_service import TokenService


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.audit_repo = LoginAuditRepository(db)
        self.token_service = TokenService(db)

    async def register(self, data: RegisterRequest) -> TokenResponse:
        role = await self.role_repo.get_by_name(data.role_name)
        if not role:
            raise ValueError("Invalid role")

        if await self.user_repo.get_by_email(data.email):
            raise ValueError("Email already registered")

        if await self.user_repo.get_by_mobile(data.mobile):
            raise ValueError("Mobile already registered")

        user = await self.user_repo.create_from_register(data, role.role_id)
        await self.db.commit()
        await self.db.refresh(user)

        return await self.token_service.create_token_pair(user, data.role_name)

    async def login(self, data: LoginRequest, ip_address: str | None) -> TokenResponse:
        user = await self.user_repo.get_by_email(data.email)

        if not user or not verify_password(data.password, user.password_hash):
            await self.audit_repo.create(
                user_id=user.user_id if user else None,
                ip_address=ip_address,
                status=LoginAuditStatus.FAILED,
            )
            await self.db.commit()
            raise ValueError("Invalid email or password")

        if user.status != UserStatus.ACTIVE.value:
            await self.audit_repo.create(
                user_id=user.user_id,
                ip_address=ip_address,
                status=LoginAuditStatus.FAILED,
            )
            await self.db.commit()
            raise ValueError("Account is not active")

        await self.audit_repo.create(
            user_id=user.user_id,
            ip_address=ip_address,
            status=LoginAuditStatus.SUCCESS,
        )

        role_name = RoleName(user.role.role_name)
        return await self.token_service.create_token_pair(user, role_name)

    async def logout(self, refresh_token: str) -> None:
        await self.token_service.revoke_refresh_token(refresh_token)

    async def logout_all(self, user_id: UUID) -> None:
        await self.token_service.revoke_all_for_user(user_id)