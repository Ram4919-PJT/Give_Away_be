"""Tests for canonical receiver assistance configuration."""

import pytest
from fastapi.testclient import TestClient

from core_app.main import register_core
from fastapi import FastAPI

from core_app.services.kyc.receiver_document_config import (
    get_all_required_document_types,
    get_category_documents,
)
from core_app.services.receiver_assistance_config import (
    CANONICAL_ASSISTANCE_CATEGORIES,
    build_receiver_assistance_config_response,
    get_active_categories,
    normalize_category_code,
    validate_assistance_category,
)


@pytest.fixture
def client():
    app = FastAPI()
    register_core(app)
    return TestClient(app)


def test_all_nine_canonical_categories_present():
    active = get_active_categories()
    codes = {c["code"] for c in active}
    assert codes == set(CANONICAL_ASSISTANCE_CATEGORIES)
    assert len(active) == 9


def test_category_codes_are_stable():
    assert CANONICAL_ASSISTANCE_CATEGORIES == (
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


def test_normalize_legacy_web_slugs_and_kyc_codes():
    assert normalize_category_code("medical") == "MEDICAL_HEALTHCARE"
    assert normalize_category_code("MEDICAL") == "MEDICAL_HEALTHCARE"
    assert normalize_category_code("BASIC_NEEDS") == "FOOD_BASIC_NEEDS"
    assert normalize_category_code("MEDICAL_HEALTHCARE") == "MEDICAL_HEALTHCARE"


def test_validate_rejects_unknown_category():
    with pytest.raises(ValueError, match="Unknown assistance category"):
        validate_assistance_category("INVALID_CODE")


def test_validate_rejects_empty_category():
    with pytest.raises(ValueError, match="required"):
        validate_assistance_category("")


def test_validate_accepts_legacy_slug():
    assert validate_assistance_category("education") == "EDUCATION"


def test_config_response_includes_document_requirements():
    payload = build_receiver_assistance_config_response()
    medical = next(c for c in payload["categories"] if c["code"] == "MEDICAL_HEALTHCARE")
    assert any(d["type"] == "MEDICAL_REPORT" for d in medical["required_documents"])
    assert any(d["type"] == "PRESCRIPTION" for d in medical["optional_documents"])


def test_get_receiver_assistance_config_endpoint(client):
    response = client.get("/api/v1/core/config/receiver-assistance")
    assert response.status_code == 200
    data = response.json()
    assert len(data["categories"]) == 9
    assert data["categories"][0]["code"] in CANONICAL_ASSISTANCE_CATEGORIES
    assert "required_documents" in data["categories"][0]


def test_get_receiver_kyc_config_endpoint(client):
    response = client.get("/api/v1/core/config/receiver-kyc")
    assert response.status_code == 200
    data = response.json()
    assert len(data["purposes"]) == 5
    assert data["purposes"][0]["code"] in {"MEDICAL", "EDUCATION", "EMERGENCY", "BASIC_NEEDS", "OTHER"}
    assert "base_documents" in data


def test_kyc_document_lookup_uses_canonical_mapping():
    docs = get_category_documents("MEDICAL")
    types = {d["type"] for d in docs}
    assert "MEDICAL_REPORT" in types


def test_kyc_required_documents_for_legacy_medical_payload():
    required = get_all_required_document_types({
        "assistance": {"category": "MEDICAL"},
        "beneficiary": {"relationship": "SELF"},
    })
    assert "ID_FRONT" in required
    assert "MEDICAL_REPORT" in required


def test_assistance_create_schema_rejects_unknown_category():
    from core_app.schemas.assistance_application import AssistanceApplicationCreate

    with pytest.raises(ValueError):
        AssistanceApplicationCreate(
            purpose="Need support for hospital treatment and medicines for my mother.",
            amount_requested=25000,
            category="not_a_real_category",
        )


def test_assistance_create_schema_accepts_canonical_code():
    from core_app.schemas.assistance_application import AssistanceApplicationCreate

    model = AssistanceApplicationCreate(
        purpose="Need support for hospital treatment and medicines for my mother.",
        amount_requested=25000,
        category="MEDICAL_HEALTHCARE",
    )
    assert model.category == "MEDICAL_HEALTHCARE"
