"""Configuration for donor identity verification documents."""

from __future__ import annotations

from typing import Any

DONOR_DOCUMENT_SPECS: list[dict[str, Any]] = [
    {
        "type": "AADHAAR_CARD",
        "label": "Aadhaar Card",
        "description": "Upload front side of your Aadhaar card",
        "required": True,
    },
    {
        "type": "SELFIE",
        "label": "Selfie",
        "description": "Upload your recent selfie",
        "required": False,
    },
    {
        "type": "ADDRESS_PROOF",
        "label": "Address Proof",
        "description": "Upload proof of your address",
        "required": False,
    },
]

DONOR_ALLOWED_DOCUMENT_TYPES = frozenset(spec["type"] for spec in DONOR_DOCUMENT_SPECS)
DONOR_REQUIRED_DOCUMENT_TYPES = frozenset(
    spec["type"] for spec in DONOR_DOCUMENT_SPECS if spec.get("required")
)

DONOR_CONSENT_VERSION = "donor-verification-v1"
DONOR_CONSENT_TEXT = (
    "I confirm that the documents I have uploaded are accurate and belong to me. "
    "I authorize AJA Abayahastham to verify my identity for donor trust and compliance purposes."
)


def get_donor_document_label(document_type: str) -> str:
    for spec in DONOR_DOCUMENT_SPECS:
        if spec["type"] == document_type:
            return spec["label"]
    return document_type.replace("_", " ").title()


def build_donor_verification_config_response() -> dict[str, Any]:
    return {
        "version": "1",
        "documents": DONOR_DOCUMENT_SPECS,
        "required_document_types": list(DONOR_REQUIRED_DOCUMENT_TYPES),
        "consent_version": DONOR_CONSENT_VERSION,
        "consent_text": DONOR_CONSENT_TEXT,
        "upload_limits": {
            "max_bytes": 10 * 1024 * 1024,
            "allowed_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "allowed_mime_types": ["application/pdf", "image/jpeg", "image/png"],
        },
    }
