"""Tests for fixture-based benchmark reproducibility artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from forecastability.utils.reproducibility import (
    verify_fixture_benchmark_artifacts,
    write_fixture_benchmark_artifacts,
)

_FIXTURE_ROOT = Path("docs/fixtures/benchmark_examples")
_EXPECTED_ROOT = _FIXTURE_ROOT / "expected"


def test_fixture_artifact_rebuild_matches_frozen_expected(tmp_path: Path) -> None:
    """Rebuilt fixture artifacts should match frozen expected outputs exactly."""
    written_paths = write_fixture_benchmark_artifacts(
        fixture_horizon_path=_FIXTURE_ROOT / "raw_horizon_table.csv",
        output_dir=tmp_path,
    )

    assert len(written_paths) == 5
    for path in written_paths:
        assert path.exists()

    verify_fixture_benchmark_artifacts(actual_dir=tmp_path, expected_dir=_EXPECTED_ROOT)

    summary_table = pd.read_csv(tmp_path / "benchmark_summary_table.csv")
    assert {
        "model_name",
        "mean_spearman_ami_smape",
        "mean_spearman_pami_smape",
        "mean_delta_pami_minus_ami",
        "preferred_diagnostic",
    }.issubset(summary_table.columns)
    assert set(summary_table["preferred_diagnostic"]) == {"pami"}


def test_fixture_verification_flags_drift(tmp_path: Path) -> None:
    """Verification should fail when any rebuilt artifact drifts."""
    write_fixture_benchmark_artifacts(
        fixture_horizon_path=_FIXTURE_ROOT / "raw_horizon_table.csv",
        output_dir=tmp_path,
    )

    rank_path = tmp_path / "rank_associations.csv"
    rank_df = pd.read_csv(rank_path)
    rank_df.loc[0, "spearman_ami_smape"] = -0.5
    rank_df.to_csv(rank_path, index=False)

    with pytest.raises(ValueError, match="rank_associations.csv"):
        verify_fixture_benchmark_artifacts(actual_dir=tmp_path, expected_dir=_EXPECTED_ROOT)
