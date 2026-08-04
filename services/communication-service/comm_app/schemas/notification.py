from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from comm_app.models.enums import NotificationChannel, NotificationStatus


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseSchema):
    notification_id: UUID
    user_id: UUID
    title: str
    body: str
    channel: NotificationChannel
    status: NotificationStatus
    read_at: datetime | None
    created_at: datetime


class NotificationCreate(BaseSchema):
    user_id: UUID
    title: str
    body: str
    channel: NotificationChannel = NotificationChannel.IN_APP


class PreferenceResponse(BaseSchema):
    preference_id: UUID
    user_id: UUID
    channel: NotificationChannel
    is_enabled: bool
    updated_at: datetime


class PreferenceUpdate(BaseSchema):
    channel: NotificationChannel
    is_enabled: bool
