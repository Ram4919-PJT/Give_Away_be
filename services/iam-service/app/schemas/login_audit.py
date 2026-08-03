from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.models.enums import LoginAuditStatus
from app.schemas.common import ORMModel
from app.schemas.validators import validate_ip_address


class LoginAuditCreate(ORMModel):
    user_id: UUID | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    status: LoginAuditStatus

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, value: str | None) -> str | None:
        return validate_ip_address(value)


class LoginAuditResponse(LoginAuditCreate):
    audit_id: UUID
    login_time: datetime