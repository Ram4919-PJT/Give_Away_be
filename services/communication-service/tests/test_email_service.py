from unittest.mock import patch

import pytest

from comm_app.services.email_service import send_email


def test_send_email_disabled_returns_skipped_local():
    with patch("comm_app.services.email_service.settings") as mock_settings:
        mock_settings.EMAIL_ENABLED = False
        mock_settings.SMTP_FROM_NAME = "Give Away"
        mock_settings.SMTP_FROM_EMAIL = "noreply@test.local"
        result = send_email(
            to_email="user@example.com",
            subject="Test",
            html_body="<p>Hello</p>",
        )
        assert result == "skipped-local"


def test_send_email_invalid_recipient_raises():
    with pytest.raises(ValueError):
        send_email(to_email="bad-email", subject="Test", html_body="<p>Hi</p>")
