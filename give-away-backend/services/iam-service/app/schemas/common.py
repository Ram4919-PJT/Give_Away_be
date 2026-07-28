from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    created_at: datetime | None = None


class UUIDSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def parse_uuid(cls, value: UUID | str) -> UUID:
        return value if isinstance(value, UUID) else UUID(str(value))