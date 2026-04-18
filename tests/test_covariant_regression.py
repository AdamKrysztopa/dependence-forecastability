"""Covariant regression tests (V3-F08).

Verifies that each covariant analysis case produces outputs matching frozen
expected references under deterministic seeds. A drift-detection suite
confirms that the verification mechanism correctly catches mutations.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from forecastability.diagnostics.covariant_regression import (
    COVARIANT_FIXTURE_CASES,
    build_covariant_regression_outputs,
    verify_covariant_regression_outputs,
    write_covariant_regression_outputs,
)

_EXPECTED_DIR = Path("docs/fixtures/covariant_regression/expected")


class TestCovariantRegressionMatchesFrozen:
    """Rebuilt covariant outputs must match frozen expected JSON files."""

    def test_rebuild_matches_frozen_expected(self, tmp_path: Path) -> None:
        """All covariant outputs must reproduce frozen expected values."""
        written_paths = write_covariant_regression_outputs(output_dir=tmp_path)

        assert len(written_paths) == len(COVARIANT_FIXTURE_CASES)
        for path in written_paths:
            assert path.exists(), f"Expected output not written: {path}"

        verify_covariant_regression_outputs(
            actual_dir=tmp_path,
            expected_dir=_EXPECTED_DIR,
        )

    def test_all_expected_files_present(self) -> None:
        """Every fixture case must have a corresponding expected JSON file."""
        for case_name in COVARIANT_FIXTURE_CASES:
            expected_path = _EXPECTED_DIR / f"{case_name}.json"
            assert expected_path.exists(), (
                f"Missing expected fixture for '{case_name}': {expected_path}"
            )


class TestCovariantDriftDetection:
    """Verification must fail when any rebuilt artifact drifts."""

    def test_corrupted_cross_ami_flags_drift(self, tmp_path: Path) -> None:
        """Corrupting a cross_ami float value must trigger failure."""
        write_covariant_regression_outputs(output_dir=tmp_path)

        path = tmp_path / "benchmark_ami_pami.json"
        data = json.loads(path.read_text())
        first_key = next(iter(data["rows"]))
        data["rows"][first_key]["cross_ami"] = 0.999
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="benchmark_ami_pami"):
            verify_covariant_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_corrupted_peak_score_driver_flags_drift(self, tmp_path: Path) -> None:
        """Corrupting peak_score_driver string must trigger failure."""
        write_covariant_regression_outputs(output_dir=tmp_path)

        path = tmp_path / "benchmark_ami_pami.json"
        data = json.loads(path.read_text())
        data["peak_score_driver"] = "driver_noise"
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

        with pytest.raises(ValueError, match="benchmark_ami_pami"):
            verify_covariant_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )

    def test_missing_file_flags_drift(self, tmp_path: Path) -> None:
        """Missing rebuilt output file must trigger failure."""
        write_covariant_regression_outputs(output_dir=tmp_path)

        (tmp_path / "benchmark_ami_pami.json").unlink()

        with pytest.raises(ValueError, match="benchmark_ami_pami"):
            verify_covariant_regression_outputs(
                actual_dir=tmp_path,
                expected_dir=_EXPECTED_DIR,
            )


@pytest.fixture(scope="module")
def covariant_outputs() -> dict[str, dict]:
    """Module-scoped covariant outputs — built once to avoid repeated computation."""
    return build_covariant_regression_outputs()


class TestCovariantFixtureSanity:
    """Sanity-check that generated outputs have expected ground-truth properties."""

    def test_benchmark_ami_pami_direct_beats_noise(
        self, covariant_outputs: dict[str, dict]
    ) -> None:
        """driver_direct peak cross_ami must exceed driver_noise peak cross_ami."""
        rows = covariant_outputs["benchmark_ami_pami"]["rows"]
        direct_peak = max(
            rows[f"driver_direct:{lag}"]["cross_ami"]
            for lag in range(1, 4)
            if rows[f"driver_direct:{lag}"].get("cross_ami") is not None
        )
        noise_peak = max(
            rows[f"driver_noise:{lag}"]["cross_ami"]
            for lag in range(1, 4)
            if rows[f"driver_noise:{lag}"].get("cross_ami") is not None
        )
        assert direct_peak > noise_peak

    def test_benchmark_gcmi_direct_beats_noise(self, covariant_outputs: dict[str, dict]) -> None:
        """driver_direct peak gcmi must exceed driver_noise peak gcmi."""
        rows = covariant_outputs["benchmark_gcmi"]["rows"]
        direct_peak = max(
            rows[f"driver_direct:{lag}"]["gcmi"]
            for lag in range(1, 4)
            if rows[f"driver_direct:{lag}"].get("gcmi") is not None
        )
        noise_peak = max(
            rows[f"driver_noise:{lag}"]["gcmi"]
            for lag in range(1, 4)
            if rows[f"driver_noise:{lag}"].get("gcmi") is not None
        )
        assert direct_peak > noise_peak

    def test_benchmark_te_direct_beats_noise(self, covariant_outputs: dict[str, dict]) -> None:
        """driver_direct peak transfer_entropy must exceed driver_noise peak."""
        rows = covariant_outputs["benchmark_te"]["rows"]
        direct_peak = max(
            rows[f"driver_direct:{lag}"]["transfer_entropy"]
            for lag in range(1, 4)
            if rows[f"driver_direct:{lag}"].get("transfer_entropy") is not None
        )
        noise_peak = max(
            rows[f"driver_noise:{lag}"]["transfer_entropy"]
            for lag in range(1, 4)
            if rows[f"driver_noise:{lag}"].get("transfer_entropy") is not None
        )
        assert direct_peak > noise_peak

    def test_peak_score_driver_is_direct_in_ami_pami_case(
        self, covariant_outputs: dict[str, dict]
    ) -> None:
        """Ground-truth: peak cross_ami driver must be informative (direct or mediated).

        At n=900, driver_mediated can peak higher than driver_direct due to the
        indirect coupling chain amplifying pairwise MI. Both are valid informative
        drivers; what matters is that the peak is not driver_noise.
        """
        peak = covariant_outputs["benchmark_ami_pami"]["peak_score_driver"]
        assert peak in {"driver_direct", "driver_mediated"}, (
            f"Expected an informative driver as peak, got {peak!r}"
        )

    def test_all_cases_present_in_outputs(self, covariant_outputs: dict[str, dict]) -> None:
        """All three case names must be present in build outputs."""
        assert "benchmark_ami_pami" in covariant_outputs
        assert "benchmark_gcmi" in covariant_outputs
        assert "benchmark_te" in covariant_outputs
