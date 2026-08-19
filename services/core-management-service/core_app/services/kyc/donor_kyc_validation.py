"""Donor verification submission validation."""

from __future__ import annotations

from typing import Any

from core_app.services.kyc.donor_document_config import (
    DONOR_REQUIRED_DOCUMENT_TYPES,
    get_donor_document_label,
)

FieldError = dict[str, str]


def _err(field: str, message: str, *, code: str | None = None) -> FieldError:
    out: FieldError = {"field": field, "message": message}
    if code:
        out["code"] = code
    return out


def validate_donor_verification_submission(
    *,
    uploaded_document_types: list[str],
) -> list[FieldError]:
    errors: list[FieldError] = []
    uploaded = set(uploaded_document_types or [])

    for doc_type in DONOR_REQUIRED_DOCUMENT_TYPES:
        if doc_type not in uploaded:
            label = get_donor_document_label(doc_type)
            errors.append(
                _err(
                    f"document.{doc_type}",
                    f"{label} is required to submit verification.",
                    code="DONOR_DOCUMENTS_MISSING",
                )
            )

    return errors


def build_donor_readiness_response(
    *,
    uploaded_document_types: list[str],
) -> dict[str, Any]:
    errors = validate_donor_verification_submission(uploaded_document_types=uploaded_document_types)
    missing_documents = sorted(
        {e["field"].replace("document.", "") for e in errors if e["field"].startswith("document.")}
    )
    return {
        "ready": not errors,
        "errors": errors,
        "missing_documents": missing_documents,
        "required_document_types": list(DONOR_REQUIRED_DOCUMENT_TYPES),
        "uploaded_document_types": list(uploaded_document_types),
    }
