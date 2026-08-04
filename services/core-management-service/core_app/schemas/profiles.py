from uuid import UUID

from core_app.models.enums import ProfileStatus, ProgramStatus
from core_app.schemas.common import BaseSchema, TimestampSchema


class DonorProfileCreate(BaseSchema):
    organization_name: str | None = None
    pan_number: str | None = None


class DonorProfileResponse(TimestampSchema):
    donor_profile_id: UUID
    user_id: UUID
    organization_name: str | None
    pan_number: str | None
    status: ProfileStatus


class ReceiverProfileCreate(BaseSchema):
    household_size: int | None = None
    monthly_income: float | None = None


class ReceiverProfileResponse(TimestampSchema):
    receiver_profile_id: UUID
    user_id: UUID
    household_size: int | None
    monthly_income: float | None
    status: ProfileStatus


class NgoProfileCreate(BaseSchema):
    registration_number: str
    organization_name: str
    focus_area: str | None = None


class NgoProfileResponse(TimestampSchema):
    ngo_profile_id: UUID
    user_id: UUID
    registration_number: str
    organization_name: str
    focus_area: str | None
    status: ProfileStatus


class ProgramCreate(BaseSchema):
    title: str
    description: str | None = None


class ProgramResponse(TimestampSchema):
    program_id: UUID
    ngo_profile_id: UUID
    title: str
    description: str | None
    status: ProgramStatus
