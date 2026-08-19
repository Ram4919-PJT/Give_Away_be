from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KycDocumentSpecOut(BaseModel):
    type: str
    label: str
    required: bool = True


class ReceiverKycPurposeOut(BaseModel):
    code: str
    name: str
    description: str
    required_documents: list[KycDocumentSpecOut] = Field(default_factory=list)
    optional_documents: list[KycDocumentSpecOut] = Field(default_factory=list)


class ReceiverKycConfigOut(BaseModel):
    version: str = "1"
    purposes: list[ReceiverKycPurposeOut]
    identity_document_types: list[dict[str, Any]]
    address_proof_types: list[dict[str, Any]]
    beneficiary_relationships: list[dict[str, Any]]
    payment_destination_types: list[dict[str, Any]]
    base_documents: list[KycDocumentSpecOut]
    progress_steps: list[dict[str, str]]
    wizard_steps: list[dict[str, Any]] = Field(default_factory=list)
    consent_version: str
    consent_text: str | None = None
    upload_limits: dict[str, Any] | None = None
