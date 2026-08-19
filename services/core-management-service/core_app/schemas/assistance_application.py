from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from core_app.services.receiver_assistance_config import validate_assistance_category


class AssistanceApplicationCreate(BaseModel):
    purpose: str = Field(..., min_length=1, max_length=2000)
    amount_requested: float = Field(..., gt=0)
    category: str = Field(..., min_length=1, max_length=100)
    expense_breakdown: str | None = None
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category_code(cls, value: str) -> str:
        return validate_assistance_category(value)


class AssistanceApplicationDocumentOut(BaseModel):
    document_id: int
    document_type: str
    original_filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    uploaded_at: datetime | None = None

    model_config = {"from_attributes": True}


class ApplicationStatusHistoryOut(BaseModel):
    history_id: int
    status: str
    changed_at: datetime | None = None

    model_config = {"from_attributes": True}


class AssistanceReadinessResponse(BaseModel):
    ready: bool
    errors: list[dict[str, str]] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    required_document_types: list[str] = Field(default_factory=list)
    uploaded_document_types: list[str] = Field(default_factory=list)
    limits: dict[str, float | int | str] | None = None


class AssistanceApplicationOut(BaseModel):
    application_id: int
    receiver_id: int
    purpose: str
    amount_requested: float
    amount_approved: float | None = None
    category: str | None = None
    expense_breakdown: str | None = None
    notes: str | None = None
    status: str
    rejection_reason: str | None = None
    action_required_reason: str | None = None
    payout_status: str | None = None
    bank_account_holder: str | None = None
    bank_name: str | None = None
    bank_ifsc: str | None = None
    bank_account_last4: str | None = None
    bank_details_submitted_at: datetime | None = None
    payment_destination_type: str | None = None
    disbursement_reference: str | None = None
    disbursed_at: datetime | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by_user_id: int | None = None
    receiver_name: str | None = None
    receiver_email: str | None = None
    receiver_mobile: str | None = None
    receiver_verification_status: str | None = None
    receiver_kyc_request_id: int | None = None
    receiver_kyc_reference: str | None = None
    documents: list[AssistanceApplicationDocumentOut] = Field(default_factory=list)
    history: list[ApplicationStatusHistoryOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AssistanceApplicationUpdate(BaseModel):
    purpose: str | None = Field(default=None, min_length=1, max_length=2000)
    amount_requested: float | None = Field(default=None, gt=0)
    category: str | None = None
    expense_breakdown: str | None = None
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_assistance_category(value)


class AssistanceReviewRequest(BaseModel):
    action: str = Field(..., description="approve, reject, under_review, or request_action")
    approved_amount: float | None = Field(default=None, gt=0)
    rejection_reason: str | None = None
    action_required_reason: str | None = None


class AssistanceDisburseRequest(BaseModel):
    disbursement_reference: str = Field(..., min_length=3, max_length=100, description="UTR / transaction reference")
    note: str | None = None


class BankDetailsSubmit(BaseModel):
    account_holder_name: str = Field(..., min_length=2, max_length=150)
    bank_name: str = Field(..., min_length=2, max_length=150)
    account_number: str = Field(..., min_length=8, max_length=18)
    ifsc_code: str = Field(..., min_length=11, max_length=11)
    confirm_account_number: str = Field(..., min_length=8, max_length=18)
