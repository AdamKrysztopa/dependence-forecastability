"""Tests for the phase-0 routing-validation real-series panel manifest."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from forecastability.diagnostics.routing_validation_panel import (
    load_default_routing_validation_real_panel,
    resolve_case_path,
)


def test_real_panel_manifest_loads_with_three_cases() -> None:
    """The manifest must load and contain the curated three-case panel."""
    manifest = load_default_routing_validation_real_panel(repo_root=Path.cwd())

    assert manifest.panel_version == "0.3.3"
    assert len(manifest.cases) == 3
    assert [case.name for case in manifest.cases] == [
        "air_passengers",
        "sunspots_monthly",
        "etth1_oht_subset",
    ]


def test_real_panel_license_notes_are_non_empty() -> None:
    """Every real-panel case must carry a non-empty license note."""
    manifest = load_default_routing_validation_real_panel(repo_root=Path.cwd())
    assert all(case.license.strip() for case in manifest.cases)


def test_bundled_real_panel_csvs_smoke_load() -> None:
    """Bundled cases should be present and readable with configured columns."""
    manifest = load_default_routing_validation_real_panel(repo_root=Path.cwd())
    bundled = [case for case in manifest.cases if case.source == "bundled"]

    assert len(bundled) == 2
    for case in bundled:
        path = resolve_case_path(case, repo_root=Path.cwd())
        assert path.exists(), f"missing bundled dataset: {path}"
        frame = pd.read_csv(path)
        assert case.column in frame.columns
        assert not frame.empty


def test_sunspots_download_command_is_documented_in_manifest() -> None:
    """The download-backed case must expose a deterministic command."""
    manifest = load_default_routing_validation_real_panel(repo_root=Path.cwd())
    sunspots = next(case for case in manifest.cases if case.name == "sunspots_monthly")

    assert sunspots.source == "download"
    assert sunspots.download_command == "uv run python scripts/download_data.py sunspots_monthly"
