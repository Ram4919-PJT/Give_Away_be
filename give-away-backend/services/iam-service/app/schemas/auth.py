from pydantic import EmailStr, Field, SecretStr

from app.schemas.common import BaseSchema


class RegisterRequest(BaseSchema):
    full_name: str = Field(
        ...,
        min_length=3,
        max_length=255,
    )

    email: EmailStr

    mobile: str = Field(
        ...,
        min_length=10,
        max_length=15,
        pattern=r"^\+?[1-9]\d{9,14}$",
    )

    password: SecretStr = Field(
        ...,
        min_length=8,
        max_length=128,
    )


class LoginRequest(BaseSchema):
    email: EmailStr

    password: SecretStr


class LogoutRequest(BaseSchema):
    refresh_token: str = Field(
        ...,
        min_length=10,
    )


class PasswordResetRequest(BaseSchema):
    email: EmailStr


class PasswordResetConfirm(BaseSchema):
    token: str

    new_password: SecretStr = Field(
        ...,
        min_length=8,
        max_length=128,
    )


class ChangePasswordRequest(BaseSchema):
    current_password: SecretStr

    new_password: SecretStr = Field(
        ...,
        min_length=8,
        max_length=128,
    )