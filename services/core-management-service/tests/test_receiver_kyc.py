"""Unit tests for receiver KYC risk and progress helpers."""

from core_app.services.kyc.masking import mask_aadhaar, mask_bank_account
from core_app.services.receiver_eligibility_service import compute_kyc_progress
from core_app.services.receiver_risk_service import classify_risk_level, compute_consistency_flags


def test_mask_aadhaar_shows_last_four_only():
    assert mask_aadhaar("1234 5678 9012") == "XXXX XXXX 9012"


def test_mask_bank_account():
    assert mask_bank_account("123456789012") is not None
    assert "9012" in mask_bank_account("123456789012")


def test_name_mismatch_flag():
    flags = compute_consistency_flags({
        "personal": {"full_name": "Rahul Kumar"},
        "identity": {"full_name": "Rahul K"},
        "bank": {"account_holder_name": "Rahul Kumar"},
    })
    assert "NAME_MISMATCH" in flags


def test_bank_name_mismatch_flag():
    flags = compute_consistency_flags({
        "personal": {"full_name": "Rahul Kumar"},
        "bank": {"account_holder_name": "Someone Else"},
    })
    assert "BANK_NAME_MISMATCH" in flags


def test_risk_level_medium_for_mismatch():
    assert classify_risk_level(["BANK_NAME_MISMATCH"]) == "MEDIUM"


def test_kyc_progress_percent():
    progress = compute_kyc_progress(
        payload={
            "personal": {"mobile": "9999999999", "email": "a@b.com"},
            "mobile_verification": {"verified_at": "2026-01-01"},
            "identity": {"id_type": "PAN"},
            "address": {"address_line": "1", "city": "X", "state": "Y", "pincode": "1"},
            "beneficiary": {"relationship": "SELF"},
            "assistance": {"category": "MEDICAL"},
            "bank": {"account_holder_name": "A", "account_number": "1", "ifsc": "X"},
        },
        documents=[{"document_type": "ID_FRONT"}],
        profile_status="KYC_IN_PROGRESS",
        request_status="DRAFT",
    )
    assert progress["percent"] > 0
    assert "CONTACT" in progress["completed"]
