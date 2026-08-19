"""Strict receiver KYC submission validation."""

from __future__ import annotations

import re
from typing import Any

from core_app.services.kyc.masking import looks_masked_value
from core_app.services.kyc.receiver_document_config import (
    KYC_ASSISTANCE_PURPOSE_OPTIONS,
    get_all_required_document_types,
    get_kyc_purpose_documents,
    normalize_kyc_purpose,
)

FieldError = dict[str, str]

_PINCODE_RE = re.compile(r"^\d{6}$")
_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$", re.IGNORECASE)
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\s'.-]{0,59}$")

_ID_NUMBER_RULES: dict[str, re.Pattern[str]] = {
    "AADHAAR": re.compile(r"^\d{12}$"),
    "PAN": re.compile(r"^[A-Z]{5}\d{4}[A-Z]$", re.IGNORECASE),
    "PASSPORT": re.compile(r"^[A-Z]\d{7}$", re.IGNORECASE),
    "VOTER_ID": re.compile(r"^[A-Z]{3}\d{7}$", re.IGNORECASE),
}


def _err(field: str, message: str, *, code: str | None = None) -> FieldError:
    out: FieldError = {"field": field, "message": message}
    if code:
        out["code"] = code
    return out


def _section(payload: dict | None, key: str) -> dict[str, Any]:
    val = (payload or {}).get(key)
    return val if isinstance(val, dict) else {}


def _missing(value: Any) -> bool:
    return value is None or not str(value).strip()


def validate_kyc_purpose_code(raw: str | None) -> str | None:
    canonical = normalize_kyc_purpose(raw)
    if not canonical:
        return None
    allowed = {opt["id"] for opt in KYC_ASSISTANCE_PURPOSE_OPTIONS}
    return canonical if canonical in allowed else None


def validate_receiver_kyc_submission(
    *,
    payload: dict | None,
    uploaded_document_types: list[str],
    consent_given: bool,
) -> list[FieldError]:
    """Return field errors; empty list means ready to submit."""
    errors: list[FieldError] = []
    payload = payload or {}
    uploaded = set(uploaded_document_types)

    if not consent_given:
        errors.append(_err("consent", "Please confirm the declaration before submitting.", code="CONSENT_REQUIRED"))

    personal = _section(payload, "personal")
    first_name = str(personal.get("first_name") or "").strip()
    last_name = str(personal.get("last_name") or "").strip()
    full_name = str(personal.get("full_name") or "").strip()
    if not full_name and (first_name or last_name):
        full_name = f"{first_name} {last_name}".strip()

    if _missing(first_name):
        errors.append(_err("personal.first_name", "Enter your first name.", code="FIELD_REQUIRED"))
    elif not _NAME_RE.match(first_name) or len(first_name) < 2:
        errors.append(
            _err(
                "personal.first_name",
                "First name must use letters only (2–60 characters).",
                code="INVALID_NAME",
            )
        )

    if _missing(last_name):
        errors.append(_err("personal.last_name", "Enter your last name.", code="FIELD_REQUIRED"))
    elif not _NAME_RE.match(last_name):
        errors.append(
            _err(
                "personal.last_name",
                "Last name must use letters only (2–60 characters).",
                code="INVALID_NAME",
            )
        )

    if _missing(full_name):
        errors.append(_err("personal.full_name", "Enter your full legal name.", code="FIELD_REQUIRED"))

    for key in ("dob", "email"):
        if _missing(personal.get(key)):
            errors.append(
                _err(f"personal.{key}", f"Enter your {key.replace('_', ' ')}.", code="FIELD_REQUIRED")
            )

    if personal.get("email") and not _EMAIL_RE.match(str(personal["email"]).strip()):
        errors.append(_err("personal.email", "Enter a valid email address.", code="INVALID_EMAIL"))

    mobile_verification = _section(payload, "mobile_verification")
    mobile_section = _section(payload, "mobile")
    mobile = mobile_verification.get("mobile") or mobile_section.get("mobile") or personal.get("mobile")
    if _missing(mobile):
        errors.append(_err("mobile", "Enter your mobile number.", code="FIELD_REQUIRED"))
    else:
        digits = "".join(c for c in str(mobile) if c.isdigit())[-10:]
        if not _MOBILE_RE.match(digits):
            errors.append(_err("mobile", "Enter a valid 10-digit mobile number.", code="INVALID_MOBILE"))
    if not mobile_verification.get("verified_at"):
        errors.append(
            _err(
                "mobile_verification",
                "Verify your mobile number with the OTP before submitting.",
                code="MOBILE_NOT_VERIFIED",
            )
        )

    identity = _section(payload, "identity")
    id_type = str(identity.get("id_type") or "").strip().upper()
    id_number = str(identity.get("id_number") or "").strip()
    if _missing(id_type):
        errors.append(_err("identity.id_type", "Select your identity document type.", code="FIELD_REQUIRED"))
    if _missing(id_number):
        errors.append(
            _err(
                "identity.id_number",
                "Enter your document number exactly as shown on the document.",
                code="FIELD_REQUIRED",
            )
        )
    elif looks_masked_value(id_number):
        errors.append(
            _err(
                "identity.id_number",
                "Re-enter your full document number. Masked values cannot be submitted.",
                code="INVALID_DOCUMENT_NUMBER",
            )
        )
    elif id_type in _ID_NUMBER_RULES:
        normalized = re.sub(r"\s+", "", id_number.upper())
        if id_type == "AADHAAR":
            normalized = re.sub(r"\D", "", id_number)
        if not _ID_NUMBER_RULES[id_type].match(normalized):
            errors.append(
                _err(
                    "identity.id_number",
                    f"Enter a valid {id_type.replace('_', ' ').title()} number.",
                    code="INVALID_DOCUMENT_NUMBER",
                )
            )
    if "ID_FRONT" not in uploaded:
        errors.append(
            _err(
                "document.ID_FRONT",
                "Please upload the front side of your identity document.",
                code="KYC_DOCUMENTS_MISSING",
            )
        )

    address = _section(payload, "address")
    for key, label in (
        ("address_line", "address"),
        ("city", "city"),
        ("state", "state"),
        ("pincode", "pincode"),
    ):
        if _missing(address.get(key)):
            errors.append(_err(f"address.{key}", f"Enter your {label}.", code="FIELD_REQUIRED"))
    pincode = str(address.get("pincode") or "").strip()
    if pincode and not _PINCODE_RE.match(pincode):
        errors.append(_err("address.pincode", "Enter a valid 6-digit pincode.", code="INVALID_PINCODE"))
    if "ADDRESS_PROOF" not in uploaded:
        errors.append(
            _err(
                "document.ADDRESS_PROOF",
                "Please upload a valid address proof document.",
                code="KYC_DOCUMENTS_MISSING",
            )
        )

    beneficiary = _section(payload, "beneficiary")
    if _missing(beneficiary.get("relationship")):
        errors.append(
            _err("beneficiary.relationship", "Select who will benefit from assistance.", code="FIELD_REQUIRED")
        )
    if beneficiary.get("relationship") not in (None, "", "SELF") and "RELATIONSHIP_PROOF" not in uploaded:
        errors.append(
            _err(
                "document.RELATIONSHIP_PROOF",
                "Upload relationship proof when the beneficiary is not yourself.",
                code="KYC_DOCUMENTS_MISSING",
            )
        )

    assistance = _section(payload, "assistance")
    kyc_purpose = validate_kyc_purpose_code(assistance.get("category") or assistance.get("assistance_purpose"))
    if not kyc_purpose:
        errors.append(
            _err("assistance.category", "Select your verification purpose.", code="INVALID_KYC_PURPOSE")
        )
    else:
        if _missing(assistance.get("explanation")):
            errors.append(
                _err(
                    "assistance.explanation",
                    "Briefly explain why you need financial assistance.",
                    code="FIELD_REQUIRED",
                )
            )
        for doc in get_kyc_purpose_documents(kyc_purpose):
            if doc.get("required") and doc["type"] not in uploaded:
                errors.append(
                    _err(
                        f"document.{doc['type']}",
                        f"Please upload: {doc['label']}.",
                        code="KYC_DOCUMENTS_MISSING",
                    )
                )

    bank = _section(payload, "bank")
    for key, label in (
        ("account_holder_name", "account holder name"),
        ("bank_name", "bank name"),
        ("account_number", "account number"),
        ("ifsc", "IFSC code"),
    ):
        if _missing(bank.get(key)):
            errors.append(_err(f"bank.{key}", f"Enter the {label}.", code="FIELD_REQUIRED"))
    account_number = str(bank.get("account_number") or "").strip()
    if account_number and looks_masked_value(account_number):
        errors.append(
            _err(
                "bank.account_number",
                "Re-enter your full bank account number.",
                code="INVALID_ACCOUNT_NUMBER",
            )
        )
    ifsc = str(bank.get("ifsc") or "").strip().upper()
    if ifsc and not _IFSC_RE.match(ifsc):
        errors.append(_err("bank.ifsc", "Enter a valid IFSC code.", code="INVALID_IFSC"))
    if "BANK_PROOF" not in uploaded:
        errors.append(
            _err(
                "document.BANK_PROOF",
                "Please upload bank proof (cancelled cheque or bank statement).",
                code="KYC_DOCUMENTS_MISSING",
            )
        )

    for doc_type in get_all_required_document_types(payload):
        if doc_type not in uploaded:
            label = doc_type.replace("_", " ").title()
            if not any(e.get("field") == f"document.{doc_type}" for e in errors):
                errors.append(
                    _err(
                        f"document.{doc_type}",
                        f"Please upload: {label}.",
                        code="KYC_DOCUMENTS_MISSING",
                    )
                )

    for item in payload.get("admin_document_requests") or []:
        if item.get("status") in (None, "PENDING", "MORE_INFORMATION_REQUIRED"):
            doc_type = item.get("document_type")
            if doc_type and doc_type not in uploaded:
                errors.append(
                    _err(
                        f"document.{doc_type}",
                        item.get("reason") or f"Admin requested: {doc_type.replace('_', ' ')}.",
                        code="ADMIN_DOCUMENT_REQUIRED",
                    )
                )

    return errors


def build_kyc_readiness_response(
    *,
    payload: dict | None,
    uploaded_document_types: list[str],
    consent_given: bool = False,
) -> dict[str, Any]:
    errors = validate_receiver_kyc_submission(
        payload=payload,
        uploaded_document_types=uploaded_document_types,
        consent_given=consent_given,
    )
    missing_documents = sorted(
        {e["field"].replace("document.", "") for e in errors if e["field"].startswith("document.")}
    )
    return {
        "ready": not errors,
        "errors": errors,
        "missing_documents": missing_documents,
        "required_document_types": get_all_required_document_types(payload),
        "uploaded_document_types": list(uploaded_document_types),
    }
