"""Configuration-driven document requirements for receiver KYC.

KYC verification uses its own purpose/intent codes (MEDICAL, BASIC_NEEDS, …).
This is separate from financial assistance request categories
(MEDICAL_HEALTHCARE, …) defined in ``receiver_assistance_config``.
"""

from __future__ import annotations

from typing import Any

KYC_ASSISTANCE_PURPOSE_OPTIONS = [
    {
        "id": "MEDICAL",
        "label": "Medical",
        "description": "Hospital bills, treatment, medicines, and healthcare costs.",
    },
    {
        "id": "EDUCATION",
        "label": "Education",
        "description": "School or college fees, books, and education-related expenses.",
    },
    {
        "id": "EMERGENCY",
        "label": "Emergency",
        "description": "Urgent crisis requiring immediate financial support.",
    },
    {
        "id": "BASIC_NEEDS",
        "label": "Basic Needs",
        "description": "Food, shelter, and essential daily living support.",
    },
    {
        "id": "OTHER",
        "label": "Other",
        "description": "Other verified financial hardship not listed above.",
    },
]

ASSISTANCE_CATEGORIES = KYC_ASSISTANCE_PURPOSE_OPTIONS

KYC_PURPOSE_CODES = tuple(opt["id"] for opt in KYC_ASSISTANCE_PURPOSE_OPTIONS)

IDENTITY_DOCUMENT_TYPES = [
    {"id": "AADHAAR", "label": "Aadhaar", "requires_back": False},
    {"id": "PAN", "label": "PAN", "requires_back": False},
    {"id": "PASSPORT", "label": "Passport", "requires_back": False},
    {"id": "DRIVING_LICENCE", "label": "Driving Licence", "requires_back": True},
    {"id": "VOTER_ID", "label": "Voter ID", "requires_back": False},
]

ADDRESS_PROOF_TYPES = [
    {"id": "AADHAAR", "label": "Aadhaar"},
    {"id": "PASSPORT", "label": "Passport"},
    {"id": "DRIVING_LICENCE", "label": "Driving Licence"},
    {"id": "VOTER_ID", "label": "Voter ID"},
    {"id": "UTILITY_BILL", "label": "Utility bill"},
    {"id": "RENT_AGREEMENT", "label": "Rent agreement"},
]

BENEFICIARY_RELATIONSHIPS = [
    {"id": "SELF", "label": "Myself"},
    {"id": "PARENT", "label": "Parent"},
    {"id": "CHILD", "label": "Child"},
    {"id": "SPOUSE", "label": "Spouse"},
    {"id": "FAMILY_MEMBER", "label": "Family member"},
    {"id": "OTHER", "label": "Other"},
]

PAYMENT_DESTINATION_TYPES = [
    {"id": "RECEIVER_BANK", "label": "Receiver bank account"},
    {"id": "BENEFICIARY_BANK", "label": "Beneficiary bank account"},
    {"id": "HOSPITAL", "label": "Hospital / medical institution"},
    {"id": "INSTITUTION", "label": "Educational institution"},
    {"id": "VENDOR", "label": "Approved vendor"},
]

RECEIVER_PROGRESS_STEPS = [
    {"id": "CONTACT", "label": "Contact"},
    {"id": "IDENTITY", "label": "Identity"},
    {"id": "ADDRESS", "label": "Address"},
    {"id": "BENEFICIARY", "label": "Beneficiary"},
    {"id": "SUPPORTING_DOCUMENTS", "label": "Supporting Documents"},
    {"id": "BANK", "label": "Bank"},
    {"id": "ADMIN_REVIEW", "label": "Admin Review"},
]

_BASE_DOCUMENTS = [
    {"type": "ID_FRONT", "label": "Identity document (front)", "required": True},
    {"type": "ADDRESS_PROOF", "label": "Address proof", "required": True},
    {"type": "BANK_PROOF", "label": "Bank proof", "required": True},
]

_KYC_PURPOSE_DOCUMENTS: dict[str, list[dict[str, Any]]] = {
    "MEDICAL": [
        {"type": "MEDICAL_REPORT", "label": "Medical report / diagnosis", "required": True},
        {"type": "HOSPITAL_ESTIMATE", "label": "Hospital estimate / bill", "required": True},
        {"type": "PRESCRIPTION", "label": "Prescription", "required": False},
    ],
    "EDUCATION": [
        {"type": "ADMISSION_LETTER", "label": "Admission letter", "required": True},
        {"type": "FEE_STRUCTURE", "label": "Fee structure", "required": True},
    ],
    "EMERGENCY": [
        {"type": "EMERGENCY_EVIDENCE", "label": "Emergency evidence", "required": True},
    ],
    "BASIC_NEEDS": [
        {"type": "SUPPORTING_PRIMARY", "label": "Supporting document", "required": True},
    ],
    "OTHER": [
        {"type": "SUPPORTING_PRIMARY", "label": "Primary supporting document", "required": True},
    ],
}

_KYC_PURPOSE_ALIASES = {
    "FOOD": "BASIC_NEEDS",
    "FOOD_BASIC_NEEDS": "BASIC_NEEDS",
    "MEDICAL_HEALTHCARE": "MEDICAL",
    "HOUSING": "BASIC_NEEDS",
    "HOUSING_SHELTER": "BASIC_NEEDS",
}


def normalize_kyc_purpose(raw: str | None) -> str | None:
    """Normalize legacy values to a KYC purpose code (not assistance category codes)."""
    if raw is None:
        return None
    cleaned = str(raw).strip()
    if not cleaned:
        return None
    upper = cleaned.upper().replace("-", "_")
    if upper in _KYC_PURPOSE_DOCUMENTS:
        return upper
    if upper in _KYC_PURPOSE_ALIASES:
        return _KYC_PURPOSE_ALIASES[upper]
    lower = cleaned.lower()
    slug_map = {
        "medical": "MEDICAL",
        "education": "EDUCATION",
        "emergency": "EMERGENCY",
        "food": "BASIC_NEEDS",
        "basic_needs": "BASIC_NEEDS",
        "other": "OTHER",
    }
    if lower in slug_map:
        return slug_map[lower]
    return None


def get_kyc_purpose_documents(kyc_purpose: str | None) -> list[dict[str, Any]]:
    code = normalize_kyc_purpose(kyc_purpose) or "OTHER"
    return list(_KYC_PURPOSE_DOCUMENTS.get(code, _KYC_PURPOSE_DOCUMENTS["OTHER"]))


def get_category_documents(category: str | None) -> list[dict[str, Any]]:
    """Backward-compatible alias for KYC purpose documents."""
    return get_kyc_purpose_documents(category)


def get_all_required_document_types(payload: dict | None) -> list[str]:
    required = [d["type"] for d in _BASE_DOCUMENTS if d["required"]]

    assistance = (payload or {}).get("assistance") or {}
    kyc_purpose = assistance.get("category") or assistance.get("assistance_purpose")
    for doc in get_kyc_purpose_documents(kyc_purpose):
        if doc.get("required"):
            required.append(doc["type"])

    beneficiary = (payload or {}).get("beneficiary") or {}
    if beneficiary.get("relationship") not in (None, "", "SELF"):
        required.append("RELATIONSHIP_PROOF")

    for item in (payload or {}).get("admin_document_requests") or []:
        if item.get("status") in (None, "PENDING", "MORE_INFORMATION_REQUIRED"):
            required.append(item["document_type"])

    return list(dict.fromkeys(required))


def build_receiver_kyc_wizard_steps() -> list[dict[str, Any]]:
    """Wizard step definitions consumed by the receiver KYC UI."""
    return [
        {
            "id": "intro",
            "title": "Why verification is needed",
            "hint": "Verification helps us review your identity and supporting documents before you can request financial assistance.",
            "fields": [],
            "documents": [],
        },
        {
            "id": "personal",
            "title": "Personal Information",
            "hint": "Please ensure these details exactly match your identity documents.",
            "fields": [
                {"key": "first_name", "label": "First name", "required": True, "type": "text"},
                {"key": "last_name", "label": "Last name", "required": True, "type": "text"},
                {"key": "dob", "label": "Date of birth", "required": True, "type": "date"},
                {"key": "email", "label": "Email address", "required": True, "type": "email"},
            ],
            "documents": [],
        },
        {
            "id": "mobile",
            "title": "Mobile Verification",
            "mobile_otp": True,
            "fields": [],
            "documents": [],
        },
        {
            "id": "identity",
            "title": "Identity Document",
            "hint": "Choose your identity document and upload the required side(s).",
            "fields": [
                {
                    "key": "id_type",
                    "label": "Identity document",
                    "required": True,
                    "type": "select",
                    "options": IDENTITY_DOCUMENT_TYPES,
                },
                {"key": "id_number", "label": "Document number", "required": True, "type": "text", "sensitive": True},
            ],
            "documents": [
                {"type": "ID_FRONT", "label": "Upload front", "required": True},
                {
                    "type": "ID_BACK",
                    "label": "Upload back",
                    "required": False,
                    "required_when": {"field": "identity.id_type", "values": ["DRIVING_LICENCE"]},
                },
            ],
        },
        {
            "id": "address",
            "title": "Address",
            "fields": [
                {"key": "address_line", "label": "Address", "required": True, "type": "text"},
                {"key": "city", "label": "City", "required": True, "type": "text"},
                {"key": "state", "label": "State", "required": True, "type": "text"},
                {"key": "pincode", "label": "Postal code", "required": True, "type": "text"},
            ],
            "documents": [{"type": "ADDRESS_PROOF", "label": "Address proof", "required": True}],
        },
        {
            "id": "beneficiary",
            "title": "Beneficiary Information",
            "hint": "Who will benefit from this assistance?",
            "fields": [
                {
                    "key": "relationship",
                    "label": "Beneficiary",
                    "required": True,
                    "type": "select",
                    "options": BENEFICIARY_RELATIONSHIPS,
                },
                {"key": "full_name", "label": "Beneficiary full name", "required": False, "type": "text"},
                {"key": "dob", "label": "Beneficiary date of birth", "required": False, "type": "date"},
            ],
            "documents": [
                {
                    "type": "RELATIONSHIP_PROOF",
                    "label": "Relationship proof",
                    "required": False,
                    "required_when": {"field": "beneficiary.relationship", "exclude_values": ["SELF", ""]},
                },
            ],
        },
        {
            "id": "assistance",
            "title": "Verification Purpose",
            "hint": "This describes why you need verification — separate from assistance request categories.",
            "fields": [
                {
                    "key": "category",
                    "label": "Verification purpose",
                    "required": True,
                    "type": "select",
                    "options": [{"id": p["id"], "label": p["label"]} for p in KYC_ASSISTANCE_PURPOSE_OPTIONS],
                },
                {"key": "explanation", "label": "Brief explanation", "required": True, "type": "textarea"},
            ],
            "documents": [],
        },
        {
            "id": "purpose_documents",
            "title": "Supporting Documents",
            "dynamic_documents": True,
            "dynamic_documents_source": "kyc_purpose",
            "documents": [],
        },
        {
            "id": "bank",
            "title": "Bank Details",
            "hint": "Payments are sent to this account after an assistance request is approved.",
            "fields": [
                {"key": "account_holder_name", "label": "Account holder name", "required": True, "type": "text"},
                {"key": "bank_name", "label": "Bank name", "required": True, "type": "text"},
                {"key": "account_number", "label": "Account number", "required": True, "type": "text", "sensitive": True},
                {"key": "ifsc", "label": "IFSC code", "required": True, "type": "text"},
            ],
            "documents": [{"type": "BANK_PROOF", "label": "Bank proof", "required": True}],
        },
        {
            "id": "review",
            "title": "Review & Submit",
            "review": True,
            "fields": [],
            "documents": [],
        },
    ]


def build_receiver_kyc_config_response() -> dict[str, Any]:
    purposes = []
    for opt in KYC_ASSISTANCE_PURPOSE_OPTIONS:
        docs = get_kyc_purpose_documents(opt["id"])
        purposes.append({
            "code": opt["id"],
            "name": opt["label"],
            "description": opt["description"],
            "required_documents": [d for d in docs if d.get("required")],
            "optional_documents": [d for d in docs if not d.get("required")],
        })
    return {
        "version": "1",
        "purposes": purposes,
        "identity_document_types": IDENTITY_DOCUMENT_TYPES,
        "address_proof_types": ADDRESS_PROOF_TYPES,
        "beneficiary_relationships": BENEFICIARY_RELATIONSHIPS,
        "payment_destination_types": PAYMENT_DESTINATION_TYPES,
        "base_documents": _BASE_DOCUMENTS,
        "progress_steps": RECEIVER_PROGRESS_STEPS,
        "wizard_steps": build_receiver_kyc_wizard_steps(),
        "consent_version": "kyc-v1",
        "consent_text": (
            "I confirm that the information and documents I have provided are accurate and belong to me "
            "or the stated beneficiary. I authorize AJA Abayahastham to verify my identity and process my "
            "documents for assistance review and disbursement."
        ),
        "upload_limits": {
            "max_bytes": 10 * 1024 * 1024,
            "allowed_extensions": [".pdf", ".jpg", ".jpeg", ".png", ".webp"],
            "allowed_mime_types": ["application/pdf", "image/jpeg", "image/png", "image/webp"],
        },
    }


__all__ = [
    "ASSISTANCE_CATEGORIES",
    "BENEFICIARY_RELATIONSHIPS",
    "IDENTITY_DOCUMENT_TYPES",
    "KYC_ASSISTANCE_PURPOSE_OPTIONS",
    "KYC_PURPOSE_CODES",
    "PAYMENT_DESTINATION_TYPES",
    "RECEIVER_PROGRESS_STEPS",
    "build_receiver_kyc_config_response",
    "get_all_required_document_types",
    "get_category_documents",
    "get_kyc_purpose_documents",
    "normalize_kyc_purpose",
]
