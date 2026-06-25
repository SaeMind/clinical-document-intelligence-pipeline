"""Validation and accuracy scoring for extracted clinical documents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError


@dataclass(frozen=True)
class ValidationResult:
    """Schema validation result."""

    valid: bool
    confidence: float
    errors: list[str]
    normalized_data: dict[str, Any] | None


class ExtractionValidator:
    """Validate extracted payloads and compare them with gold standards."""

    def validate(self, data: dict[str, Any], schema: type[BaseModel]) -> ValidationResult:
        """Validate extracted data against a Pydantic schema.

        Args:
            data: Extracted data dictionary.
            schema: Pydantic model class for the document type.

        Returns:
            ValidationResult with normalized data and error messages.
        """

        try:
            parsed = schema.model_validate(data)
            return ValidationResult(
                valid=True,
                confidence=0.95,
                errors=[],
                normalized_data=parsed.model_dump(mode="json"),
            )
        except ValidationError as error:
            return ValidationResult(
                valid=False,
                confidence=0.55,
                errors=[str(error)],
                normalized_data=None,
            )

    def compare_to_ground_truth(
        self,
        extracted: dict[str, Any],
        expected: dict[str, Any],
    ) -> dict[str, float | int]:
        """Compute exact-match field-level validation metrics.

        Args:
            extracted: Model-extracted normalized dictionary.
            expected: Manual gold-standard dictionary.

        Returns:
            Dictionary with field accuracy, precision, recall, and F1.
        """

        expected_flat = self._flatten(expected)
        extracted_flat = self._flatten(extracted)
        true_positive = sum(
            1 for key, value in expected_flat.items() if extracted_flat.get(key) == value
        )
        false_positive = sum(1 for key in extracted_flat if key not in expected_flat)
        false_negative = sum(
            1 for key, value in expected_flat.items() if extracted_flat.get(key) != value
        )
        total = len(expected_flat) or 1
        precision = true_positive / max(true_positive + false_positive, 1)
        recall = true_positive / max(true_positive + false_negative, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)
        return {
            "field_accuracy": round(true_positive / total, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "true_positive_fields": true_positive,
            "false_positive_fields": false_positive,
            "false_negative_fields": false_negative,
            "total_gold_fields": total,
        }

    def _flatten(self, payload: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        """Flatten nested dictionaries and lists into comparable field paths.

        Args:
            payload: Dictionary to flatten.
            prefix: Recursive field prefix.

        Returns:
            Flattened dictionary keyed by dot/bracket paths.
        """

        flattened: dict[str, Any] = {}
        for key, value in payload.items():
            field = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flattened.update(self._flatten(value, field))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    list_field = f"{field}[{index}]"
                    if isinstance(item, dict):
                        flattened.update(self._flatten(item, list_field))
                    else:
                        flattened[list_field] = item
            elif value is not None:
                flattened[field] = value
        return flattened
