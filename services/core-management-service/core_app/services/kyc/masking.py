"""Mask sensitive identity and financial values for API responses."""

from __future__ import annotations

import re

_MASKED_CHAR_RE = re.compile(r"[•\*X]{2,}", re.IGNORECASE)


def mask_last4(value: str | None, *, visible: int = 4) -> str | None:
    if not value:
        return None
    raw = re.sub(r"\s+", "", str(value))
    if len(raw) <= visible:
        return "••••"
    return f"{'•' * max(4, len(raw) - visible)} {raw[-visible:]}"


def mask_aadhaar(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", str(value))
    if len(digits) < 4:
        return "XXXX XXXX ••••"
    return f"XXXX XXXX {digits[-4:]}"


def mask_pan(value: str | None) -> str | None:
    if not value:
        return None
    raw = str(value).strip().upper()
    if len(raw) <= 4:
        return "••••"
    return f"{'•' * (len(raw) - 4)}{raw[-4:]}"


def mask_bank_account(value: str | None) -> str | None:
    return mask_last4(value)


def mask_document_number(document_type: str | None, value: str | None) -> str | None:
    if not value:
        return None
    id_type = str(document_type or "").upper()
    if "AADHAAR" in id_type:
        return mask_aadhaar(value)
    if "PAN" in id_type:
        return mask_pan(value)
    return mask_last4(value)


def looks_masked_value(value: str | None) -> bool:
    """True when a value appears to be a display mask, not a real document/account number."""
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    if _MASKED_CHAR_RE.search(text):
        return True
    if "XXXX" in text.upper():
        return True
    return False


def mask_payload_sensitive(payload: dict | None) -> dict:
    if not payload:
        return {}
    out = dict(payload)

    identity = dict(out.get("identity") or {})
    if identity.get("id_number"):
        identity["id_number"] = mask_document_number(
            identity.get("id_type"), identity["id_number"]
        )
    out["identity"] = identity

    for key in ("bank", "payment_destination"):
        section = dict(out.get(key) or {})
        if section.get("account_number"):
            section["account_number"] = mask_bank_account(section["account_number"])
        out[key] = section

    return out
