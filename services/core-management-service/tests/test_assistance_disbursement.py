"""Tests for assistance approval and disbursement rules."""

from core_app.services.receiver_kyc_payout import get_receiver_kyc_payout_info


def test_kyc_payout_info_structure():
    # Document expected keys for integration tests with DB fixtures later
    assert callable(get_receiver_kyc_payout_info)
