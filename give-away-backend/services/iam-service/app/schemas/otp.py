from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.models.enums import OtpPurpose, OtpVerifiedStatus
from app.schemas.common import ORMModel
from app.schemas.validators import validate_otp_code


class OtpCreate(ORMModel):
    user_id: UUID
    otp_code: str = Field(..., min_length=4, max_length=6)
    purpose: OtpPurpose
    expires_at: datetime

    @field_validator("otp_code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return validate_otp_code(value)

    @model_validator(mode="after")
    def validate_expiry(self) -> "OtpCreate":
        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        return self


class OtpVerifyRequest(ORMModel):
    otp_code: str = Field(..., min_length=4, max_length=6)
    purpose: OtpPurpose

    @field_validator("otp_code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return validate_otp_code(value)


class OtpResponse(ORMModel):
    otp_id: UUID
    user_id: UUID
    purpose: OtpPurpose
    expires_at: datetime
    verified_status: OtpVerifiedStatus