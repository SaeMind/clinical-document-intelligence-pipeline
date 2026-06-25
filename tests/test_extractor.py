"""Tests for demo-mode structured extraction from clinical PDF text.

These tests exist specifically to catch a class of bug found during review:
a demo parser that returns fixed, hardcoded values regardless of input,
rather than actually parsing the supplied document text. Each test below
uses input values that differ from any value that previously appeared as a
hardcoded default, so a regression back to hardcoded output would fail
these tests even if it happened to coincidentally match the original demo
PDFs.
"""

from extractor import DocumentExtractor
from document_classifier import DocumentType


def _extractor() -> DocumentExtractor:
    """Build an extractor in demo mode (no Anthropic client)."""

    return DocumentExtractor()


def test_parse_lab_results_extracts_real_values_not_hardcoded_defaults() -> None:
    """Lab test results must be parsed from text, not a fixed constant list.

    Uses test names/values that do not match any previously hardcoded
    default (Hemoglobin A1c / Creatinine) to prove the parser is reading
    the input rather than ignoring it.
    """

    text = (
        "LAB RESULTS\n"
        "Patient Name: Test Patient\n"
        "Patient ID: MRN-00001\n"
        "Date of Service: 2026-01-01\n"
        "Lab Name: Test Lab\n"
        "Ordering Physician: Dr. Test\n"
        "Specimen Type: Blood\n"
        "Test Results: Potassium 5.8 mEq/L Critical reference 3.5-5.0 mEq/L; "
        "White Blood Cell Count 11.2 cells/uL High reference 4.5-11.0 cells/uL\n"
        "Notes: none"
    )
    extractor = _extractor()
    result = extractor._parse_lab_results(text)

    assert len(result["test_results"]) == 2
    assert result["test_results"][0]["test_name"] == "Potassium"
    assert result["test_results"][0]["value"] == 5.8
    assert result["test_results"][0]["flag"] == "Critical"
    assert result["test_results"][1]["test_name"] == "White Blood Cell Count"
    assert result["test_results"][1]["value"] == 11.2
    assert result["test_results"][1]["flag"] == "High"
    # Explicitly assert the old hardcoded values are NOT present.
    test_names = {entry["test_name"] for entry in result["test_results"]}
    assert "Hemoglobin A1c" not in test_names
    assert "Creatinine" not in test_names


def test_parse_lab_results_returns_empty_list_when_no_test_results_present() -> None:
    """Absent test-results data should yield an empty list, not fabricated entries."""

    text = "LAB RESULTS\nPatient Name: Test Patient\nPatient ID: MRN-00002"
    extractor = _extractor()
    result = extractor._parse_lab_results(text)
    assert result["test_results"] == []


def test_parse_discharge_extracts_real_medications_not_hardcoded_defaults() -> None:
    """Discharge medications must be parsed from text, not a fixed constant list.

    Uses medications that do not match any previously hardcoded default
    (Metformin / Lisinopril) to prove the parser is reading the input.
    """

    text = (
        "DISCHARGE SUMMARY\n"
        "Admission Date: 2026-02-01\n"
        "Discharge Date: 2026-02-05\n"
        "Patient Name: Test Patient\n"
        "Patient ID: MRN-00003\n"
        "Primary Diagnosis: Test diagnosis\n"
        "Secondary Diagnoses: None\n"
        "Procedures Performed: None\n"
        "Discharge Medications: Atorvastatin 40 mg daily PO; Furosemide 20 mg BID PO\n"
        "Hospital Course: Uneventful\n"
        "Discharge Disposition: Home\n"
        "Follow-up Instructions: Cardiology within 14 days; Weigh daily\n"
        "Attending Physician: Dr. Test"
    )
    extractor = _extractor()
    result = extractor._parse_discharge(text)

    med_names = {med["name"] for med in result["discharge_medications"]}
    assert med_names == {"Atorvastatin", "Furosemide"}
    assert "Metformin" not in med_names
    assert "Lisinopril" not in med_names

    furosemide = next(m for m in result["discharge_medications"] if m["name"] == "Furosemide")
    assert furosemide["dose"] == "20 mg"
    assert furosemide["frequency"] == "BID"
    assert furosemide["route"] == "PO"


def test_parse_discharge_follow_up_appointments_derived_from_instructions() -> None:
    """Follow-up appointments must be derived from actual instruction text.

    Uses a specialist/timeframe pair that does not match the previously
    hardcoded default (Primary Care / 7 days) to prove the value is
    derived from input, not a fixed constant.
    """

    text = (
        "DISCHARGE SUMMARY\n"
        "Admission Date: 2026-02-01\n"
        "Discharge Date: 2026-02-05\n"
        "Patient Name: Test Patient\n"
        "Patient ID: MRN-00003\n"
        "Primary Diagnosis: Test diagnosis\n"
        "Secondary Diagnoses: None\n"
        "Procedures Performed: None\n"
        "Discharge Medications: Atorvastatin 40 mg daily PO\n"
        "Hospital Course: Uneventful\n"
        "Discharge Disposition: Home\n"
        "Follow-up Instructions: Cardiology within 14 days; Weigh daily\n"
        "Attending Physician: Dr. Test"
    )
    extractor = _extractor()
    result = extractor._parse_discharge(text)

    assert len(result["follow_up_appointments"]) == 1
    appt = result["follow_up_appointments"][0]
    assert appt["specialist"] == "Cardiology"
    assert appt["recommended_timeframe"] == "14 days"
    assert appt["specialist"] != "Primary Care"


def test_parse_discharge_no_appointment_inferred_when_no_timeframe_pattern() -> None:
    """Instructions without a 'within N days' pattern should not produce a fabricated appointment."""

    text = (
        "DISCHARGE SUMMARY\n"
        "Admission Date: 2026-02-01\n"
        "Discharge Date: 2026-02-05\n"
        "Patient Name: Test Patient\n"
        "Patient ID: MRN-00003\n"
        "Primary Diagnosis: Test diagnosis\n"
        "Secondary Diagnoses: None\n"
        "Procedures Performed: None\n"
        "Discharge Medications: Atorvastatin 40 mg daily PO\n"
        "Hospital Course: Uneventful\n"
        "Discharge Disposition: Home\n"
        "Follow-up Instructions: Monitor symptoms; Return for fever\n"
        "Attending Physician: Dr. Test"
    )
    extractor = _extractor()
    result = extractor._parse_discharge(text)
    assert result["follow_up_appointments"] == []


def test_extract_raises_for_missing_file(tmp_path) -> None:
    """Extraction should raise a clear error for a nonexistent PDF path."""

    extractor = _extractor()
    missing = tmp_path / "does_not_exist.pdf"
    try:
        extractor.extract(missing)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected FileNotFoundError for missing PDF")
