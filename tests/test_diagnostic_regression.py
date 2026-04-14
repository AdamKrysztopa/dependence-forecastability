"""Diagnostic regression tests for F1–F6 diagnostics (F9).

Verifies that each diagnostic service produces outputs matching frozen
expected references under deterministic seeds.  A drift-detection test
confirms that the verification mechanism correctly catches mutations.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from forecastability.diagnostics.diagnostic_regression import (
    FIXTURE_SERIES,
    verify_diagnostic_regression_outputs,
    write_diagnostic_regression_outputs,
)

_EXPECTED_DIR = Path("docs/fixtures/diagnostic_regression/expected")


class TestDiagnosticRegressionMatchesFrozen:
    """Rebuilt diagnostic outputs must match frozen expected JSON files."""

    def test_rebuild_matches_frozen_expected(self, tmp_path: Path) -> None:
        """All diagnostic outputs must reproduce frozen expected values."""
        written_paths = write_diagnostic_regression_outputs(output_dir=tmp_path)

        assert len(written_paths) == len(FIXTURE_SERIES)
        for path in written_paths:
            assert path.exists(), f"Expected output not written: {path}"

        verify_diagnostic_regression_outputs(
            actual_dir=tmp_path,
            expected_dir=_EXPECTED_DIR,
        )

    def test_all_expected_files_present(self) -> None:
        """Every fixture series must have a corresponding expected JSON file."""
        for series_name in FIXTURE_SERIES:
            expected_path = _EXPECTED_DIR / f"{series_name}.json"
            assert expected_path.exists(), (
                f"Missing expected fixture for '{series_name}': {expected_path}"
            )


class TestDriftDetection:
    """Verification must fail when any rebuilt artifact drifts."""

    def test_corrupted_f4_omega_flags_drift(self, tmp_path: Path) -> None:
        """Corrupting a spectral predictability value must trigger failure."""
        write_diagnostic_regression_outputs(output_dir=tmp_path)

        # Corrupt the white_noise F4 omega
        wn_path = tmp_path / "white_noise.json"
        data = json.loads(wn_path.read_text())
        data["F4"]["omega"] = 0.999
        wn_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="white_noise"):
            verify_diagnostic_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_corrupted_f1_horizons_flags_drift(self, tmp_path: Path) -> None:
        """Corrupting informative horizons must trigger failure."""
        write_diagnostic_regression_outputs(output_dir=tmp_path)

        ar1_path = tmp_path / "ar1_phi085.json"
        data = json.loads(ar1_path.read_text())
        data["F1"]["informative_horizons"] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        ar1_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="ar1_phi085"):
            verify_diagnostic_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_missing_file_flags_drift(self, tmp_path: Path) -> None:
        """Missing rebuilt output file must trigger failure."""
        write_diagnostic_regression_outputs(output_dir=tmp_path)

        (tmp_path / "white_noise.json").unlink()

        with pytest.raises(ValueError, match="white_noise"):
            verify_diagnostic_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )


class TestFixtureSeriesSanity:
    """Sanity-check that generated fixture series have expected properties."""

    def test_ar1_has_expected_length(self) -> None:
        series = FIXTURE_SERIES["ar1_phi085"]["generator"]()
        assert len(series) == 500

    def test_ar2_has_expected_length(self) -> None:
        series = FIXTURE_SERIES["ar2_finite_memory"]["generator"]()
        assert len(series) == 1000

    def test_logistic_map_has_expected_length(self) -> None:
        series = FIXTURE_SERIES["logistic_map_r39"]["generator"]()
        assert len(series) == 2000

    def test_sine_wave_range(self) -> None:
        series = FIXTURE_SERIES["sine_wave"]["generator"]()
        assert series.min() > -1.1
        assert series.max() < 1.1

    def test_logistic_map_in_unit_interval(self) -> None:
        series = FIXTURE_SERIES["logistic_map_r39"]["generator"]()
        assert series.min() >= 0.0
        assert series.max() <= 1.0
