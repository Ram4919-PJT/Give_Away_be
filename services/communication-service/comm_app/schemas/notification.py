from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseSchema):
    notification_id: int
    user_id: int
    notification_type: str
    title: str
    message: str
    status: str
    related_entity_type: str | None = None
    related_entity_id: int | None = None
    action_url: str | None = None
    read_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class NotificationSummary(BaseSchema):
    all: int = 0
    unread: int = 0
    donations: int = 0
    campaigns: int = 0
    account: int = 0
    applications: int = 0


class NotificationListResponse(BaseSchema):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int
    summary: NotificationSummary


class NotificationCreate(BaseSchema):
    user_id: int
    title: str = Field(max_length=150)
    message: str
    notification_type: str = "ACCOUNT"
    related_entity_type: str | None = None
    related_entity_id: int | None = None
    action_url: str | None = None


class InternalNotificationCreate(NotificationCreate):
    event_type: str | None = None
    recipient_email: str | None = None
    recipient_name: str | None = None
    template_data: dict | None = None
    idempotency_key: str | None = None
    send_in_app: bool = True
    send_email: bool = True


class EmailOnlyDispatch(BaseSchema):
    user_id: int | None = None
    recipient_email: str | None = None
    recipient_name: str | None = None
    event_type: str
    notification_type: str = "ACCOUNT"
    title: str = Field(max_length=150)
    message: str
    template_data: dict | None = None
    related_entity_type: str | None = None
    related_entity_id: int | None = None
    action_url: str | None = None
    idempotency_key: str | None = None


class PreferenceResponse(BaseSchema):
    preference_id: int
    user_id: int
    channel: str
    is_enabled: bool
    updated_at: datetime | None = None


class PreferenceUpdate(BaseSchema):
    channel: str
    is_enabled: bool
