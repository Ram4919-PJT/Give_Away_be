"""Tests for donor verification validation."""

from core_app.services.kyc.donor_kyc_validation import (
    build_donor_readiness_response,
    validate_donor_verification_submission,
)


def test_donor_missing_aadhaar():
    errors = validate_donor_verification_submission(uploaded_document_types=[])
    assert any(e["code"] == "DONOR_DOCUMENTS_MISSING" for e in errors)


def test_donor_ready_with_aadhaar():
    errors = validate_donor_verification_submission(uploaded_document_types=["AADHAAR_CARD"])
    assert errors == []


def test_donor_ready_with_optional_docs():
    errors = validate_donor_verification_submission(
        uploaded_document_types=["AADHAAR_CARD", "SELFIE", "ADDRESS_PROOF"]
    )
    assert errors == []


def test_donor_readiness_response():
    result = build_donor_readiness_response(uploaded_document_types=["AADHAAR_CARD"])
    assert result["ready"] is True
    assert result["missing_documents"] == []
