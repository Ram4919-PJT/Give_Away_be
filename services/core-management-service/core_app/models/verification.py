import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base
from core_app.models.enums import DocumentType, VerificationEntityType, VerificationStatus


class VerificationRejectionReason(Base):
    __tablename__ = "verification_rejection_reasons"

    reason_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))


class VerificationRequest(Base):
    __tablename__ = "verification_requests"

    verification_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    entity_type: Mapped[VerificationEntityType] = mapped_column(
        Enum(VerificationEntityType, name="verification_entity_type_enum"),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status_enum"),
        nullable=False,
        server_default=VerificationStatus.PENDING.value,
        index=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    rejection_reason_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("verification_rejection_reasons.reason_id", ondelete="SET NULL"),
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list["VerificationDocument"]] = relationship(
        back_populates="verification_request"
    )
    history: Mapped[list["VerificationHistory"]] = relationship(
        back_populates="verification_request"
    )


class VerificationDocument(Base):
    __tablename__ = "verification_documents"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    verification_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("verification_requests.verification_request_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type_enum"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    verification_request: Mapped["VerificationRequest"] = relationship(
        back_populates="documents"
    )


class VerificationHistory(Base):
    __tablename__ = "verification_history"

    history_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    verification_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("verification_requests.verification_request_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[VerificationStatus | None] = mapped_column(
        Enum(VerificationStatus, name="verification_status_enum", create_constraint=False)
    )
    to_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status_enum", create_constraint=False),
        nullable=False,
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    comment: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    verification_request: Mapped["VerificationRequest"] = relationship(back_populates="history")
