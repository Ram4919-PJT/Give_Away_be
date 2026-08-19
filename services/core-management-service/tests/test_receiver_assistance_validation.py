"""Tests for receiver assistance application validation."""

import pytest

from core_app.services.receiver_assistance_validation import (
    build_assistance_readiness_response,
    validate_assistance_application,
)


def test_valid_application_no_doc_requirements():
    errors = validate_assistance_application(
        purpose="Need support for groceries and essential household items this month.",
        amount_requested=5000,
        category="FOOD_BASIC_NEEDS",
        expense_breakdown="Groceries ₹3000, utilities ₹2000",
        uploaded_document_types=[],
    )
    assert errors == []


def test_invalid_category():
    errors = validate_assistance_application(
        purpose="Need support for groceries and essential household items this month.",
        amount_requested=5000,
        category="not_real",
        expense_breakdown="Groceries ₹3000",
        uploaded_document_types=[],
    )
    assert any(e["code"] == "INVALID_CATEGORY" for e in errors)


def test_legacy_category_normalizes_via_validation():
    errors = validate_assistance_application(
        purpose="Need support for hospital treatment and medicines for my mother.",
        amount_requested=25000,
        category="medical",
        expense_breakdown="Hospital ₹20000, medicines ₹5000",
        uploaded_document_types=["MEDICAL_REPORT", "HOSPITAL_ESTIMATE"],
    )
    assert errors == []


def test_missing_purpose():
    errors = validate_assistance_application(
        purpose="",
        amount_requested=1000,
        category="EMERGENCY",
        expense_breakdown="Emergency travel ₹1000",
        uploaded_document_types=["EMERGENCY_EVIDENCE"],
    )
    assert any(e["code"] == "FIELD_REQUIRED" for e in errors)


def test_vague_purpose_rejected():
    errors = validate_assistance_application(
        purpose="financial help",
        amount_requested=1000,
        category="EMERGENCY",
        expense_breakdown="Emergency travel ₹1000",
        uploaded_document_types=["EMERGENCY_EVIDENCE"],
    )
    assert any(e["code"] == "INVALID_PURPOSE" for e in errors)


def test_amount_too_low():
    errors = validate_assistance_application(
        purpose="Need urgent support for emergency travel to hospital.",
        amount_requested=50,
        category="EMERGENCY",
        expense_breakdown="Travel ₹50",
        uploaded_document_types=["EMERGENCY_EVIDENCE"],
    )
    assert any(e["code"] == "AMOUNT_TOO_LOW" for e in errors)


def test_amount_too_high():
    errors = validate_assistance_application(
        purpose="Need urgent support for emergency travel to hospital.",
        amount_requested=1_000_000,
        category="EMERGENCY",
        expense_breakdown="Travel ₹1000000",
        uploaded_document_types=["EMERGENCY_EVIDENCE"],
    )
    assert any(e["code"] == "AMOUNT_TOO_HIGH" for e in errors)


def test_negative_amount():
    errors = validate_assistance_application(
        purpose="Need urgent support for emergency travel to hospital.",
        amount_requested=-100,
        category="EMERGENCY",
        expense_breakdown="Travel ₹100",
        uploaded_document_types=["EMERGENCY_EVIDENCE"],
    )
    assert any(e["code"] == "INVALID_AMOUNT" for e in errors)


def test_expense_exceeds_amount():
    errors = validate_assistance_application(
        purpose="Need support for hospital treatment and medicines for my mother.",
        amount_requested=10000,
        category="MEDICAL_HEALTHCARE",
        expense_breakdown="Hospital ₹15000",
        uploaded_document_types=["MEDICAL_REPORT", "HOSPITAL_ESTIMATE"],
    )
    assert any(e["code"] == "EXPENSE_EXCEEDS_AMOUNT" for e in errors)


def test_missing_required_document():
    errors = validate_assistance_application(
        purpose="Need support for hospital treatment and medicines for my mother.",
        amount_requested=25000,
        category="MEDICAL_HEALTHCARE",
        expense_breakdown="Hospital ₹20000, medicines ₹5000",
        uploaded_document_types=["MEDICAL_REPORT"],
    )
    assert any(e["code"] == "DOCUMENT_REQUIRED" for e in errors)


def test_readiness_response():
    result = build_assistance_readiness_response(
        purpose="Need support for hospital treatment and medicines for my mother.",
        amount_requested=25000,
        category="MEDICAL_HEALTHCARE",
        expense_breakdown="Hospital ₹20000, medicines ₹5000",
        uploaded_document_types=["MEDICAL_REPORT", "HOSPITAL_ESTIMATE"],
    )
    assert result["ready"] is True
    assert result["limits"]["max_amount"] == 500_000
