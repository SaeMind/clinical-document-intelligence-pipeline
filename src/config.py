"""Runtime configuration for the document intelligence pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Centralized runtime settings.

    Attributes:
        project_root: Repository root directory.
        data_dir: Directory containing input data.
        sample_documents_dir: Directory containing demo PDF files.
        ground_truth_dir: Directory containing manual gold-standard JSON files.
        outputs_dir: Directory for timestamped pipeline outputs.
        anthropic_api_key: Optional Anthropic API key.
        anthropic_model: Anthropic model used for classification and extraction.
        demo_mode: Whether to run deterministic local extraction without Claude.
    """

    project_root: Path
    data_dir: Path
    sample_documents_dir: Path
    ground_truth_dir: Path
    outputs_dir: Path
    anthropic_api_key: str | None
    anthropic_model: str
    demo_mode: bool


def get_settings() -> Settings:
    """Build application settings from environment variables.

    Returns:
        Settings instance with all key project paths and model configuration.
    """

    project_root = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[1]))
    data_dir = project_root / "data"
    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        sample_documents_dir=data_dir / "sample_documents",
        ground_truth_dir=data_dir / "ground_truth",
        outputs_dir=project_root / "outputs",
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        demo_mode=os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes"},
    )
