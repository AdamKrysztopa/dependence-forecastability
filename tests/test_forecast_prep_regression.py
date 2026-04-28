"""Forecast prep contract regression tests for frozen fixture snapshots (FPC-F11)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from forecastability.diagnostics.forecast_prep_regression import (
    FORECAST_PREP_FIXTURE_CASES,
    verify_forecast_prep_regression_outputs,
    write_forecast_prep_regression_outputs,
)

_EXPECTED_DIR = Path("docs/fixtures/forecast_prep_regression/expected")


class TestForecastPrepRegressionFixturesPresent:
    """All expected fixture files must exist for each scenario case."""

    def test_all_expected_files_exist(self) -> None:
        """Every fixture case should have a corresponding expected JSON file."""
        for case_name in FORECAST_PREP_FIXTURE_CASES:
            expected_path = _EXPECTED_DIR / f"{case_name}.json"
            assert expected_path.exists(), (
                f"Missing expected fixture for '{case_name}': {expected_path}"
            )

    def test_expected_files_are_valid_json(self) -> None:
        """Every expected fixture file must parse as valid JSON."""
        for case_name in FORECAST_PREP_FIXTURE_CASES:
            expected_path = _EXPECTED_DIR / f"{case_name}.json"
            if not expected_path.exists():
                pytest.skip(f"Expected fixture missing: {case_name}")
            payload = json.loads(expected_path.read_text())
            assert isinstance(payload, dict), f"Expected JSON root to be a dict for {case_name}"


class TestForecastPrepRegressionContractInvariants:
    """Frozen fixtures must satisfy domain invariants independently of drift detection."""

    def test_univariate_contract_has_version_034(self) -> None:
        """Frozen univariate contract must carry the 0.3.4 schema version."""
        expected_path = _EXPECTED_DIR / "contract_univariate.json"
        if not expected_path.exists():
            pytest.skip("Fixture missing")
        payload = json.loads(expected_path.read_text())
        assert payload["contract"]["contract_version"] == "0.3.4"

    def test_blocked_contract_has_empty_recommended_families(self) -> None:
        """Frozen blocked fixture must have recommended_families == []."""
        expected_path = _EXPECTED_DIR / "contract_blocked.json"
        if not expected_path.exists():
            pytest.skip("Fixture missing")
        payload = json.loads(expected_path.read_text())
        assert payload["contract"]["blocked"] is True
        assert payload["contract"]["recommended_families"] == []
        assert payload["contract"]["recommended_target_lags"] == []

    def test_blocked_contract_has_caution_flag(self) -> None:
        """Frozen blocked fixture must carry a 'blocked' caution entry."""
        expected_path = _EXPECTED_DIR / "contract_blocked.json"
        if not expected_path.exists():
            pytest.skip("Fixture missing")
        payload = json.loads(expected_path.read_text())
        flags = payload["contract"]["caution_flags"]
        assert any("blocked" in flag for flag in flags), (
            f"Expected a blocked caution flag, got: {flags}"
        )

    def test_calendar_contract_has_calendar_features(self) -> None:
        """Frozen calendar fixture must include _calendar__* entries."""
        expected_path = _EXPECTED_DIR / "contract_with_calendar.json"
        if not expected_path.exists():
            pytest.skip("Fixture missing")
        payload = json.loads(expected_path.read_text())
        calendar_features = payload["contract"]["calendar_features"]
        assert len(calendar_features) >= 5, (
            f"Expected at least 5 calendar features, got: {calendar_features}"
        )
        for feature in calendar_features:
            assert feature.startswith("_calendar__"), (
                f"Calendar feature {feature!r} does not start with '_calendar__'"
            )

    def test_univariate_target_lags_are_positive(self) -> None:
        """All frozen target lags in the univariate fixture must be >= 1."""
        expected_path = _EXPECTED_DIR / "contract_univariate.json"
        if not expected_path.exists():
            pytest.skip("Fixture missing")
        payload = json.loads(expected_path.read_text())
        for lag in payload["contract"]["recommended_target_lags"]:
            assert lag >= 1, f"Target lag {lag} is not strictly positive"

    def test_lag_table_rows_are_ordered_by_axis_driver_lag(self) -> None:
        """Lag table rows in the frozen univariate fixture must be deterministically ordered."""
        expected_path = _EXPECTED_DIR / "contract_univariate.json"
        if not expected_path.exists():
            pytest.skip("Fixture missing")
        payload = json.loads(expected_path.read_text())
        rows = payload["lag_table"]
        sort_keys = [(r["axis"], r["driver"], r["lag"]) for r in rows]
        assert sort_keys == sorted(sort_keys), (
            "Lag table rows are not ordered by (axis, driver, lag)"
        )


class TestForecastPrepRegressionDriftDetection:
    """Verification should fail when rebuilt outputs drift from frozen expected."""

    def test_corrupted_confidence_label_flags_drift(self, tmp_path: Path) -> None:
        """Mutating confidence_label should trigger verification failure."""
        write_forecast_prep_regression_outputs(output_dir=tmp_path)

        path = tmp_path / "contract_univariate.json"
        payload = json.loads(path.read_text())
        payload["contract"]["confidence_label"] = "low"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="contract_univariate"):
            verify_forecast_prep_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_corrupted_recommended_target_lags_flags_drift(self, tmp_path: Path) -> None:
        """Mutating recommended_target_lags should trigger verification failure."""
        write_forecast_prep_regression_outputs(output_dir=tmp_path)

        path = tmp_path / "contract_univariate.json"
        payload = json.loads(path.read_text())
        payload["contract"]["recommended_target_lags"] = [99]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="contract_univariate"):
            verify_forecast_prep_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_missing_output_file_flags_drift(self, tmp_path: Path) -> None:
        """Missing rebuilt output file should trigger verification failure."""
        write_forecast_prep_regression_outputs(output_dir=tmp_path)

        (tmp_path / "contract_univariate.json").unlink()

        with pytest.raises(ValueError, match="contract_univariate"):
            verify_forecast_prep_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_verify_passes_with_intact_outputs(self, tmp_path: Path) -> None:
        """Verification must pass when rebuilt outputs are identical to frozen expected."""
        write_forecast_prep_regression_outputs(output_dir=tmp_path)

        # Raises ValueError on any drift; should not raise here.
        verify_forecast_prep_regression_outputs(
            actual_dir=tmp_path,
            expected_dir=_EXPECTED_DIR,
        )
