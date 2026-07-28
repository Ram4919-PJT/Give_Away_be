from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.models.enums import RoleName
from app.schemas.common import ORMModel
from app.schemas.validators import normalize_email, validate_password


class LoginRequest(ORMModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: EmailStr) -> str:
        return normalize_email(value)


class RegisterRequest(ORMModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    mobile: str
    password: str = Field(..., min_length=8, max_length=128)
    role_name: RoleName

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: EmailStr) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return validate_password(value)


class TokenResponse(ORMModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(ORMModel):
    refresh_token: str = Field(..., min_length=20)


class AccessTokenPayload(ORMModel):
    sub: UUID
    role: RoleName
    email: EmailStr


class PasswordResetRequest(ORMModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: EmailStr) -> str:
        return normalize_email(value)


class PasswordResetConfirm(ORMModel):
    otp_code: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password(value)