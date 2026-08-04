from datetime import datetime
from uuid import UUID

from core_app.models.enums import AssistanceRequestStatus
from core_app.schemas.common import BaseSchema, TimestampSchema


class AssistanceRequestCreate(BaseSchema):
    title: str
    description: str | None = None


class AssistanceRequestResponse(TimestampSchema):
    assistance_request_id: UUID
    receiver_user_id: UUID
    title: str
    description: str | None
    status: AssistanceRequestStatus
