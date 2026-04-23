"""Manifest loader for the real-series routing validation panel (plan v0.3.3 §6.2).

Parses ``configs/routing_validation_real_panel.yaml`` into a frozen Pydantic
manifest model so the orchestration use case can consume it without repeating
YAML parsing logic.

This module lives in ``use_cases/`` (not ``diagnostics/``) because it is an
application-layer concern: loading the manifest is part of the use-case
workflow, not a numerical building-block or regression helper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

RealPanelSource = Literal["bundled", "download"]


class RealPanelCaseEntry(BaseModel):
    """One entry in the real-series routing validation panel manifest."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Stable, machine-readable case identifier.")
    source: RealPanelSource = Field(description="How the data is obtained.")
    path: str = Field(description="Relative path from the repository root to the CSV.")
    column: str = Field(description="Column name to use as the series values.")
    expected_primary_families: list[str] = Field(
        description="Non-empty list of acceptable primary routing families.",
    )
    expected_caution_flags: list[str] = Field(default_factory=list)
    license: str = Field(description="License identifier for the dataset.")
    download_command: str | None = Field(
        default=None,
        description="Shell command to download the data (for 'download' sources).",
    )

    @field_validator("expected_primary_families")
    @classmethod
    def _families_non_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("expected_primary_families must be non-empty")
        return value

    @field_validator("license")
    @classmethod
    def _license_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("license must be non-empty")
        return value


class RealValidationPanelManifest(BaseModel):
    """Parsed routing_validation_real_panel.yaml manifest."""

    model_config = ConfigDict(frozen=True)

    panel_version: str = Field(description="Manifest schema version.")
    cases: list[RealPanelCaseEntry] = Field(
        description="One entry per real-series validation case.",
    )


def load_real_panel_manifest(path: Path) -> RealValidationPanelManifest:
    """Parse the real-series routing validation panel YAML manifest.

    Args:
        path: Absolute or relative path to the YAML manifest file.

    Returns:
        Frozen ``RealValidationPanelManifest`` instance.

    Raises:
        FileNotFoundError: If the manifest file does not exist.
        ValueError: If the YAML structure is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Real panel manifest not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return RealValidationPanelManifest.model_validate(raw)


def load_series_from_entry(
    entry: RealPanelCaseEntry,
    *,
    repo_root: Path,
) -> np.ndarray:
    """Load the time series from a real panel case entry.

    Args:
        entry: Parsed real panel case entry with path and column information.
        repo_root: Absolute path to the repository root (used to resolve
            relative CSV paths from the manifest).

    Returns:
        1-D float64 numpy array of the time series values.

    Raises:
        FileNotFoundError: If the CSV file does not exist at the resolved path.
        KeyError: If the named column is absent from the CSV.
    """
    import pandas as pd

    csv_path = repo_root / entry.path
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Real panel CSV not found: {csv_path} "
            f"(entry='{entry.name}', source='{entry.source}')"
        )
    df = pd.read_csv(csv_path)
    if entry.column not in df.columns:
        raise KeyError(
            f"Column '{entry.column}' not found in {csv_path}. "
            f"Available columns: {list(df.columns)}"
        )
    return df[entry.column].to_numpy(dtype=float)


__all__ = [
    "RealPanelCaseEntry",
    "RealPanelSource",
    "RealValidationPanelManifest",
    "load_real_panel_manifest",
    "load_series_from_entry",
]
