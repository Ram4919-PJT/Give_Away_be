from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema for all API models."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Reusable timestamp fields."""

    created_at: datetime


class UUIDSchema(BaseSchema):
    """Reusable UUID field."""

    id: UUID