"""Structured data extraction from clinical PDFs."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - optional production dependency
    Anthropic = None  # type: ignore[assignment]
from pydantic import BaseModel

from config import Settings, get_settings
from document_classifier import DocumentClassifier, DocumentType
from schemas import SCHEMA_BY_DOCUMENT_TYPE
from utils import extract_pdf_text
from validator import ExtractionValidator

logger = logging.getLogger(__name__)


class DocumentExtractor:
    """Extract structured data from clinical PDFs.

    The extractor supports two execution modes:
    1. demo mode: deterministic local parsing for portfolio review and tests.
    2. Claude mode: Anthropic Files API + schema-guided structured extraction.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize extractor dependencies.

        Args:
            settings: Optional runtime settings. Defaults to environment-derived settings.
        """

        self.settings = settings or get_settings()
        self.classifier = DocumentClassifier()
        self.validator = ExtractionValidator()
        self.client = (
            Anthropic(api_key=self.settings.anthropic_api_key)
            if Anthropic is not None
            and self.settings.anthropic_api_key
            and not self.settings.demo_mode
            else None
        )

    def extract(self, pdf_path: Path) -> dict[str, Any]:
        """Extract and validate structured data from one PDF.

        Args:
            pdf_path: Path to a PDF document.

        Returns:
            Extraction record containing document type, payload, confidence, and errors.
        """

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        document_text = extract_pdf_text(pdf_path)
        doc_type = self.classifier.classify(document_text)
        schema = SCHEMA_BY_DOCUMENT_TYPE.get(doc_type.value)
        if schema is None:
            return self._failure_record(pdf_path, doc_type, "Unsupported or unknown document type")
        raw_data = (
            self._extract_demo(document_text, doc_type)
            if self.client is None
            else self._extract_with_claude(pdf_path, doc_type, schema)
        )
        validation = self.validator.validate(raw_data, schema)
        return {
            "pdf_file": pdf_path.name,
            "document_type": doc_type.value,
            "extracted_data": validation.normalized_data or raw_data,
            "confidence": validation.confidence,
            "valid": validation.valid,
            "errors": validation.errors,
        }

    def _extract_with_claude(
        self,
        pdf_path: Path,
        doc_type: DocumentType,
        schema: type[BaseModel],
    ) -> dict[str, Any]:
        """Extract structured data using Anthropic Files API.

        Args:
            pdf_path: PDF path to upload.
            doc_type: Classified document type.
            schema: Pydantic schema used to construct the extraction prompt.

        Returns:
            Parsed JSON dictionary from the model response.
        """

        assert self.client is not None
        with pdf_path.open("rb") as file:
            uploaded = self.client.beta.files.upload(
                file=(pdf_path.name, file, "application/pdf")
            )
        schema_json = schema.model_json_schema()
        prompt = (
            f"Extract all fields from this {doc_type.value} document. "
            "Return only valid JSON matching the supplied JSON schema. "
            "Do not include markdown, explanations, or extra keys.\n\n"
            f"JSON schema:\n{json.dumps(schema_json, indent=2)}"
        )
        try:
            message = self.client.beta.messages.create(
                model=self.settings.anthropic_model,
                max_tokens=3000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {"type": "file", "file_id": uploaded.id},
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
            response_text = message.content[0].text
            return self._parse_model_json(response_text)
        finally:
            try:
                self.client.beta.files.delete(uploaded.id)
            except Exception as error:  # pragma: no cover - best effort cleanup
                logger.warning("Could not delete uploaded file %s: %s", uploaded.id, error)

    def _extract_demo(self, document_text: str, doc_type: DocumentType) -> dict[str, Any]:
        """Extract structured data with deterministic regex rules for demo documents.

        Args:
            document_text: Text extracted from PDF.
            doc_type: Classified document type.

        Returns:
            Structured extraction dictionary.
        """

        parsers = {
            DocumentType.PRIOR_AUTH: self._parse_prior_auth,
            DocumentType.LAB_RESULTS: self._parse_lab_results,
            DocumentType.REFERRAL: self._parse_referral,
            DocumentType.DISCHARGE: self._parse_discharge,
            DocumentType.EOB: self._parse_eob,
        }
        return parsers[doc_type](document_text)

    def _field(self, text: str, label: str, default: str = "") -> str:
        """Extract a labeled line from demo text.

        Args:
            text: Document text.
            label: Label before a colon.
            default: Default value when missing.

        Returns:
            Extracted string value.
        """

        match = re.search(rf"{re.escape(label)}:\s*(.+)", text)
        return match.group(1).strip() if match else default

    def _list_field(self, text: str, label: str) -> list[str]:
        """Extract a semicolon-delimited list field.

        Args:
            text: Document text.
            label: Label before a colon.

        Returns:
            List of extracted items.
        """

        value = self._field(text, label)
        return [item.strip() for item in value.split(";") if item.strip()]

    def _parse_prior_auth(self, text: str) -> dict[str, Any]:
        """Parse a synthetic prior authorization PDF."""

        return {
            "authorization_number": self._field(text, "Authorization Number"),
            "member_id": self._field(text, "Member ID"),
            "member_name": self._field(text, "Member Name"),
            "procedure_code": self._field(text, "Procedure Code"),
            "procedure_description": self._field(text, "Procedure Description"),
            "requesting_physician": self._field(text, "Requesting Physician"),
            "facility": self._field(text, "Facility"),
            "authorization_date": self._field(text, "Authorization Date"),
            "expiration_date": self._field(text, "Expiration Date"),
            "auth_status": self._field(text, "Auth Status").lower(),
            "number_of_visits": int(self._field(text, "Number of Visits", "0")),
            "clinical_indication": self._field(text, "Clinical Indication"),
            "special_conditions": self._list_field(text, "Special Conditions"),
        }

    def _parse_test_results(self, text: str) -> list[dict[str, Any]]:
        """Parse semicolon-delimited lab test result entries from demo text.

        Expected source format per entry:
            "<Name> <value> <unit> <Flag> reference <low>-<high><unit-suffix>"
        e.g. "Hemoglobin A1c 7.2 % High reference 4.0-5.6%"

        Args:
            text: Full document text.

        Returns:
            List of structured test-result dictionaries. Returns an empty
            list (not fabricated data) if the "Test Results:" line is
            absent or no entry matches the expected pattern.
        """

        raw = self._field(text, "Test Results")
        if not raw:
            return []
        results = []
        pattern = re.compile(
            r"(?P<name>[A-Za-z0-9 ]+?)\s+"
            r"(?P<value>-?\d+(?:\.\d+)?)\s+"
            r"(?P<unit>%|mg/dL|mmol/L|g/dL|mEq/L|U/L|ng/mL|pg/mL|/uL|cells/uL)\s+"
            r"(?P<flag>High|Low|Normal|Critical)\s+"
            r"reference\s+(?P<ref>[^;]+)",
            re.IGNORECASE,
        )
        for match in pattern.finditer(raw):
            results.append({
                "test_name": match.group("name").strip(),
                "value": float(match.group("value")),
                "unit": match.group("unit"),
                "reference_range": match.group("ref").strip().rstrip(";").strip(),
                "flag": match.group("flag").title(),
            })
        return results

    def _parse_lab_results(self, text: str) -> dict[str, Any]:
        """Parse a synthetic lab result PDF."""

        return {
            "patient_name": self._field(text, "Patient Name"),
            "patient_id": self._field(text, "Patient ID"),
            "date_of_service": self._field(text, "Date of Service"),
            "lab_name": self._field(text, "Lab Name"),
            "test_results": self._parse_test_results(text),
            "ordering_physician": self._field(text, "Ordering Physician"),
            "specimen_type": self._field(text, "Specimen Type"),
            "notes": self._field(text, "Notes"),
        }

    def _parse_referral(self, text: str) -> dict[str, Any]:
        """Parse a synthetic referral letter PDF."""

        return {
            "referral_date": self._field(text, "Referral Date"),
            "referring_physician": self._field(text, "Referring Physician"),
            "referring_facility": self._field(text, "Referring Facility"),
            "specialist_name": self._field(text, "Specialist Name"),
            "specialty_requested": self._field(text, "Specialty Requested"),
            "patient_name": self._field(text, "Patient Name"),
            "patient_id": self._field(text, "Patient ID"),
            "date_of_birth": self._field(text, "Date of Birth"),
            "insurance_info": self._field(text, "Insurance Info"),
            "clinical_indication": self._field(text, "Clinical Indication"),
            "chief_complaint": self._field(text, "Chief Complaint"),
            "relevant_history": self._field(text, "Relevant History"),
            "current_medications": self._list_field(text, "Current Medications"),
            "allergies": self._list_field(text, "Allergies"),
            "urgency": self._field(text, "Urgency").lower(),
            "requested_timeframe": self._field(text, "Requested Timeframe"),
            "prior_tests_imaging": self._field(text, "Prior Tests/Imaging"),
        }

    def _parse_medications(self, text: str) -> list[dict[str, Any]]:
        """Parse semicolon-delimited discharge medication entries from demo text.

        Expected source format per entry: "<Name> <dose> <frequency> <route>"
        e.g. "Metformin 500 mg BID PO" or "Lisinopril 10 mg daily PO".

        Args:
            text: Full document text.

        Returns:
            List of structured medication dictionaries. Returns an empty
            list (not fabricated data) if no entry matches the expected
            pattern.
        """

        raw = self._field(text, "Discharge Medications")
        if not raw:
            return []
        medications = []
        pattern = re.compile(
            r"(?P<name>[A-Za-z][A-Za-z\-]*)\s+"
            r"(?P<dose>\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|units))\s+"
            r"(?P<frequency>BID|TID|QID|daily|Daily|weekly|Weekly|q\d+h|PRN)\s+"
            r"(?P<route>PO|IV|IM|SC|SL|topical)",
            re.IGNORECASE,
        )
        for match in pattern.finditer(raw):
            frequency = match.group("frequency")
            frequency = frequency.upper() if frequency.upper() in {"BID", "TID", "QID", "PRN"} else frequency.capitalize()
            medications.append({
                "name": match.group("name").strip(),
                "dose": match.group("dose").strip(),
                "frequency": frequency,
                "route": match.group("route").upper(),
            })
        return medications

    def _parse_follow_up_appointments(self, follow_up_instructions: list[str]) -> list[dict[str, Any]]:
        """Derive structured follow-up appointments from free-text instructions.

        This is a best-effort heuristic: discharge summaries in this demo
        corpus do not contain a separately labeled appointments section, so
        an appointment record is inferred only when an instruction names a
        specialist/department and a recommended timeframe (e.g. "Primary
        care within 7 days"). Instructions that don't match this pattern
        (e.g. "Check glucose twice daily") are not converted into a
        fabricated appointment.

        Args:
            follow_up_instructions: Parsed list of follow-up instruction strings.

        Returns:
            List of structured appointment dictionaries (possibly empty).
        """

        appointments = []
        pattern = re.compile(
            r"(?P<specialist>[A-Za-z][A-Za-z ]*?)\s+within\s+(?P<timeframe>\d+\s*\w+)",
            re.IGNORECASE,
        )
        for instruction in follow_up_instructions:
            match = pattern.search(instruction)
            if match:
                appointments.append({
                    "specialist": match.group("specialist").strip().title(),
                    "reason": "Post-discharge follow-up",
                    "recommended_timeframe": match.group("timeframe").strip(),
                })
        return appointments

    def _parse_discharge(self, text: str) -> dict[str, Any]:
        """Parse a synthetic discharge summary PDF."""

        follow_up_instructions = self._list_field(text, "Follow-up Instructions")
        return {
            "discharge_date": self._field(text, "Discharge Date"),
            "admission_date": self._field(text, "Admission Date"),
            "patient_name": self._field(text, "Patient Name"),
            "patient_id": self._field(text, "Patient ID"),
            "primary_diagnosis": self._field(text, "Primary Diagnosis"),
            "secondary_diagnoses": self._list_field(text, "Secondary Diagnoses"),
            "procedures_performed": self._list_field(text, "Procedures Performed"),
            "discharge_medications": self._parse_medications(text),
            "hospital_course": self._field(text, "Hospital Course"),
            "discharge_disposition": self._field(text, "Discharge Disposition"),
            "follow_up_instructions": follow_up_instructions,
            "follow_up_appointments": self._parse_follow_up_appointments(follow_up_instructions),
            "attending_physician": self._field(text, "Attending Physician"),
        }

    def _parse_eob(self, text: str) -> dict[str, Any]:
        """Parse a synthetic explanation of benefits PDF."""

        money = lambda label: float(self._field(text, label, "0").replace("$", ""))
        return {
            "claim_id": self._field(text, "Claim ID"),
            "member_id": self._field(text, "Member ID"),
            "member_name": self._field(text, "Member Name"),
            "payer_name": self._field(text, "Payer Name"),
            "provider_name": self._field(text, "Provider Name"),
            "service_date": self._field(text, "Service Date"),
            "procedure_code": self._field(text, "Procedure Code"),
            "billed_amount": money("Billed Amount"),
            "allowed_amount": money("Allowed Amount"),
            "amount_paid": money("Amount Paid"),
            "patient_responsibility": money("Patient Responsibility"),
            "deductible_applied": money("Deductible Applied"),
            "copay": money("Copay"),
            "coinsurance": money("Coinsurance"),
            "denial_reason": self._field(text, "Denial Reason") or None,
        }

    def _parse_model_json(self, response_text: str) -> dict[str, Any]:
        """Parse JSON from a model response.

        Args:
            response_text: Raw model response text.

        Returns:
            Parsed JSON object.
        """

        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.removeprefix("json").strip()
        return json.loads(cleaned)

    def _failure_record(self, pdf_path: Path, doc_type: DocumentType, error: str) -> dict[str, Any]:
        """Create a standardized failure record.

        Args:
            pdf_path: Failed PDF path.
            doc_type: Classified document type.
            error: Error description.

        Returns:
            Failure record dictionary.
        """

        return {
            "pdf_file": pdf_path.name,
            "document_type": doc_type.value,
            "extracted_data": None,
            "confidence": 0.0,
            "valid": False,
            "errors": [error],
        }
