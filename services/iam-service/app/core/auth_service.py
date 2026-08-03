from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.otp_service import OtpService
from app.core.security.password import hash_password, verify_password
from app.core.token_service import TokenService
from app.events.publishers import EventPublisher
from app.models.enums import LoginAuditStatus, OtpPurpose, RoleName, UserStatus
from app.repositories.login_audit_repository import LoginAuditRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.otp import OtpSendRequest, OtpVerifyRequest


class AuthService:
    PUBLIC_ROLES = {RoleName.DONOR, RoleName.RECEIVER, RoleName.NGO}

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.audit_repo = LoginAuditRepository(db)
        self.token_service = TokenService(db)
        self.otp_service = OtpService(db)

    async def register(self, data: RegisterRequest) -> TokenResponse:
        if data.role_name not in self.PUBLIC_ROLES:
            raise ConflictError("Invalid role for self-registration")

        role = await self.role_repo.get_by_name(data.role_name)
        if not role:
            raise ConflictError("Invalid role")

        if await self.user_repo.get_by_email(str(data.email)):
            raise ConflictError("Email already registered")

        if await self.user_repo.get_by_mobile(data.mobile):
            raise ConflictError("Mobile already registered")

        user = await self.user_repo.create_from_register(data, role.role_id)
        await self.db.commit()
        await self.db.refresh(user)

        await EventPublisher.publish(
            "user.registered",
            {"user_id": str(user.user_id), "email": user.email, "role": data.role_name.value},
        )

        return await self.token_service.create_token_pair(user, data.role_name)

    async def login(
        self,
        data: LoginRequest,
        ip_address: str | None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        user = await self.user_repo.get_by_email(str(data.email))

        if not user or not verify_password(
            data.password.get_secret_value(), user.password_hash
        ):
            await self.audit_repo.create(
                user_id=user.user_id if user else None,
                ip_address=ip_address,
                user_agent=user_agent,
                status=LoginAuditStatus.FAILED,
            )
            await self.db.commit()
            raise AuthenticationError("Invalid email or password")

        if user.status != UserStatus.ACTIVE:
            await self.audit_repo.create(
                user_id=user.user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                status=LoginAuditStatus.FAILED,
            )
            await self.db.commit()
            raise AuthenticationError("Account is not active")

        await self.audit_repo.create(
            user_id=user.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=LoginAuditStatus.SUCCESS,
        )
        await self.db.commit()

        role_name = RoleName(user.role.role_name)
        return await self.token_service.create_token_pair(user, role_name)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        return await self.token_service.refresh_tokens(refresh_token)

    async def logout(self, refresh_token: str) -> None:
        await self.token_service.revoke_refresh_token(refresh_token)

    async def logout_all(self, user_id: UUID) -> None:
        await self.token_service.revoke_all_for_user(user_id)

    async def forgot_password(self, data: PasswordResetRequest) -> None:
        user = await self.user_repo.get_by_email(str(data.email))
        if not user:
            return

        await self.otp_service.send_otp(
            OtpSendRequest(email=str(data.email), purpose=OtpPurpose.PASSWORD_RESET)
        )
        await EventPublisher.publish(
            "password.reset.requested",
            {"user_id": str(user.user_id), "email": user.email},
        )

    async def reset_password(self, data: PasswordResetConfirm) -> None:
        user = await self.user_repo.get_by_email(str(data.email))
        if not user:
            raise AuthenticationError("Invalid reset request")

        await self.otp_service.verify_otp(
            OtpVerifyRequest(
                email=str(data.email),
                otp_code=data.otp_code,
                purpose=OtpPurpose.PASSWORD_RESET,
            )
        )

        await self.user_repo.update_password(
            user,
            hash_password(data.new_password.get_secret_value()),
        )
        await self.token_service.revoke_all_for_user(user.user_id)
        await self.db.commit()

    async def change_password(self, user_id: UUID, data: ChangePasswordRequest) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")

        if not verify_password(
            data.current_password.get_secret_value(), user.password_hash
        ):
            raise AuthenticationError("Current password is incorrect")

        await self.user_repo.update_password(
            user,
            hash_password(data.new_password.get_secret_value()),
        )
        await self.db.commit()
