from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator, model_validator

from app.models.enums import OtpPurpose, OtpVerificationStatus
from app.schemas.common import ORMModel
from app.schemas.validators import normalize_email, normalize_mobile, validate_otp_code


class OtpSendRequest(ORMModel):
    email: EmailStr | None = None
    mobile: str | None = None
    purpose: OtpPurpose

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: EmailStr | None) -> str | None:
        return normalize_email(value) if value else None

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str | None) -> str | None:
        return normalize_mobile(value) if value else None

    @model_validator(mode="after")
    def validate_identifier(self) -> "OtpSendRequest":
        if not self.email and not self.mobile:
            raise ValueError("Either email or mobile is required")
        return self


class OtpVerifyRequest(ORMModel):
    email: EmailStr | None = None
    mobile: str | None = None
    otp_code: str = Field(..., min_length=4, max_length=6)
    purpose: OtpPurpose

    @field_validator("otp_code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return validate_otp_code(value)

    @model_validator(mode="after")
    def validate_identifier(self) -> "OtpVerifyRequest":
        if not self.email and not self.mobile:
            raise ValueError("Either email or mobile is required")
        return self


class OtpResponse(ORMModel):
    otp_id: UUID
    user_id: UUID
    purpose: OtpPurpose
    expires_at: datetime
    verified_status: OtpVerificationStatus
