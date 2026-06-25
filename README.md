# Structured Output Document Intelligence Pipeline

A production-oriented clinical document intelligence pipeline that extracts structured data from heterogeneous healthcare PDFs using document classification, type-specific Pydantic schemas, structured LLM output, schema validation, and gold-standard evaluation.

**Portfolio positioning:** Clinical Data Science / Real-World Evidence / Healthcare AI Engineering artifact.

## Overview

Healthcare organizations process high volumes of PDFs: prior authorizations, lab results, referral letters, discharge summaries, and insurance explanation-of-benefits documents. This project demonstrates how to convert those unstructured clinical documents into validated, machine-readable JSON suitable for analytics, workflow automation, quality reporting, and downstream real-world evidence pipelines.

The repository includes a deterministic demo mode so reviewers can run the full pipeline without API credentials. Production mode supports Claude Files API extraction when `ANTHROPIC_API_KEY` is configured.

## Document Types Supported

| Document type | Core extracted fields |
|---|---|
| Prior Authorization | authorization number, member ID, procedure code, status, authorization/expiration dates, visits, clinical indication |
| Lab Results | patient ID, date of service, lab name, structured test results, units, reference ranges, abnormal flags |
| Referral Letter | referring physician, specialty, clinical indication, chief complaint, urgency, medications, allergies |
| Discharge Summary | diagnoses, procedures, medications, hospital course, disposition, follow-up instructions |
| Explanation of Benefits | claim ID, payer/provider, service date, billed/allowed/paid amounts, patient responsibility |

## Architecture

```text
[PDF File]
    ↓
[Text Extraction / Claude Files API]
    ↓
[Document Classification]
    ↓
[Type-Specific Pydantic Schema]
    ↓
[Structured Extraction]
    ↓
[Runtime Validation]
    ↓
[Structured JSONL + Validation Report + Error Log]
```

## Repository Structure

```text
document-intelligence-pipeline/
├── src/
│   ├── config.py
│   ├── document_classifier.py
│   ├── extractor.py
│   ├── main.py
│   ├── schemas.py
│   ├── storage.py
│   ├── utils.py
│   └── validator.py
├── data/
│   ├── sample_documents/
│   └── ground_truth/
├── docs/
│   └── architecture.md
├── outputs/
├── tests/
├── .github/workflows/ci.yml
├── .env.example
├── pyproject.toml
├── requirements.txt
└── README.md
```

## How to Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the offline demo pipeline:

```bash
python src/main.py --batch data/sample_documents
```

Run a single document:

```bash
python src/main.py --pdf data/sample_documents/prior_auth_1.pdf
```

Run tests:

```bash
pytest -q
```

Outputs are written to timestamped folders under `outputs/run_<timestamp>/`:

```text
extracted_data.jsonl
validation_report.json
error_log.json
```

## Claude Files API Mode

Demo mode is enabled by default. To run with Claude Files API:

```bash
cp .env.example .env
export DEMO_MODE=false
export ANTHROPIC_API_KEY=your_api_key_here
python src/main.py --pdf data/sample_documents/prior_auth_1.pdf
```

The production path uploads the PDF, supplies the appropriate schema to the model, requires JSON-only structured output, validates the response with Pydantic, and cleans up the uploaded file.

## Extraction Schemas

Schemas live in `src/schemas.py` and enforce:

- required fields per document type
- typed dates, floats, lists, nested objects
- enum-constrained status/urgency/flag fields
- forbidden extra fields to reduce hallucinated outputs
- procedure code plausibility checks

Example prior authorization output:

```json
{
  "pdf_file": "prior_auth_1.pdf",
  "document_type": "prior_authorization",
  "extracted_data": {
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
    "special_conditions": [
      "Use in-network provider",
      "Submit progress notes after fifth visit"
    ]
  },
  "confidence": 0.95,
  "valid": true,
  "errors": []
}
```

## Validation Results

The pipeline generates two evaluation layers:

1. **Schema validation:** whether each extraction conforms to its Pydantic schema.
2. **Gold-standard comparison:** exact-match field-level accuracy, precision, recall, and F1 against `data/ground_truth/*.json`.

This makes the project recruiter-legible: it is not just an LLM demo, it is an evaluated extraction system.

## Technologies Used

- Python 3.11+
- Anthropic Claude Files API
- Pydantic v2
- pypdf
- pytest
- GitHub Actions CI

## Recruiter Narrative

> Built a structured document intelligence pipeline for clinical PDFs that classifies document type, extracts schema-constrained JSON, validates outputs with Pydantic, and evaluates field-level accuracy against manual gold standards. The system supports prior authorizations, lab results, referral letters, discharge summaries, and insurance EOBs, with offline demo mode and Claude Files API production mode.
