"""Tests for deterministic document classification."""

from document_classifier import DocumentClassifier, DocumentType


def test_classifier_detects_lab_result() -> None:
    """Classifier should identify lab result documents from domain terms."""

    classifier = DocumentClassifier()
    text = "Lab Results\nReference Range\nOrdering Physician: Dr. Lee"
    assert classifier.classify(text) == DocumentType.LAB_RESULTS
