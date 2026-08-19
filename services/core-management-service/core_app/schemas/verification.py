from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class VerificationDocumentOut(BaseModel):
    document_id: int
    document_type: str
    original_filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    verification_status: str
    uploaded_at: datetime | None = None
    rejection_reason: str | None = None

    model_config = {"from_attributes": True}


class VerificationHistoryOut(BaseModel):
    history_id: int
    status: str
    note: str | None = None
    changed_at: datetime | None = None
    changed_by: int | None = None

    model_config = {"from_attributes": True}


class VerificationRequestOut(BaseModel):
    request_id: int
    reference_code: str | None = None
    user_id: int
    request_type: str
    status: str
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    risk_level: str | None = None
    risk_flags: list[str] | None = None
    consent_given: bool = False
    consent_version: str | None = None
    consent_timestamp: datetime | None = None
    payload: dict[str, Any] | None = None
    current_step: int = 1
    documents: list[VerificationDocumentOut] = Field(default_factory=list)
    history: list[VerificationHistoryOut] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class VerificationMeResponse(BaseModel):
    profile_status: str
    request: VerificationRequestOut | None = None


class VerificationDraftUpdate(BaseModel):
    payload: dict[str, Any] | None = None
    current_step: int | None = None


class VerificationSubmitRequest(BaseModel):
    consent_given: bool = False
    consent_version: str = "kyc-v1"


class AdminRejectRequest(BaseModel):
    reason: str


class AdminApproveRequest(BaseModel):
    note: str | None = None


class AdminRequestDocumentsBody(BaseModel):
    document_type: str
    reason: str
    comment: str | None = None
    deadline: str | None = None


class AdminRequestFieldUpdatesBody(BaseModel):
    field_paths: list[str] = Field(min_length=1)
    reason: str
    comment: str | None = None


class AdminSuspendRequest(BaseModel):
    reason: str


class MobileOtpSendRequest(BaseModel):
    mobile: str
    request_id: int


class MobileOtpSendResponse(BaseModel):
    sent: bool = True
    message: str = "OTP sent successfully."
    dev_otp: str | None = None


class MobileOtpVerifyRequest(BaseModel):
    mobile: str
    otp_code: str = Field(..., min_length=4, max_length=6)
    request_id: int


class ReceiverEligibilityResponse(BaseModel):
    eligible: bool
    can_request_assistance: bool = False
    block_reason_code: str | None = None
    reasons: list[str] = Field(default_factory=list)
    missing_steps: list[str] = Field(default_factory=list)
    blocking_flags: list[str] = Field(default_factory=list)
    progress: dict[str, Any] | None = None
    profile_status: str | None = None
    request_status: str | None = None


class KycFieldErrorOut(BaseModel):
    field: str
    message: str
    code: str | None = None


class KycReadinessResponse(BaseModel):
    ready: bool
    errors: list[KycFieldErrorOut] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    required_document_types: list[str] = Field(default_factory=list)
    uploaded_document_types: list[str] = Field(default_factory=list)


class AdminVerificationListItem(BaseModel):
    request_id: int
    reference_code: str | None
    user_id: int
    request_type: str
    status: str
    submitted_at: datetime | None
    risk_level: str | None
    risk_flags: list[str] | None
    applicant_name: str | None = None
