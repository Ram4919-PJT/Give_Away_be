from pydantic import Field
from app.schemas.common import ORMModel


class RoleBase(ORMModel):
    role_name: str
    description: str | None = Field(default=None, max_length=255)


class RoleCreate(RoleBase):
    pass


class RoleUpdate(ORMModel):
    role_name: str | None = None
    description: str | None = Field(default=None, max_length=255)


class RoleResponse(RoleBase):
    role_id: int