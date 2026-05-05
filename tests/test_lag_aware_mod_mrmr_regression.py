"""Lag-aware ModMRMR regression tests for frozen Phase 2 fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from forecastability.diagnostics.lag_aware_mod_mrmr_regression import (
    LAG_AWARE_MOD_MRMR_FIXTURE_CASES,
    verify_lag_aware_mod_mrmr_regression_outputs,
    write_lag_aware_mod_mrmr_regression_outputs,
)

_EXPECTED_DIR = Path("docs/fixtures/lag_aware_mod_mrmr/expected")


class TestLagAwareModMRMRRegressionMatchesFrozen:
    """Rebuilt lag-aware ModMRMR outputs must match frozen expected JSON files."""

    def test_rebuild_matches_frozen_expected(self, tmp_path: Path) -> None:
        """All lag-aware outputs must reproduce the frozen expected values."""
        written_paths = write_lag_aware_mod_mrmr_regression_outputs(output_dir=tmp_path)

        assert len(written_paths) == len(LAG_AWARE_MOD_MRMR_FIXTURE_CASES)
        for path in written_paths:
            assert path.exists(), f"Expected output not written: {path}"

        verify_lag_aware_mod_mrmr_regression_outputs(
            actual_dir=tmp_path,
            expected_dir=_EXPECTED_DIR,
        )

    def test_all_expected_files_present(self) -> None:
        """Every fixture case must have a corresponding expected JSON file."""
        for case_name in LAG_AWARE_MOD_MRMR_FIXTURE_CASES:
            expected_path = _EXPECTED_DIR / f"{case_name}.json"
            assert expected_path.exists(), (
                f"Missing expected fixture for '{case_name}': {expected_path}"
            )


class TestLagAwareModMRMRRegressionDriftDetection:
    """Verification must fail when any rebuilt lag-aware artifact drifts."""

    def test_rebuild_clears_stale_json_from_reused_output_dir(self, tmp_path: Path) -> None:
        """Rebuild should remove stale JSONs from reused output directories."""
        stale_path = tmp_path / "stale_case.json"
        stale_path.write_text("{}\n")

        write_lag_aware_mod_mrmr_regression_outputs(output_dir=tmp_path)

        assert not stale_path.exists()

    def test_corrupted_known_future_contract_flags_drift(self, tmp_path: Path) -> None:
        """Mutating preserved future lag detail should trigger verification failure."""
        write_lag_aware_mod_mrmr_regression_outputs(output_dir=tmp_path)

        path = tmp_path / "known_future_bypass.json"
        payload = json.loads(path.read_text())
        payload["lag_table"][0]["lag"] = 99
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="known_future_bypass"):
            verify_lag_aware_mod_mrmr_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_corrupted_aggregate_penalty_winner_flags_drift(self, tmp_path: Path) -> None:
        """Mutating the aggregate-vs-maximum winner should trigger failure."""
        write_lag_aware_mod_mrmr_regression_outputs(output_dir=tmp_path)

        path = tmp_path / "aggregate_redundancy_vs_maximum.json"
        payload = json.loads(path.read_text())
        payload["winner_by_penalty"]["maximum_redundancy"] = "duplicate_candidate"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="aggregate_redundancy_vs_maximum"):
            verify_lag_aware_mod_mrmr_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_unexpected_output_file_flags_drift(self, tmp_path: Path) -> None:
        """Unexpected JSON files in the rebuilt directory must fail verification."""
        write_lag_aware_mod_mrmr_regression_outputs(output_dir=tmp_path)

        extra_path = tmp_path / "unexpected_case.json"
        extra_path.write_text("{}\n")

        with pytest.raises(ValueError, match="Unexpected rebuilt output: unexpected_case.json"):
            verify_lag_aware_mod_mrmr_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )
