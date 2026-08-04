from datetime import datetime
from uuid import UUID

from core_app.models.enums import DonationStatus, DonationType, VerificationEntityType, VerificationStatus
from core_app.schemas.common import BaseSchema, TimestampSchema


class DonationCreate(BaseSchema):
    donation_type: DonationType
    notes: str | None = None
    amount: float | None = None
    currency: str = "INR"


class DonationResponse(TimestampSchema):
    donation_id: UUID
    donor_user_id: UUID
    donation_type: DonationType
    status: DonationStatus
    notes: str | None


class VerificationRequestCreate(BaseSchema):
    entity_type: VerificationEntityType
    entity_id: UUID
    notes: str | None = None


class VerificationRequestResponse(BaseSchema):
    verification_request_id: UUID
    user_id: UUID
    entity_type: VerificationEntityType
    entity_id: UUID
    status: VerificationStatus
    submitted_at: datetime
    notes: str | None
