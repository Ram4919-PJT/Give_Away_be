"""Canonical Receiver Financial Assistance configuration.

Single source of truth for assistance-request categories, document requirements,
and category validation.

KYC vs Assistance (important distinction)
---------------------------------------
* **KYC verification** collects identity, address, bank, and optional
  "assistance purpose" during onboarding. Legacy KYC purpose codes (e.g.
  ``MEDICAL``, ``BASIC_NEEDS``) are mapped to canonical codes via
  ``normalize_category_code``.
* **Assistance requests** (POST /core/applications) must use the 9 canonical
  codes defined in ``CANONICAL_ASSISTANCE_CATEGORIES``.

Mobile app note
---------------
The mobile wireframe uses a different 7-category list (includes Women & Child,
Senior Citizen). Those are not 1:1 with canonical codes — see
``MOBILE_LEGACY_CATEGORY_NOTES`` for documented mappings. Mobile should adopt
``GET /core/config/receiver-assistance`` in a future release.
"""

from __future__ import annotations

import re
from typing import Any

DocumentSpec = dict[str, Any]
CategorySpec = dict[str, Any]

CANONICAL_ASSISTANCE_CATEGORIES: tuple[str, ...] = (
    "MEDICAL_HEALTHCARE",
    "EDUCATION",
    "FOOD_BASIC_NEEDS",
    "HOUSING_SHELTER",
    "EMERGENCY",
    "DISABILITY_SUPPORT",
    "FAMILY_SUPPORT",
    "DISASTER_RELIEF",
    "OTHER",
)

MIN_AMOUNT_REQUESTED = 100
MAX_AMOUNT_REQUESTED = 500_000
MIN_PURPOSE_LENGTH = 20

VAGUE_PURPOSE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^i need money$", re.IGNORECASE),
    re.compile(r"^financial help$", re.IGNORECASE),
    re.compile(r"^please help me$", re.IGNORECASE),
    re.compile(r"^help me$", re.IGNORECASE),
    re.compile(r"^need help$", re.IGNORECASE),
    re.compile(r"^financial assistance$", re.IGNORECASE),
)

# Legacy aliases accepted at API boundaries and normalized to canonical codes.
_CATEGORY_ALIASES: dict[str, str] = {
    # Former web slugs (Give_away_fe receiverApplyConfig.js)
    "MEDICAL": "MEDICAL_HEALTHCARE",
    "FOOD": "FOOD_BASIC_NEEDS",
    "HOUSING": "HOUSING_SHELTER",
    "DISABILITY": "DISABILITY_SUPPORT",
    "FAMILY": "FAMILY_SUPPORT",
    "DISASTER": "DISASTER_RELIEF",
    # Legacy KYC intent codes (receiver_document_config / kycConfig.js)
    "BASIC_NEEDS": "FOOD_BASIC_NEEDS",
}

MOBILE_LEGACY_CATEGORY_NOTES: dict[str, str] = {
    "medical": "MEDICAL_HEALTHCARE",
    "education": "EDUCATION",
    "emergency": "EMERGENCY",
    "disability": "DISABILITY_SUPPORT",
    "other": "OTHER",
    "women-child": "FAMILY_SUPPORT — approximate; mobile-specific label",
    "senior": "OTHER — no canonical senior category; use OTHER with explanation",
}

_CATEGORIES: list[CategorySpec] = [
    {
        "code": "MEDICAL_HEALTHCARE",
        "name": "Medical & Healthcare",
        "description": "Hospital bills, medicines, diagnostics, and treatment-related expenses.",
        "active": True,
        "requires_detailed_explanation": True,
        "required_documents": [
            {"type": "MEDICAL_REPORT", "label": "Medical report / diagnosis", "required": True},
            {"type": "HOSPITAL_ESTIMATE", "label": "Hospital estimate or bill", "required": True},
        ],
        "optional_documents": [
            {"type": "PRESCRIPTION", "label": "Doctor prescription", "required": False},
            {"type": "DIAGNOSTIC_REPORT", "label": "Diagnostic report", "required": False},
        ],
        "conditional_documents": [
            {
                "type": "HOSPITAL_BILL",
                "label": "Hospital bill (if treatment already received)",
                "required": False,
                "condition": "where_applicable",
            },
        ],
    },
    {
        "code": "EDUCATION",
        "name": "Education",
        "description": "School or college fees, admission, and education-related costs.",
        "active": True,
        "requires_detailed_explanation": True,
        "required_documents": [
            {"type": "ADMISSION_LETTER", "label": "Admission letter", "required": True},
            {"type": "FEE_STRUCTURE", "label": "Fee structure or fee receipt", "required": True},
        ],
        "optional_documents": [
            {"type": "STUDENT_ID", "label": "Student ID", "required": False},
            {"type": "FEE_RECEIPT", "label": "Previous fee receipt", "required": False},
        ],
        "conditional_documents": [],
    },
    {
        "code": "FOOD_BASIC_NEEDS",
        "name": "Food & Basic Needs",
        "description": "Food, groceries, and essential daily living support.",
        "active": True,
        "requires_detailed_explanation": True,
        "required_documents": [],
        "optional_documents": [
            {"type": "SUPPORTING_PRIMARY", "label": "Supporting evidence of need", "required": False},
        ],
        "conditional_documents": [
            {
                "type": "SUPPORTING_PRIMARY",
                "label": "Relevant supporting proof where available",
                "required": False,
                "condition": "where_available",
            },
        ],
    },
    {
        "code": "HOUSING_SHELTER",
        "name": "Housing & Shelter",
        "description": "Rent, shelter, repairs, eviction, or housing emergency support.",
        "active": True,
        "requires_detailed_explanation": True,
        "required_documents": [],
        "optional_documents": [
            {"type": "SUPPORTING_PRIMARY", "label": "Housing or shelter supporting document", "required": False},
        ],
        "conditional_documents": [
            {"type": "RENT_AGREEMENT", "label": "Rent agreement", "required": False, "condition": "where_applicable"},
            {"type": "EVICTION_NOTICE", "label": "Eviction notice", "required": False, "condition": "where_applicable"},
            {"type": "REPAIR_ESTIMATE", "label": "Damage or repair estimate", "required": False, "condition": "where_applicable"},
        ],
    },
    {
        "code": "EMERGENCY",
        "name": "Emergency",
        "description": "Urgent crisis support requiring timely assistance.",
        "active": True,
        "requires_detailed_explanation": True,
        "required_documents": [
            {"type": "EMERGENCY_EVIDENCE", "label": "Emergency supporting document", "required": True},
        ],
        "optional_documents": [
            {"type": "MEDICAL_REPORT", "label": "Medical or emergency report", "required": False},
            {"type": "SUPPORTING_PRIMARY", "label": "Other supporting evidence", "required": False},
        ],
        "conditional_documents": [],
    },
    {
        "code": "DISABILITY_SUPPORT",
        "name": "Disability Support",
        "description": "Aid for persons with disabilities including medical and assistive needs.",
        "active": True,
        "requires_detailed_explanation": True,
        "required_documents": [],
        "optional_documents": [
            {"type": "DISABILITY_CERTIFICATE", "label": "Disability certificate", "required": False},
            {"type": "MEDICAL_REPORT", "label": "Medical or supporting documentation", "required": False},
        ],
        "conditional_documents": [
            {
                "type": "DISABILITY_CERTIFICATE",
                "label": "Disability certificate where available",
                "required": False,
                "condition": "where_available",
            },
        ],
    },
    {
        "code": "FAMILY_SUPPORT",
        "name": "Family Support",
        "description": "Support for family members in verified financial hardship.",
        "active": True,
        "requires_detailed_explanation": True,
        "required_documents": [],
        "optional_documents": [
            {"type": "SUPPORTING_PRIMARY", "label": "Relevant supporting documents", "required": False},
            {"type": "RELATIONSHIP_PROOF", "label": "Relationship or family proof", "required": False},
        ],
        "conditional_documents": [
            {
                "type": "RELATIONSHIP_PROOF",
                "label": "Relationship proof where applicable",
                "required": False,
                "condition": "where_applicable",
            },
        ],
    },
    {
        "code": "DISASTER_RELIEF",
        "name": "Disaster Relief",
        "description": "Recovery support after natural or community disasters.",
        "active": True,
        "requires_detailed_explanation": True,
        "required_documents": [],
        "optional_documents": [
            {"type": "SUPPORTING_PRIMARY", "label": "Damage or disaster evidence", "required": False},
        ],
        "conditional_documents": [
            {"type": "DAMAGE_EVIDENCE", "label": "Damage evidence (photos or reports)", "required": False, "condition": "where_available"},
            {"type": "AUTHORITY_DOCUMENT", "label": "Local authority documentation", "required": False, "condition": "where_available"},
        ],
    },
    {
        "code": "OTHER",
        "name": "Other",
        "description": "Other verified financial hardship not covered above.",
        "active": True,
        "requires_detailed_explanation": True,
        "required_documents": [],
        "optional_documents": [
            {"type": "SUPPORTING_PRIMARY", "label": "Relevant supporting evidence", "required": False},
        ],
        "conditional_documents": [],
    },
]

_BY_CODE: dict[str, CategorySpec] = {c["code"]: c for c in _CATEGORIES}


def normalize_category_code(raw: str | None) -> str | None:
    """Normalize legacy slug/code to a canonical assistance category code."""
    if raw is None:
        return None
    cleaned = str(raw).strip()
    if not cleaned:
        return None
    upper = cleaned.upper().replace("-", "_")
    if upper in _BY_CODE:
        return upper
    if upper in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[upper]
    lower = cleaned.lower()
    if lower in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[lower]
    # Web slugs (lowercase)
    slug_map = {
        "medical": "MEDICAL_HEALTHCARE",
        "education": "EDUCATION",
        "food": "FOOD_BASIC_NEEDS",
        "housing": "HOUSING_SHELTER",
        "emergency": "EMERGENCY",
        "disability": "DISABILITY_SUPPORT",
        "family": "FAMILY_SUPPORT",
        "disaster": "DISASTER_RELIEF",
        "other": "OTHER",
    }
    if lower in slug_map:
        return slug_map[lower]
    return None


def get_category(code: str) -> CategorySpec | None:
    canonical = normalize_category_code(code)
    if not canonical:
        return None
    return _BY_CODE.get(canonical)


def get_active_categories() -> list[CategorySpec]:
    return [dict(c) for c in _CATEGORIES if c.get("active", True)]


def get_category_document_types(code: str, *, include_optional: bool = False) -> list[DocumentSpec]:
    """Document types for KYC supporting docs or assistance evidence for a category."""
    category = get_category(code)
    if not category:
        return []
    docs: list[DocumentSpec] = []
    for doc in category.get("required_documents") or []:
        docs.append({**doc, "required": True})
    if include_optional:
        for doc in category.get("optional_documents") or []:
            docs.append({**doc, "required": False})
        for doc in category.get("conditional_documents") or []:
            docs.append({**doc, "required": False})
    return docs


def get_strictly_required_document_types(code: str) -> list[str]:
    """Document types that must be uploaded when category mandates them."""
    types: list[str] = []
    for doc in get_category_document_types(code, include_optional=False):
        if doc.get("required"):
            types.append(doc["type"])
    return types


def validate_assistance_category(raw: str | None) -> str:
    """Return canonical code or raise ValueError for invalid/inactive categories."""
    if raw is None or not str(raw).strip():
        raise ValueError("Assistance category is required")
    canonical = normalize_category_code(raw)
    if not canonical:
        raise ValueError(f"Unknown assistance category: {raw}")
    category = _BY_CODE.get(canonical)
    if not category or not category.get("active", True):
        raise ValueError(f"Assistance category is not available: {canonical}")
    return canonical


def build_receiver_assistance_config_response() -> dict[str, Any]:
    """Public API payload for GET /core/config/receiver-assistance."""
    categories = []
    for cat in get_active_categories():
        categories.append({
            "code": cat["code"],
            "name": cat["name"],
            "description": cat["description"],
            "requires_detailed_explanation": cat.get("requires_detailed_explanation", True),
            "required_documents": list(cat.get("required_documents") or []),
            "optional_documents": list(cat.get("optional_documents") or []),
            "conditional_documents": list(cat.get("conditional_documents") or []),
        })
    return {
        "categories": categories,
        "version": "1",
        "limits": {
            "min_amount": MIN_AMOUNT_REQUESTED,
            "max_amount": MAX_AMOUNT_REQUESTED,
            "min_purpose_length": MIN_PURPOSE_LENGTH,
            "currency": "INR",
        },
    }
