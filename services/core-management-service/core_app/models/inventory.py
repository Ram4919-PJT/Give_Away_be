import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base
from core_app.models.enums import InventoryStatus


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    donation_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("donation_items.donation_item_id", ondelete="SET NULL"),
    )
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    unit: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[InventoryStatus] = mapped_column(
        Enum(InventoryStatus, name="inventory_status_enum"),
        nullable=False,
        server_default=InventoryStatus.AVAILABLE.value,
        index=True,
    )
    warehouse_location: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class InventoryAllocation(Base):
    __tablename__ = "inventory_allocations"

    allocation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory_items.inventory_item_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assistance_request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assistance_requests.assistance_request_id", ondelete="SET NULL"),
    )
    allocated_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_to_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    allocated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
