from datetime import datetime
from pydantic import EmailStr, Field

from app.schemas.common import ORMModel
from app.schemas.role import RoleResponse


class UserBase(ORMModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: str
    mobile: str = Field(..., min_length=10, max_length=20)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)
    role_name: str = "DONOR"


class UserUpdate(ORMModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    email: str | None = None
    mobile: str | None = Field(default=None, min_length=10, max_length=20)
    status: str | None = None
    role_name: str | None = None


class UserStatusUpdate(ORMModel):
    status: str


class RoleAssignRequest(ORMModel):
    role_name: str


class UserResponse(UserBase):
    user_id: int
    role_id: int
    status: str
    created_at: datetime


class UserWithRoleResponse(UserResponse):
    role: RoleResponse


class UserInDB(UserResponse):
    password_hash: str