from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError, RateLimitError
from shared.redis.keys import LOGIN_RATE
from shared.redis.rate_limit import is_rate_limited
from app.core.otp_service import OtpService
from app.core.security.password import hash_password, verify_password
from app.core.token_service import TokenService
from app.events.publishers import EventPublisher
from app.integrations.notification_client import dispatch_email_only, notify_user
from app.models.enums import LoginAuditStatus, OtpPurpose, RoleName, UserStatus
from app.repositories.login_audit_repository import LoginAuditRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AccountPasswordRequest,
    ChangePasswordRequest,
    DeleteAccountRequest,
    LoginAuditEntry,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    SecurityInfoResponse,
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
        self.refresh_repo = RefreshTokenRepository(db)
        self.token_service = TokenService(db)
        self.otp_service = OtpService(db)

    @staticmethod
    def _role_name(value: RoleName | str | None) -> RoleName:
        if value is None:
            return RoleName.DONOR
        if isinstance(value, RoleName):
            return value
        return RoleName(str(value))

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

        user = await self.user_repo.create_from_register(data, int(role.role_id))
        await self.db.commit()
        await self.db.refresh(user)

        await EventPublisher.publish(
            "user.registered",
            {
                "user_id": str(user.user_id),
                "email": user.email,
                "role": data.role_name.value,
                "full_name": user.full_name,
            },
        )

        await notify_user(
            user_id=int(user.user_id),
            title="Welcome to Give Away",
            message="Your account has been created successfully. Start exploring ways to give and receive support.",
            notification_type="ACCOUNT",
            event_type="ACCOUNT_CREATED",
            recipient_email=user.email,
            recipient_name=user.full_name,
            action_url="/dashboard",
            idempotency_key=f"account-created:{user.user_id}",
        )

        return await self.token_service.create_token_pair(user, data.role_name)

    async def login(
        self,
        data: LoginRequest,
        ip_address: str | None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        from gateway.config import settings

        rate_key = LOGIN_RATE.format(email=str(data.email).lower())
        if await is_rate_limited(
            rate_key,
            max_attempts=settings.REDIS_LOGIN_RATE_LIMIT,
            window_seconds=settings.REDIS_LOGIN_RATE_WINDOW,
        ):
            raise RateLimitError("Too many login attempts. Please try again later.")

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

        status_value = (
            user.status.value if hasattr(user.status, "value") else str(user.status)
        )
        if status_value == UserStatus.PENDING.value:
            await self.audit_repo.create(
                user_id=user.user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                status=LoginAuditStatus.FAILED,
            )
            await self.db.commit()
            raise AuthenticationError("Your account is awaiting admin approval")
        if status_value != UserStatus.ACTIVE.value:
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

        role_name = self._role_name(user.role.role_name if user.role else None)
        return await self.token_service.create_token_pair(user, role_name)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        return await self.token_service.refresh_tokens(refresh_token)

    async def logout(self, refresh_token: str) -> None:
        await self.token_service.revoke_refresh_token(refresh_token)

    async def logout_all(self, user_id: int) -> None:
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
        await self.token_service.revoke_all_for_user(int(user.user_id))
        await self.db.commit()

        await dispatch_email_only(
            user_id=int(user.user_id),
            recipient_email=user.email,
            recipient_name=user.full_name,
            event_type="PASSWORD_CHANGED",
            title="Your Give Away password was changed",
            message="Your password was reset successfully.",
            idempotency_key=f"password-reset-complete:{user.user_id}:{int(datetime.now(UTC).timestamp())}",
        )

    async def change_password(self, user_id: int, data: ChangePasswordRequest) -> None:
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

        await notify_user(
            user_id=int(user.user_id),
            title="Password changed",
            message="Your password was changed successfully. If this wasn't you, contact support immediately.",
            notification_type="ACCOUNT",
            event_type="PASSWORD_CHANGED",
            recipient_email=user.email,
            recipient_name=user.full_name,
            action_url="/dashboard",
            idempotency_key=f"password-changed:{user.user_id}:{int(datetime.now(UTC).timestamp())}",
        )

    async def get_security_info(self, user_id: int) -> SecurityInfoResponse:
        last_login = await self.audit_repo.get_last_successful_login(user_id)
        history = await self.audit_repo.get_user_login_history(user_id, limit=10)
        active_sessions = await self.refresh_repo.count_active_for_user(user_id)

        last_login_at = None
        last_login_ip = None
        if last_login:
            last_login_at = last_login.login_time.isoformat()
            last_login_ip = last_login.ip_address

        recent_logins = [
            LoginAuditEntry(
                login_time=row.login_time.isoformat(),
                ip_address=row.ip_address,
                user_agent=row.user_agent,
                status=row.status,
            )
            for row in history
        ]

        return SecurityInfoResponse(
            last_login_at=last_login_at,
            last_login_ip=last_login_ip,
            active_sessions=active_sessions,
            recent_logins=recent_logins,
        )

    async def _verify_account_password(self, user_id: int, password: str):
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Password is incorrect")
        return user

    async def deactivate_account(self, user_id: int, data: AccountPasswordRequest) -> None:
        user = await self._verify_account_password(
            user_id, data.password.get_secret_value()
        )
        await self.user_repo.update_status(user, UserStatus.INACTIVE)
        await self.token_service.revoke_all_for_user(int(user.user_id))
        await self.db.commit()

        await notify_user(
            user_id=int(user.user_id),
            title="Account deactivated",
            message="Your account has been deactivated. Contact support to reactivate.",
            notification_type="ACCOUNT",
            event_type="ACCOUNT_DEACTIVATED",
            recipient_email=user.email,
            recipient_name=user.full_name,
            idempotency_key=f"account-deactivated:{user.user_id}",
        )

    async def delete_account(self, user_id: int, data: DeleteAccountRequest) -> None:
        if data.confirmation.strip().upper() != "DELETE":
            raise AuthenticationError('Type DELETE to confirm account removal')

        user = await self._verify_account_password(
            user_id, data.password.get_secret_value()
        )

        from datetime import UTC, datetime

        stamp = int(datetime.now(UTC).timestamp())
        user.email = f"deleted_{user.user_id}_{stamp}@deleted.local"
        user.mobile = f"deleted{user.user_id}"
        user.full_name = "Deleted User"
        await self.user_repo.update_status(user, UserStatus.INACTIVE)
        await self.token_service.revoke_all_for_user(int(user.user_id))
        await self.db.commit()
