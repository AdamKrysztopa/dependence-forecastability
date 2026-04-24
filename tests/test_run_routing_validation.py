"""Focused tests for run_routing_validation real-panel file handling."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from forecastability.use_cases.run_routing_validation import run_routing_validation
from forecastability.utils.synthetic import ExpectedFamilyMetadata


def _empty_synthetic_panel() -> list[ExpectedFamilyMetadata]:
    return []


def _write_series_csv(path: Path, *, column: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    values = np.sin(2.0 * np.pi * np.arange(240) / 12.0)
    pd.DataFrame({column: values}).to_csv(path, index=False)


def _write_manifest(repo_root: Path, *, cases_yaml: str) -> Path:
    manifest_path = repo_root / "configs" / "routing_validation_real_panel.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        f"panel_version: 0.3.3\ncases:\n{cases_yaml}",
        encoding="utf-8",
    )
    return manifest_path


def test_run_routing_validation_skips_missing_download_case(tmp_path: Path) -> None:
    csv_path = tmp_path / "data" / "raw" / "bundled_case.csv"
    _write_series_csv(csv_path, column="value")
    manifest_path = _write_manifest(
        tmp_path,
        cases_yaml=(
            "  - name: bundled_case\n"
            "    source: bundled\n"
            "    path: data/raw/bundled_case.csv\n"
            "    column: value\n"
            "    expected_primary_families: [seasonal_naive]\n"
            "    expected_caution_flags: []\n"
            "    license: test\n"
            "  - name: missing_download_case\n"
            "    source: download\n"
            "    path: data/processed/missing_download.csv\n"
            "    column: value\n"
            "    expected_primary_families: [arima]\n"
            "    expected_caution_flags: []\n"
            "    license: test\n"
            "    download_command: uv run python scripts/download_data.py missing_download_case\n"
        ),
    )

    bundle = run_routing_validation(
        synthetic_panel=_empty_synthetic_panel(),
        real_panel_path=manifest_path,
        n_per_archetype=200,
        random_state=42,
    )

    assert bundle.audit.total_cases == 1
    assert [case.case_name for case in bundle.cases] == ["bundled_case"]


def test_run_routing_validation_skips_too_short_real_case(tmp_path: Path) -> None:
    valid_path = tmp_path / "data" / "raw" / "bundled_case.csv"
    short_path = tmp_path / "data" / "raw" / "too_short_case.csv"
    _write_series_csv(valid_path, column="value")
    pd.DataFrame({"value": np.sin(2.0 * np.pi * np.arange(60) / 12.0)}).to_csv(
        short_path,
        index=False,
    )
    manifest_path = _write_manifest(
        tmp_path,
        cases_yaml=(
            "  - name: bundled_case\n"
            "    source: bundled\n"
            "    path: data/raw/bundled_case.csv\n"
            "    column: value\n"
            "    expected_primary_families: [seasonal_naive]\n"
            "    expected_caution_flags: []\n"
            "    license: test\n"
            "  - name: too_short_case\n"
            "    source: bundled\n"
            "    path: data/raw/too_short_case.csv\n"
            "    column: value\n"
            "    expected_primary_families: [seasonal_naive]\n"
            "    expected_caution_flags: []\n"
            "    license: test\n"
        ),
    )

    bundle = run_routing_validation(
        synthetic_panel=_empty_synthetic_panel(),
        real_panel_path=manifest_path,
        n_per_archetype=200,
        random_state=42,
    )

    assert bundle.audit.total_cases == 1
    assert [case.case_name for case in bundle.cases] == ["bundled_case"]


def test_run_routing_validation_raises_for_missing_bundled_case(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path,
        cases_yaml=(
            "  - name: missing_bundled_case\n"
            "    source: bundled\n"
            "    path: data/raw/missing_bundled.csv\n"
            "    column: value\n"
            "    expected_primary_families: [arima]\n"
            "    expected_caution_flags: []\n"
            "    license: test\n"
        ),
    )

    with pytest.raises(FileNotFoundError, match="missing_bundled_case"):
        run_routing_validation(
            synthetic_panel=_empty_synthetic_panel(),
            real_panel_path=manifest_path,
            n_per_archetype=200,
            random_state=42,
        )
