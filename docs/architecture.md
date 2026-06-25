# Architecture Document

## Problem Statement

Clinical workflows depend on unstructured PDFs that are difficult to query, validate, or integrate into analytics systems. This pipeline converts heterogeneous clinical documents into validated structured JSON, enabling downstream automation for real-world evidence, prior authorization operations, care coordination, quality analytics, and claims review.

## Design Principles

1. **Schema-first extraction:** every document type maps to a strict Pydantic contract.
2. **Human-auditable routing:** document classification is explicit and inspectable.
3. **Graceful degradation:** failures are logged without terminating batch runs.
4. **Credential-free portfolio review:** deterministic demo mode proves the architecture without external services.
5. **Production extensibility:** Claude Files API path can replace deterministic parsing with schema-guided LLM extraction.

## Pipeline Stages

1. PDF ingestion
2. PDF text extraction or Files API upload
3. document-type classification
4. schema selection
5. structured field extraction
6. schema validation
7. ground-truth metric computation
8. JSONL/report persistence

## Evaluation Plan

For each document type, create synthetic but realistic HIPAA-safe PDFs and corresponding manual gold-standard JSON files. Compare extraction against gold standard using field-level exact match metrics:

- accuracy
- precision
- recall
- F1
- schema pass rate
- confidence distribution

## Failure Modes

| Failure mode | Mitigation |
|---|---|
| Misclassified document type | explicit classifier output and UNKNOWN fallback |
| Missing required fields | Pydantic validation errors captured in error log |
| Hallucinated fields | `extra="forbid"` schema setting |
| Invalid formats | field validators and typed date/money fields |
| Batch interruption | per-document exception handling |

## Production Upgrade Path

- Replace deterministic keyword classifier with Claude or a trained classifier.
- Store outputs in PostgreSQL or BigQuery.
- Add human review UI for low-confidence extractions.
- Add document-level and field-level confidence calibration.
- Add PHI redaction and audit logging.
- Add OCR preprocessing for scanned documents.
