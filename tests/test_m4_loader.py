"""Tests for M4 subset loader with deterministic cache behavior."""

from __future__ import annotations

from pathlib import Path

from forecastability.utils.datasets import load_m4_subset, m4_seasonal_period


def test_m4_seasonal_period_mapping() -> None:
    assert m4_seasonal_period("Monthly") == 12
    assert m4_seasonal_period("Quarterly") == 4


def test_load_m4_subset_mock_is_deterministic(tmp_path: Path) -> None:
    panel_a = load_m4_subset(
        frequency="Monthly",
        n_series=5,
        cache_dir=tmp_path / "m4",
        random_state=42,
        allow_mock=True,
    )
    panel_b = load_m4_subset(
        frequency="Monthly",
        n_series=5,
        cache_dir=tmp_path / "m4",
        random_state=42,
        allow_mock=True,
    )
    ids_a = [row[0] for row in panel_a]
    ids_b = [row[0] for row in panel_b]
    assert ids_a == ids_b
