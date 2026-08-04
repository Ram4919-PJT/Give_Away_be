import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from comm_app.db.base import Base
from comm_app.models.enums import DeliveryStatus, NotificationChannel, NotificationStatus


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    title_template: Mapped[str] = mapped_column(String(255), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel_enum"),
        nullable=False,
        server_default=NotificationChannel.IN_APP.value,
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    notifications: Mapped[list["Notification"]] = relationship(back_populates="template")


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("notification_templates.template_id", ondelete="SET NULL"),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel_enum", create_constraint=False),
        nullable=False,
        server_default=NotificationChannel.IN_APP.value,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status_enum"),
        nullable=False,
        server_default=NotificationStatus.PENDING.value,
        index=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    template: Mapped["NotificationTemplate | None"] = relationship(back_populates="notifications")
    delivery_logs: Mapped[list["DeliveryLog"]] = relationship(back_populates="notification")


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    delivery_log_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("notifications.notification_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel_enum", create_constraint=False),
        nullable=False,
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status_enum"),
        nullable=False,
        server_default=DeliveryStatus.QUEUED.value,
    )
    provider_response: Mapped[str | None] = mapped_column(Text)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    notification: Mapped["Notification"] = relationship(back_populates="delivery_logs")


class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"

    preference_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel_enum", create_constraint=False),
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        {"comment": "Per-user channel opt-in/out"},
    )
