"""Pydantic schemas for structured clinical document extraction."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictHealthcareModel(BaseModel):
    """Base model that forbids hallucinated fields and validates assignment."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class LabTestResult(StrictHealthcareModel):
    """Single lab test result extracted from a lab report."""

    test_name: str = Field(..., min_length=1)
    value: float | str
    unit: str | None = None
    reference_range: str | None = None
    flag: Literal["Low", "High", "Critical", "Normal"] | None = None


class Medication(StrictHealthcareModel):
    """Medication entry extracted from a discharge summary."""

    name: str
    dose: str
    frequency: str
    route: str | None = None


class FollowUpAppointment(StrictHealthcareModel):
    """Follow-up appointment recommendation."""

    specialist: str
    reason: str
    recommended_timeframe: str


class PriorAuthSchema(StrictHealthcareModel):
    """Schema for prior authorization documents."""

    authorization_number: str
    member_id: str
    member_name: str
    procedure_code: str
    procedure_description: str
    requesting_physician: str
    facility: str | None = None
    authorization_date: date
    expiration_date: date
    auth_status: Literal["approved", "conditional", "denied", "pending"]
    number_of_visits: int | None = Field(default=None, ge=0)
    clinical_indication: str | None = None
    special_conditions: list[str] | None = None

    @field_validator("procedure_code")
    @classmethod
    def validate_procedure_code(cls, value: str) -> str:
        """Validate CPT/ICD-style procedure code format.

        Args:
            value: Extracted procedure code.

        Returns:
            Original procedure code when valid.

        Raises:
            ValueError: If the code pattern is not plausible.
        """

        valid_prefixes = ("9", "I", "J", "C", "G")
        if not value.upper().startswith(valid_prefixes):
            raise ValueError("Invalid procedure code format")
        return value


class LabResultSchema(StrictHealthcareModel):
    """Schema for lab result documents."""

    patient_name: str
    patient_id: str
    date_of_service: date
    lab_name: str
    test_results: list[LabTestResult]
    ordering_physician: str
    specimen_type: str
    notes: str | None = None


class ReferralLetterSchema(StrictHealthcareModel):
    """Schema for specialist referral letters."""

    referral_date: date
    referring_physician: str
    referring_facility: str
    specialist_name: str | None = None
    specialty_requested: str
    patient_name: str
    patient_id: str
    date_of_birth: date | None = None
    insurance_info: str | None = None
    clinical_indication: str
    chief_complaint: str
    relevant_history: str
    current_medications: list[str] | None = None
    allergies: list[str] | None = None
    urgency: Literal["routine", "urgent", "emergent"]
    requested_timeframe: str | None = None
    prior_tests_imaging: str | None = None


class DischargeSummarySchema(StrictHealthcareModel):
    """Schema for hospital discharge summaries."""

    discharge_date: date
    admission_date: date
    patient_name: str
    patient_id: str
    primary_diagnosis: str
    secondary_diagnoses: list[str]
    procedures_performed: list[str]
    discharge_medications: list[Medication]
    hospital_course: str
    physical_exam_discharge: str | None = None
    lab_results_discharge: list[LabTestResult] | None = None
    imaging_results: list[str] | None = None
    discharge_disposition: str
    follow_up_instructions: list[str]
    follow_up_appointments: list[FollowUpAppointment] | None = None
    special_instructions: str | None = None
    attending_physician: str


class ExplanationOfBenefitsSchema(StrictHealthcareModel):
    """Schema for insurance explanation of benefits documents."""

    claim_id: str
    member_id: str
    member_name: str
    payer_name: str
    provider_name: str
    service_date: date
    procedure_code: str
    billed_amount: float = Field(..., ge=0)
    allowed_amount: float = Field(..., ge=0)
    amount_paid: float = Field(..., ge=0)
    patient_responsibility: float = Field(..., ge=0)
    deductible_applied: float | None = Field(default=None, ge=0)
    copay: float | None = Field(default=None, ge=0)
    coinsurance: float | None = Field(default=None, ge=0)
    denial_reason: str | None = None


SCHEMA_BY_DOCUMENT_TYPE = {
    "prior_authorization": PriorAuthSchema,
    "lab_results": LabResultSchema,
    "referral_letter": ReferralLetterSchema,
    "discharge_summary": DischargeSummarySchema,
    "explanation_of_benefits": ExplanationOfBenefitsSchema,
}
