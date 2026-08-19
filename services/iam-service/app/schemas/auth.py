from pydantic import EmailStr, Field, SecretStr, field_validator

from app.models.enums import RoleName
from app.schemas.common import BaseSchema
from app.schemas.validators import (
    normalize_email,
    normalize_full_name,
    normalize_mobile,
    validate_password,
)


class RegisterRequest(BaseSchema):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    mobile: str = Field(..., min_length=10, max_length=15)
    password: SecretStr = Field(..., min_length=8, max_length=128)
    role_name: RoleName

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return normalize_full_name(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: EmailStr) -> str:
        return normalize_email(value)

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str) -> str:
        return normalize_mobile(value)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: SecretStr) -> SecretStr:
        validate_password(value.get_secret_value())
        return value


class LoginRequest(BaseSchema):
    email: EmailStr
    password: SecretStr


class LogoutRequest(BaseSchema):
    refresh_token: str = Field(..., min_length=10)


class RefreshTokenRequest(BaseSchema):
    refresh_token: str = Field(..., min_length=10)


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseSchema):
    email: EmailStr


class PasswordResetConfirm(BaseSchema):
    email: EmailStr
    otp_code: str = Field(..., min_length=4, max_length=6)
    new_password: SecretStr = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseSchema):
    current_password: SecretStr
    new_password: SecretStr = Field(..., min_length=8, max_length=128)


class AccountPasswordRequest(BaseSchema):
    password: SecretStr


class DeleteAccountRequest(BaseSchema):
    password: SecretStr
    confirmation: str = Field(..., min_length=4, max_length=64)


class LoginAuditEntry(BaseSchema):
    login_time: str
    ip_address: str | None = None
    user_agent: str | None = None
    status: str


class SecurityInfoResponse(BaseSchema):
    last_login_at: str | None = None
    last_login_ip: str | None = None
    active_sessions: int = 0
    recent_logins: list[LoginAuditEntry] = []
