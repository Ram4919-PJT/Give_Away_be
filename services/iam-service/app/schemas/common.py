from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class ORMModel(BaseSchema):
    pass


class TimestampSchema(BaseSchema):
    created_at: datetime


class UUIDSchema(BaseSchema):
    id: UUID
