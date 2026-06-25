"""Command-line orchestrator for the document intelligence pipeline."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

from config import get_settings
from extractor import DocumentExtractor
from schemas import SCHEMA_BY_DOCUMENT_TYPE
from storage import OutputStore
from utils import read_json, utc_timestamp
from validator import ExtractionValidator

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def collect_pdf_paths(pdf: str | None, batch: str | None) -> list[Path]:
    """Resolve CLI inputs into a list of PDF paths.

    Args:
        pdf: Optional single PDF path.
        batch: Optional batch directory path.

    Returns:
        List of PDF paths to process.
    """

    if pdf:
        return [Path(pdf)]
    if batch:
        return sorted(Path(batch).glob("*.pdf"))
    raise ValueError("Provide either --pdf or --batch")


def build_validation_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize schema validation outcomes by document type.

    Args:
        records: Extraction records.

    Returns:
        Aggregated validation report.
    """

    summary: dict[str, Any] = {"total_documents": len(records), "by_document_type": {}}
    for record in records:
        doc_type = record["document_type"]
        bucket = summary["by_document_type"].setdefault(
            doc_type, {"count": 0, "valid": 0, "average_confidence": 0.0}
        )
        bucket["count"] += 1
        bucket["valid"] += int(record.get("valid", False))
        bucket["average_confidence"] += float(record.get("confidence", 0.0))
    for bucket in summary["by_document_type"].values():
        bucket["average_confidence"] = round(bucket["average_confidence"] / bucket["count"], 4)
        bucket["schema_pass_rate"] = round(bucket["valid"] / bucket["count"], 4)
    return summary


def evaluate_against_ground_truth(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate extractions against available gold-standard files.

    Args:
        records: Extraction records.

    Returns:
        Aggregate field-level accuracy metrics.
    """

    settings = get_settings()
    validator = ExtractionValidator()
    evaluations: list[dict[str, Any]] = []
    for record in records:
        truth_path = settings.ground_truth_dir / f"{Path(record['pdf_file']).stem}.json"
        if not truth_path.exists() or not record.get("extracted_data"):
            continue
        expected = read_json(truth_path)
        metrics = validator.compare_to_ground_truth(record["extracted_data"], expected)
        evaluations.append({"pdf_file": record["pdf_file"], **metrics})
    if not evaluations:
        return {"evaluated_documents": 0, "documents": []}
    avg = lambda key: round(sum(float(item[key]) for item in evaluations) / len(evaluations), 4)
    return {
        "evaluated_documents": len(evaluations),
        "macro_field_accuracy": avg("field_accuracy"),
        "macro_precision": avg("precision"),
        "macro_recall": avg("recall"),
        "macro_f1": avg("f1"),
        "documents": evaluations,
    }


def main() -> None:
    """Run document extraction from CLI arguments.

    Returns:
        None.
    """

    parser = argparse.ArgumentParser(description="Structured clinical PDF extraction")
    parser.add_argument("--pdf", type=str, help="Single PDF to extract")
    parser.add_argument("--batch", type=str, help="Directory of PDFs to process")
    args = parser.parse_args()

    settings = get_settings()
    run_dir = settings.outputs_dir / f"run_{utc_timestamp()}"
    store = OutputStore(run_dir)
    extractor = DocumentExtractor(settings)
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for pdf_path in collect_pdf_paths(args.pdf, args.batch):
        try:
            logger.info("Processing %s", pdf_path)
            records.append(extractor.extract(pdf_path))
        except Exception as error:
            logger.exception("Failed to process %s", pdf_path)
            errors.append({"pdf_file": pdf_path.name, "error": str(error)})

    validation_report = build_validation_report(records)
    validation_report["ground_truth_evaluation"] = evaluate_against_ground_truth(records)
    validation_report["schemas_supported"] = sorted(SCHEMA_BY_DOCUMENT_TYPE.keys())

    store.write_jsonl("extracted_data.jsonl", records)
    store.write_report("validation_report.json", validation_report)
    store.write_report("error_log.json", {"errors": errors})
    logger.info("Processed %s documents", len(records))
    logger.info("Outputs written to %s", run_dir)


if __name__ == "__main__":
    main()
