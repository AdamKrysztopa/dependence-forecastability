"""Lagged-exogenous regression tests for frozen Phase 3 fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from forecastability.diagnostics.lagged_exog_regression import (
    LAGGED_EXOG_FIXTURE_CASES,
    verify_lagged_exog_regression_outputs,
    write_lagged_exog_regression_outputs,
)

_EXPECTED_DIR = Path("docs/fixtures/lagged_exog_regression/expected")


class TestLaggedExogRegressionMatchesFrozen:
    """Rebuilt lagged-exog outputs must match frozen expected JSON files."""

    def test_rebuild_matches_frozen_expected(self, tmp_path: Path) -> None:
        """All lagged-exog outputs must reproduce frozen expected values."""
        written_paths = write_lagged_exog_regression_outputs(output_dir=tmp_path)

        assert len(written_paths) == len(LAGGED_EXOG_FIXTURE_CASES)
        for path in written_paths:
            assert path.exists(), f"Expected output not written: {path}"

        verify_lagged_exog_regression_outputs(
            actual_dir=tmp_path,
            expected_dir=_EXPECTED_DIR,
        )

    def test_all_expected_files_present(self) -> None:
        """Every fixture case must have a corresponding expected JSON file."""
        for case_name in LAGGED_EXOG_FIXTURE_CASES:
            expected_path = _EXPECTED_DIR / f"{case_name}.json"
            assert expected_path.exists(), (
                f"Missing expected fixture for '{case_name}': {expected_path}"
            )


class TestLaggedExogRegressionDriftDetection:
    """Verification must fail when any rebuilt artifact drifts."""

    def test_corrupted_selected_lag_map_flags_drift(self, tmp_path: Path) -> None:
        """Mutating selected_lag_map should trigger verification failure."""
        write_lagged_exog_regression_outputs(output_dir=tmp_path)

        path = tmp_path / "selected_lag_map_panel.json"
        payload = json.loads(path.read_text())
        payload["selected_lag_map"]["direct_lag2"] = [1]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="selected_lag_map_panel"):
            verify_lagged_exog_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_corrupted_default_call_path_curve_flags_drift(self, tmp_path: Path) -> None:
        """Mutating default raw curve should trigger verification failure."""
        write_lagged_exog_regression_outputs(output_dir=tmp_path)

        path = tmp_path / "default_curve_call_path.json"
        payload = json.loads(path.read_text())
        payload["raw_default_curve"][0] = 999.0
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="default_curve_call_path"):
            verify_lagged_exog_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_corrupted_cross_pami_contract_flags_drift(self, tmp_path: Path) -> None:
        """Mutating target_only conditioning tags should trigger failure."""
        write_lagged_exog_regression_outputs(output_dir=tmp_path)

        path = tmp_path / "cross_pami_target_only_contract.json"
        payload = json.loads(path.read_text())
        payload["conditioning_tags"] = ["none", "none", "none"]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="cross_pami_target_only_contract"):
            verify_lagged_exog_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )
