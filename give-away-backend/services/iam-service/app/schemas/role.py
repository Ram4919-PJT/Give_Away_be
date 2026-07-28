from uuid import UUID

from pydantic import Field, field_validator

from app.models.enums import RoleName
from app.schemas.common import ORMModel


class RoleBase(ORMModel):
    role_name: RoleName
    description: str | None = Field(default=None, max_length=255)


class RoleCreate(RoleBase):
    pass


class RoleUpdate(ORMModel):
    role_name: RoleName | None = None
    description: str | None = Field(default=None, max_length=255)


class RoleResponse(RoleBase):
    role_id: UUID