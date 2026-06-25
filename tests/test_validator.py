"""Tests for field-level validation metrics."""

from validator import ExtractionValidator


def test_compare_to_ground_truth_exact_match() -> None:
    """Exact match should yield perfect field metrics."""

    validator = ExtractionValidator()
    expected = {"patient": {"name": "Jane"}, "tests": [{"value": 1.0}]}
    metrics = validator.compare_to_ground_truth(expected, expected)
    assert metrics["field_accuracy"] == 1.0
    assert metrics["f1"] == 1.0
