from __future__ import annotations

from pydantic import BaseModel


class DonorDocumentSpecOut(BaseModel):
    type: str
    label: str
    description: str
    required: bool = False


class DonorVerificationConfigOut(BaseModel):
    version: str = "1"
    documents: list[DonorDocumentSpecOut]
    required_document_types: list[str]
    consent_version: str
    consent_text: str
    upload_limits: dict[str, int | list[str]]
