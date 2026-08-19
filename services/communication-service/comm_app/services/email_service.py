"""SMTP email delivery."""

from __future__ import annotations

import logging
import re
import smtplib
import ssl
from email.message import EmailMessage

from comm_app.config import settings

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_recipient(email: str | None) -> str | None:
    if not email:
        return None
    cleaned = email.strip()
    if not _EMAIL_RE.match(cleaned):
        return None
    if "\n" in cleaned or "\r" in cleaned:
        return None
    return cleaned


def send_email(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> str:
    """Send email via SMTP. Returns provider message id or local id."""
    recipient = validate_recipient(to_email)
    if not recipient:
        raise ValueError("Invalid recipient email address")

    if not settings.EMAIL_ENABLED:
        logger.info("EMAIL_ENABLED=false — skipping SMTP send to %s", recipient)
        return "skipped-local"

    message = EmailMessage()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = recipient
    message["Subject"] = subject.replace("\n", " ").replace("\r", " ")
    message.set_content(text_body or _html_to_text(html_body), subtype="plain", charset="utf-8")
    message.add_alternative(html_body, subtype="html", charset="utf-8")

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls(context=context)
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        response = server.send_message(message)

    provider_id = f"smtp:{recipient}:{message['Subject']}"
    if response:
        logger.debug("SMTP partial failures: %s", response)
    return provider_id


def _html_to_text(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
