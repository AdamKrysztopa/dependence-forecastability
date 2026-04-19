"""Fingerprint regression tests for frozen geometry and routing fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from forecastability.diagnostics.fingerprint_regression import (
    FINGERPRINT_FIXTURE_SERIES,
    verify_fingerprint_regression_outputs,
    write_fingerprint_regression_outputs,
)

_EXPECTED_DIR = Path("docs/fixtures/fingerprint_regression/expected")


class TestFingerprintRegressionMatchesFrozen:
    """Rebuilt fingerprint outputs must match frozen expected JSON files."""

    def test_rebuild_matches_frozen_expected(self, tmp_path: Path) -> None:
        """All canonical fingerprint outputs should reproduce frozen values."""
        written_paths = write_fingerprint_regression_outputs(output_dir=tmp_path)

        assert len(written_paths) == len(FINGERPRINT_FIXTURE_SERIES)
        for path in written_paths:
            assert path.exists(), f"Expected output not written: {path}"

        verify_fingerprint_regression_outputs(
            actual_dir=tmp_path,
            expected_dir=_EXPECTED_DIR,
        )

    def test_all_expected_files_present(self) -> None:
        """Every fixture case should have a corresponding expected JSON file."""
        for target_name in FINGERPRINT_FIXTURE_SERIES:
            expected_path = _EXPECTED_DIR / f"{target_name}.json"
            assert expected_path.exists(), (
                f"Missing expected fixture for '{target_name}': {expected_path}"
            )


class TestFingerprintRegressionDriftDetection:
    """Verification should fail when rebuilt outputs drift from frozen expected."""

    def test_corrupted_signal_to_noise_flags_drift(self, tmp_path: Path) -> None:
        """Mutating a geometry float should trigger verification failure."""
        write_fingerprint_regression_outputs(output_dir=tmp_path)

        path = tmp_path / "white_noise.json"
        payload = json.loads(path.read_text())
        payload["geometry"]["signal_to_noise"] = 0.123
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="white_noise"):
            verify_fingerprint_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_corrupted_route_family_flags_drift(self, tmp_path: Path) -> None:
        """Mutating primary route families should trigger verification failure."""
        write_fingerprint_regression_outputs(output_dir=tmp_path)

        path = tmp_path / "seasonal_periodic.json"
        payload = json.loads(path.read_text())
        payload["recommendation"]["primary_families"] = ["arima"]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="seasonal_periodic"):
            verify_fingerprint_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_missing_file_flags_drift(self, tmp_path: Path) -> None:
        """Missing rebuilt output file should trigger verification failure."""
        write_fingerprint_regression_outputs(output_dir=tmp_path)

        (tmp_path / "ar1_monotonic.json").unlink()

        with pytest.raises(ValueError, match="ar1_monotonic"):
            verify_fingerprint_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )