"""Document type classifier for heterogeneous clinical PDFs."""

from __future__ import annotations

from enum import Enum


class DocumentType(str, Enum):
    """Supported healthcare document classes."""

    PRIOR_AUTH = "prior_authorization"
    LAB_RESULTS = "lab_results"
    REFERRAL = "referral_letter"
    DISCHARGE = "discharge_summary"
    EOB = "explanation_of_benefits"
    UNKNOWN = "unknown"


class DocumentClassifier:
    """Classify clinical documents using high-signal keyword routing.

    This deterministic classifier is intentionally included for demo mode so the
    repository can run without external credentials. In production, the same
    routing interface can be backed by Claude or a fine-tuned classifier.
    """

    keyword_map: dict[DocumentType, tuple[str, ...]] = {
        DocumentType.PRIOR_AUTH: (
            "prior authorization",
            "authorization number",
            "auth status",
            "procedure code",
        ),
        DocumentType.LAB_RESULTS: (
            "lab results",
            "reference range",
            "specimen",
            "ordering physician",
        ),
        DocumentType.REFERRAL: (
            "referral letter",
            "specialty requested",
            "clinical indication",
            "urgency",
        ),
        DocumentType.DISCHARGE: (
            "discharge summary",
            "hospital course",
            "discharge medications",
            "follow-up instructions",
        ),
        DocumentType.EOB: (
            "explanation of benefits",
            "claim id",
            "amount paid",
            "patient responsibility",
        ),
    }

    def classify(self, document_text: str) -> DocumentType:
        """Infer the document type from extracted PDF text.

        Args:
            document_text: Text extracted from a PDF document.

        Returns:
            Matching DocumentType, or UNKNOWN if no signal is found.
        """

        text = document_text.lower()
        scores: dict[DocumentType, int] = {}
        for doc_type, keywords in self.keyword_map.items():
            scores[doc_type] = sum(1 for keyword in keywords if keyword in text)
        best_type = max(scores, key=scores.get)
        return best_type if scores[best_type] > 0 else DocumentType.UNKNOWN
