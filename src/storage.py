"""Output persistence layer for document extraction runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils import write_json


class OutputStore:
    """Persist extracted records, validation reports, and errors."""

    def __init__(self, output_dir: Path) -> None:
        """Initialize an output store.

        Args:
            output_dir: Directory where run artifacts will be written.
        """

        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_jsonl(self, filename: str, records: list[dict[str, Any]]) -> Path:
        """Write records to a JSONL file.

        Args:
            filename: Output filename.
            records: List of serializable dictionaries.

        Returns:
            Path to the written file.
        """

        path = self.output_dir / filename
        with path.open("w", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(record, default=str) + "\n")
        return path

    def write_report(self, filename: str, report: dict[str, Any]) -> Path:
        """Write a JSON report.

        Args:
            filename: Output filename.
            report: Report payload.

        Returns:
            Path to the written report.
        """

        path = self.output_dir / filename
        write_json(path, report)
        return path
