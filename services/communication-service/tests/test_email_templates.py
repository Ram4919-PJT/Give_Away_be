import pytest

from comm_app.services.email_service import validate_recipient
from comm_app.services.email_template_service import render_email_template


def test_validate_recipient_accepts_valid_email():
    assert validate_recipient("user@example.com") == "user@example.com"


def test_validate_recipient_rejects_invalid_email():
    assert validate_recipient("not-an-email") is None
    assert validate_recipient("") is None
    assert validate_recipient("a@b.com\nBcc: evil@x.com") is None


def test_render_welcome_template_contains_name():
    _, html = render_email_template(
        "welcome",
        {"user_name": "Ramesh Kumar", "action_url": "http://localhost/dashboard"},
    )
    assert "Ramesh Kumar" in html
    assert "Give Away" in html


def test_render_payment_success_contains_amount():
    _, html = render_email_template(
        "payment_success",
        {
            "user_name": "Donor",
            "campaign_name": "Education Support",
            "amount_display": "₹5,000",
            "donation_id": "123",
        },
    )
    assert "₹5,000" in html
    assert "Education Support" in html


def test_render_password_reset_contains_otp():
    _, html = render_email_template(
        "password_reset",
        {"user_name": "User", "otp_code": "123456"},
    )
    assert "123456" in html
