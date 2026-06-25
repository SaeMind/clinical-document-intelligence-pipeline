# Recruiter Walkthrough

## 30-Second Explanation

This project extracts structured clinical data from heterogeneous PDFs. It classifies the document type, chooses the right schema, extracts fields, validates with Pydantic, and scores results against manual ground truth.

## Why It Matters

Healthcare data is locked in PDFs. This pipeline demonstrates the exact skill stack needed for Clinical Data Scientist and RWE Analyst roles: document AI, structured data extraction, validation, error logging, and metric-based evaluation.

## What To Demo

```bash
pip install -r requirements.txt
pytest -q
python src/main.py --batch data/sample_documents
cat outputs/run_*/validation_report.json
```

## Strong Interview Talking Points

- I used schema-first design to prevent unbounded LLM output.
- I separated classification, extraction, validation, and storage for maintainability.
- I included gold-standard field-level metrics instead of relying on subjective output quality.
- I designed the repo with offline demo mode and a Claude Files API production path.
