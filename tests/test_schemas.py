"""Tests for Pydantic schema validation."""

from schemas import PriorAuthSchema


def test_prior_auth_schema_accepts_valid_payload() -> None:
    """PriorAuthSchema should accept a complete valid payload."""

    payload = {
        "authorization_number": "PA-2026-001234",
        "member_id": "M123456789",
        "member_name": "John Smith",
        "procedure_code": "99213",
        "procedure_description": "Office visit, established patient",
        "requesting_physician": "Dr. Jane Doe, NPI 1234567890",
        "facility": "Primary Care Clinic",
        "authorization_date": "2026-06-15",
        "expiration_date": "2026-12-15",
        "auth_status": "approved",
        "number_of_visits": 5,
        "clinical_indication": "Management of hypertension and diabetes",
        "special_conditions": ["Use in-network provider"],
    }
    parsed = PriorAuthSchema.model_validate(payload)
    assert parsed.authorization_number == "PA-2026-001234"


def test_prior_auth_schema_rejects_bad_procedure_code() -> None:
    """PriorAuthSchema should reject implausible procedure code prefixes."""

    payload = {
        "authorization_number": "PA-2026-001234",
        "member_id": "M123456789",
        "member_name": "John Smith",
        "procedure_code": "ABC123",
        "procedure_description": "Office visit, established patient",
        "requesting_physician": "Dr. Jane Doe, NPI 1234567890",
        "authorization_date": "2026-06-15",
        "expiration_date": "2026-12-15",
        "auth_status": "approved",
    }
    try:
        PriorAuthSchema.model_validate(payload)
    except ValueError as error:
        assert "Invalid procedure code" in str(error)
    else:
        raise AssertionError("Expected schema validation to fail")
