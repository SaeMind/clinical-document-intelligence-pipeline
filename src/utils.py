"""Shared utilities for PDF text extraction and JSON handling."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader


def utc_timestamp() -> str:
    """Return a filesystem-safe UTC timestamp.

    Returns:
        Timestamp string formatted as YYYYmmddTHHMMSSZ.
    """

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from a PDF file using pypdf.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Concatenated text from all readable pages.
    """

    reader = PdfReader(str(pdf_path))
    page_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(page_text).strip()


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object from disk.

    Args:
        path: JSON file path.

    Returns:
        Parsed JSON dictionary.
    """

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON dictionary to disk.

    Args:
        path: Destination JSON path.
        payload: Serializable dictionary.

    Returns:
        None.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, default=str)
        file.write("\n")
