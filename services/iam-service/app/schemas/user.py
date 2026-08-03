from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.models.enums import RoleName, UserStatus
from app.schemas.common import ORMModel
from app.schemas.role import RoleResponse
from app.schemas.validators import (
    normalize_email,
    normalize_full_name,
    normalize_mobile,
    validate_password,
)


class UserBase(ORMModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    mobile: str = Field(..., min_length=10, max_length=15)

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


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    role_name: RoleName

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return validate_password(value)


class UserUpdate(ORMModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    mobile: str | None = Field(default=None, min_length=10, max_length=15)
    status: UserStatus | None = None
    role_name: RoleName | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        return normalize_full_name(value) if value else None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: EmailStr | None) -> str | None:
        return normalize_email(value) if value else None

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str | None) -> str | None:
        return normalize_mobile(value) if value else None


class UserStatusUpdate(ORMModel):
    status: UserStatus


class RoleAssignRequest(ORMModel):
    role_name: RoleName


class UserResponse(UserBase):
    user_id: UUID
    role_id: UUID
    status: UserStatus
    created_at: datetime


class UserWithRoleResponse(UserResponse):
    role: RoleResponse


class UserInDB(UserResponse):
    password_hash: str