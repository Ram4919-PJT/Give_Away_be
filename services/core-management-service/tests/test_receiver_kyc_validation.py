"""Tests for receiver KYC submission validation."""

import pytest

from core_app.services.kyc.receiver_kyc_validation import (
    build_kyc_readiness_response,
    validate_receiver_kyc_submission,
)


def _valid_payload() -> dict:
    return {
        "personal": {
            "full_name": "Rahul Kumar",
            "dob": "1990-01-15",
            "email": "rahul@example.com",
            "mobile": "9876543210",
        },
        "mobile_verification": {
            "mobile": "9876543210",
            "verified_at": "2026-01-01T10:00:00Z",
        },
        "identity": {"id_type": "PAN", "id_number": "ABCDE1234F"},
        "address": {
            "address_line": "12 MG Road",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560001",
        },
        "beneficiary": {"relationship": "SELF"},
        "assistance": {
            "category": "MEDICAL",
            "explanation": "Need support for hospital treatment and medicines.",
        },
        "bank": {
            "account_holder_name": "Rahul Kumar",
            "bank_name": "State Bank",
            "account_number": "123456789012",
            "ifsc": "SBIN0001234",
        },
        "payment_destination": {"type": "RECEIVER_BANK"},
    }


def _uploaded_docs() -> list[str]:
    return [
        "ID_FRONT",
        "ADDRESS_PROOF",
        "BANK_PROOF",
        "MEDICAL_REPORT",
        "HOSPITAL_ESTIMATE",
    ]


def test_valid_submission_has_no_errors():
    errors = validate_receiver_kyc_submission(
        payload=_valid_payload(),
        uploaded_document_types=_uploaded_docs(),
        consent_given=True,
    )
    assert errors == []


def test_missing_consent_returns_error():
    errors = validate_receiver_kyc_submission(
        payload=_valid_payload(),
        uploaded_document_types=_uploaded_docs(),
        consent_given=False,
    )
    assert any(e["code"] == "CONSENT_REQUIRED" for e in errors)


def test_unverified_mobile_blocks_submit():
    payload = _valid_payload()
    payload["mobile_verification"] = {"mobile": "9876543210"}
    errors = validate_receiver_kyc_submission(
        payload=payload,
        uploaded_document_types=_uploaded_docs(),
        consent_given=True,
    )
    assert any(e["code"] == "MOBILE_NOT_VERIFIED" for e in errors)


def test_missing_required_documents():
    errors = validate_receiver_kyc_submission(
        payload=_valid_payload(),
        uploaded_document_types=["ID_FRONT"],
        consent_given=True,
    )
    fields = {e["field"] for e in errors}
    assert "document.ADDRESS_PROOF" in fields
    assert any(e["code"] == "KYC_DOCUMENTS_MISSING" for e in errors)


def test_invalid_kyc_purpose_rejected():
    payload = _valid_payload()
    payload["assistance"]["category"] = "NOT_A_VALID_PURPOSE"
    errors = validate_receiver_kyc_submission(
        payload=payload,
        uploaded_document_types=_uploaded_docs(),
        consent_given=True,
    )
    assert any(e["code"] == "INVALID_KYC_PURPOSE" for e in errors)


def test_invalid_pan_number():
    payload = _valid_payload()
    payload["identity"]["id_number"] = "INVALID"
    errors = validate_receiver_kyc_submission(
        payload=payload,
        uploaded_document_types=_uploaded_docs(),
        consent_given=True,
    )
    assert any(e["code"] == "INVALID_DOCUMENT_NUMBER" for e in errors)


def test_readiness_response_ready_when_complete():
    result = build_kyc_readiness_response(
        payload=_valid_payload(),
        uploaded_document_types=_uploaded_docs(),
        consent_given=True,
    )
    assert result["ready"] is True
    assert result["errors"] == []
    assert "MEDICAL_REPORT" in result["required_document_types"]


def test_readiness_response_not_ready_lists_missing_docs():
    result = build_kyc_readiness_response(
        payload=_valid_payload(),
        uploaded_document_types=["ID_FRONT"],
        consent_given=True,
    )
    assert result["ready"] is False
    assert "ADDRESS_PROOF" in result["missing_documents"]
