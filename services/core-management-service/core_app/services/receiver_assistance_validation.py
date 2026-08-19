"""Strict receiver assistance application validation."""

from __future__ import annotations

import re
from typing import Any

from core_app.services.receiver_assistance_config import (
    MAX_AMOUNT_REQUESTED,
    MIN_AMOUNT_REQUESTED,
    MIN_PURPOSE_LENGTH,
    VAGUE_PURPOSE_PATTERNS,
    get_category,
    get_strictly_required_document_types,
    validate_assistance_category,
)

FieldError = dict[str, str]

_EXPENSE_AMOUNT_RE = re.compile(r"₹?\s*([0-9][0-9,]*(?:\.[0-9]+)?)")


def _err(field: str, message: str, *, code: str | None = None) -> FieldError:
    out: FieldError = {"field": field, "message": message}
    if code:
        out["code"] = code
    return out


def _parse_expense_amounts(text: str) -> list[float]:
    return [
        float(m.group(1).replace(",", ""))
        for m in _EXPENSE_AMOUNT_RE.finditer(text or "")
    ]


def validate_assistance_application(
    *,
    purpose: str | None,
    amount_requested: float | None,
    category: str | None,
    expense_breakdown: str | None = None,
    uploaded_document_types: list[str] | None = None,
) -> list[FieldError]:
    errors: list[FieldError] = []
    uploaded = set(uploaded_document_types or [])

    canonical_category: str | None = None
    try:
        canonical_category = validate_assistance_category(category)
    except ValueError as exc:
        errors.append(_err("category", str(exc), code="INVALID_CATEGORY"))

    purpose_text = (purpose or "").strip()
    if not purpose_text:
        errors.append(
            _err("purpose", "Please describe what you need assistance for.", code="FIELD_REQUIRED")
        )
    elif any(pattern.search(purpose_text) for pattern in VAGUE_PURPOSE_PATTERNS):
        errors.append(
            _err(
                "purpose",
                "Please be specific about how the funds will be used.",
                code="INVALID_PURPOSE",
            )
        )
    elif len(purpose_text) < MIN_PURPOSE_LENGTH:
        errors.append(
            _err(
                "purpose",
                f"Please provide at least {MIN_PURPOSE_LENGTH} characters explaining your need.",
                code="PURPOSE_TOO_SHORT",
            )
        )

    amount: float | None = None
    if amount_requested is None:
        errors.append(_err("amount", "Enter the amount you are requesting.", code="FIELD_REQUIRED"))
    else:
        try:
            amount = float(amount_requested)
        except (TypeError, ValueError):
            errors.append(_err("amount", "Enter a valid amount.", code="INVALID_AMOUNT"))
        if amount is not None:
            if amount <= 0:
                errors.append(
                    _err("amount", "Amount must be greater than zero.", code="INVALID_AMOUNT")
                )
            elif amount < MIN_AMOUNT_REQUESTED:
                errors.append(
                    _err(
                        "amount",
                        f"Minimum request amount is ₹{MIN_AMOUNT_REQUESTED:,.0f}.",
                        code="AMOUNT_TOO_LOW",
                    )
                )
            elif amount > MAX_AMOUNT_REQUESTED:
                errors.append(
                    _err(
                        "amount",
                        f"Maximum request amount is ₹{MAX_AMOUNT_REQUESTED:,.0f}.",
                        code="AMOUNT_TOO_HIGH",
                    )
                )

    category_spec = get_category(canonical_category) if canonical_category else None
    if category_spec and category_spec.get("requires_detailed_explanation"):
        breakdown = (expense_breakdown or "").strip()
        if not breakdown:
            errors.append(
                _err(
                    "expense_breakdown",
                    "Please provide an expense breakdown.",
                    code="FIELD_REQUIRED",
                )
            )
        elif len(breakdown) < 10:
            errors.append(
                _err(
                    "expense_breakdown",
                    "Please add more detail to your expense breakdown.",
                    code="EXPENSE_TOO_SHORT",
                )
            )
        elif amount is not None and amount > 0:
            expense_amounts = _parse_expense_amounts(breakdown)
            if expense_amounts:
                total = sum(expense_amounts)
                if total > amount * 1.05:
                    errors.append(
                        _err(
                            "expense_breakdown",
                            "Expense breakdown total should not exceed the requested amount.",
                            code="EXPENSE_EXCEEDS_AMOUNT",
                        )
                    )

    if canonical_category:
        for doc_type in get_strictly_required_document_types(canonical_category):
            if doc_type not in uploaded:
                label = doc_type.replace("_", " ").title()
                errors.append(
                    _err(
                        f"document.{doc_type}",
                        f"Please upload: {label}.",
                        code="DOCUMENT_REQUIRED",
                    )
                )

    return errors


def build_assistance_readiness_response(
    *,
    purpose: str | None,
    amount_requested: float | None,
    category: str | None,
    expense_breakdown: str | None = None,
    uploaded_document_types: list[str] | None = None,
) -> dict[str, Any]:
    errors = validate_assistance_application(
        purpose=purpose,
        amount_requested=amount_requested,
        category=category,
        expense_breakdown=expense_breakdown,
        uploaded_document_types=uploaded_document_types,
    )
    canonical = None
    try:
        canonical = validate_assistance_category(category)
    except ValueError:
        pass
    required_docs = get_strictly_required_document_types(canonical) if canonical else []
    missing_documents = sorted(
        {e["field"].replace("document.", "") for e in errors if e["field"].startswith("document.")}
    )
    return {
        "ready": not errors,
        "errors": errors,
        "missing_documents": missing_documents,
        "required_document_types": required_docs,
        "uploaded_document_types": list(uploaded_document_types or []),
        "limits": {
            "min_amount": MIN_AMOUNT_REQUESTED,
            "max_amount": MAX_AMOUNT_REQUESTED,
            "min_purpose_length": MIN_PURPOSE_LENGTH,
        },
    }
