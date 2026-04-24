"""Tests for routing validation regression fixture generation and verification.

Covers:
- ``rebuild_fixtures`` produces all three fixture files with correct structure
- ``verify_fixtures`` returns 0 when rebuilt outputs match the frozen expected files
- Discrete fields compare exactly; float fields compare with math.isclose
- ``calibrate_near_threshold_amplitude`` finds an amplitude in the target band
- Phase-3 fixture files are present and parseable after the freeze (smoke test)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from forecastability.diagnostics.routing_validation_regression import (
    _ATOL,
    _AUDIT_SUMMARY_FILE,
    _CALIBRATION_FILE,
    _CONFIDENCE_LABELS_FILE,
    _EXPECTED_SUBDIR,
    _RTOL,
    _SYNTHETIC_PANEL_FILE,
    calibrate_near_threshold_amplitude,
    load_pinned_weak_seasonal_amplitude,
    rebuild_fixtures,
    verify_fixtures,
)
from forecastability.use_cases.run_routing_validation import run_routing_validation
from forecastability.utils.types import RoutingPolicyAuditConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXPECTED_DIR = _REPO_ROOT / _EXPECTED_SUBDIR


def _load_expected(filename: str) -> Any:
    path = _EXPECTED_DIR / filename
    if not path.exists():
        pytest.skip(
            f"Frozen fixture not found: {path} — run rebuild_routing_validation_fixtures.py first"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _prepare_rebuild_root(repo_root: Path) -> Path:
    dest_dir = repo_root / _EXPECTED_SUBDIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    cal_src = _EXPECTED_DIR / _CALIBRATION_FILE
    if cal_src.exists():
        (dest_dir / _CALIBRATION_FILE).write_bytes(cal_src.read_bytes())

    return dest_dir


@pytest.fixture(scope="module")
def rebuilt_fixture_root(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    repo_root = tmp_path_factory.mktemp("routing_validation_regression")
    dest_dir = _prepare_rebuild_root(repo_root)
    rc = rebuild_fixtures(repo_root)
    assert rc == 0
    return repo_root, dest_dir


@pytest.fixture(scope="module")
def calibration_result() -> dict[str, Any]:
    return calibrate_near_threshold_amplitude()


# ---------------------------------------------------------------------------
# Smoke tests: frozen fixtures are present and parseable
# ---------------------------------------------------------------------------


class TestFrozenFixturesExist:
    def test_synthetic_panel_exists_and_parseable(self) -> None:
        data = _load_expected(_SYNTHETIC_PANEL_FILE)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_audit_summary_exists_and_parseable(self) -> None:
        data = _load_expected(_AUDIT_SUMMARY_FILE)
        assert isinstance(data, dict)
        assert "total_cases" in data

    def test_confidence_labels_exists_and_parseable(self) -> None:
        data = _load_expected(_CONFIDENCE_LABELS_FILE)
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_calibrated_amplitude_loads_from_fixture(self) -> None:
        calibration = _load_expected(_CALIBRATION_FILE)
        amplitude = load_pinned_weak_seasonal_amplitude(_REPO_ROOT)

        assert amplitude == calibration["calibrated_amplitude"]


# ---------------------------------------------------------------------------
# Fixture structure: discrete fields and float fields
# ---------------------------------------------------------------------------


class TestSyntheticPanelStructure:
    def test_all_cases_have_required_fields(self) -> None:
        data = _load_expected(_SYNTHETIC_PANEL_FILE)
        assert isinstance(data, list)
        required = {
            "case_name",
            "source_kind",
            "outcome",
            "confidence_label",
            "expected_primary_families",
            "observed_primary_families",
            "threshold_margin",
            "rule_stability",
            "fingerprint_penalty_count",
        }
        for row in data:
            assert isinstance(row, dict)
            missing = required - row.keys()
            assert not missing, f"Row {row.get('case_name')!r} missing fields: {missing}"

    def test_outcomes_are_valid(self) -> None:
        data = _load_expected(_SYNTHETIC_PANEL_FILE)
        valid_outcomes = {"pass", "fail", "downgrade", "abstain"}
        assert isinstance(data, list)
        for row in data:
            assert isinstance(row, dict)
            assert row["outcome"] in valid_outcomes, (
                f"Case {row['case_name']!r}: unexpected outcome {row['outcome']!r}"
            )

    def test_source_kind_is_synthetic(self) -> None:
        data = _load_expected(_SYNTHETIC_PANEL_FILE)
        assert isinstance(data, list)
        for row in data:
            assert isinstance(row, dict)
            assert row["source_kind"] == "synthetic"

    def test_threshold_margin_is_finite_float(self) -> None:
        data = _load_expected(_SYNTHETIC_PANEL_FILE)
        assert isinstance(data, list)
        for row in data:
            assert isinstance(row, dict)
            margin = row["threshold_margin"]
            assert isinstance(margin, (int, float))
            assert math.isfinite(float(margin))

    def test_ten_cases_present(self) -> None:
        """Routing validation should cover exactly the ten canonical archetypes."""
        data = _load_expected(_SYNTHETIC_PANEL_FILE)
        assert isinstance(data, list)
        assert len(data) == 10


class TestAuditSummaryStructure:
    def test_required_count_keys_present(self) -> None:
        data = _load_expected(_AUDIT_SUMMARY_FILE)
        assert isinstance(data, dict)
        required = {
            "total_cases",
            "passed_cases",
            "failed_cases",
            "downgraded_cases",
            "abstained_cases",
        }
        assert required <= data.keys()

    def test_counts_are_non_negative_integers(self) -> None:
        data = _load_expected(_AUDIT_SUMMARY_FILE)
        assert isinstance(data, dict)
        outcome_keys = (
            "total_cases",
            "passed_cases",
            "failed_cases",
            "downgraded_cases",
            "abstained_cases",
        )
        for key in outcome_keys:
            assert isinstance(data[key], int)
            assert data[key] >= 0

    def test_total_equals_sum_of_outcomes(self) -> None:
        data = _load_expected(_AUDIT_SUMMARY_FILE)
        assert isinstance(data, dict)
        total = data["total_cases"]
        parts = (
            data["passed_cases"]
            + data["failed_cases"]
            + data["downgraded_cases"]
            + data["abstained_cases"]
        )
        assert total == parts


class TestCoverageRequirements:
    """§6.3 acceptance criteria — at least one case of each outcome type."""

    def test_at_least_one_pass(self) -> None:
        data = _load_expected(_AUDIT_SUMMARY_FILE)
        assert isinstance(data, dict)
        assert data["passed_cases"] >= 1, "No pass cases found (§6.3 requires at least one)"

    def test_at_least_one_downgrade(self) -> None:
        data = _load_expected(_AUDIT_SUMMARY_FILE)
        assert isinstance(data, dict)
        assert data["downgraded_cases"] >= 1, "No downgrade cases (§6.3 requires weak_seasonal)"

    def test_at_least_one_abstain(self) -> None:
        data = _load_expected(_AUDIT_SUMMARY_FILE)
        assert isinstance(data, dict)
        assert data["abstained_cases"] >= 1, "No abstain cases (§6.3 requires white_noise)"

    def test_at_least_one_low_confidence_label(self) -> None:
        data = _load_expected(_CONFIDENCE_LABELS_FILE)
        assert isinstance(data, dict)
        labels = list(data.values())
        assert "low" in labels, "No low-confidence case (§6.3 requires low_directness_high_penalty)"


class TestPinnedCalibrationPath:
    def test_run_routing_validation_matches_pinned_weak_seasonal_fixture(self) -> None:
        amplitude = load_pinned_weak_seasonal_amplitude(_REPO_ROOT)
        if amplitude is None:
            pytest.skip("Pinned calibration fixture is not present")

        bundle = run_routing_validation(
            real_panel_path=None,
            n_per_archetype=600,
            random_state=42,
            weak_seasonal_amplitude=amplitude,
        )
        expected_panel = _load_expected(_SYNTHETIC_PANEL_FILE)
        expected_case = next(
            row for row in expected_panel if row["case_name"] == "weak_seasonal_near_threshold"
        )
        actual_case = next(
            case for case in bundle.cases if case.case_name == "weak_seasonal_near_threshold"
        )

        assert actual_case.outcome == expected_case["outcome"]
        assert actual_case.confidence_label == expected_case["confidence_label"]
        assert (
            sorted(actual_case.observed_primary_families)
            == expected_case["observed_primary_families"]
        )
        assert math.isclose(
            actual_case.threshold_margin,
            expected_case["threshold_margin"],
            rel_tol=_RTOL,
            abs_tol=_ATOL,
        )


# ---------------------------------------------------------------------------
# Rebuild round-trip: write to tmp, compare
# ---------------------------------------------------------------------------


class TestRebuildRoundTrip:
    def test_rebuild_exits_zero(self, rebuilt_fixture_root: tuple[Path, Path]) -> None:
        """rebuild_fixtures(tmp_path) should succeed."""
        _, dest_dir = rebuilt_fixture_root
        assert dest_dir.exists()

    def test_rebuild_writes_three_files(self, rebuilt_fixture_root: tuple[Path, Path]) -> None:
        _, expected_dir = rebuilt_fixture_root
        assert (expected_dir / _SYNTHETIC_PANEL_FILE).exists()
        assert (expected_dir / _AUDIT_SUMMARY_FILE).exists()
        assert (expected_dir / _CONFIDENCE_LABELS_FILE).exists()

    def test_rebuild_output_matches_frozen(self, rebuilt_fixture_root: tuple[Path, Path]) -> None:
        """Rebuilding in a temp dir should reproduce the frozen fixture exactly."""
        if not (_EXPECTED_DIR / _SYNTHETIC_PANEL_FILE).exists():
            pytest.skip("Frozen fixtures not present — run rebuild script first")

        _, dest_dir = rebuilt_fixture_root

        for fname in (_SYNTHETIC_PANEL_FILE, _AUDIT_SUMMARY_FILE, _CONFIDENCE_LABELS_FILE):
            actual = json.loads((dest_dir / fname).read_text(encoding="utf-8"))
            expected = json.loads((_EXPECTED_DIR / fname).read_text(encoding="utf-8"))
            _assert_deep_equal(actual, expected, path=fname)


def _assert_deep_equal(actual: Any, expected: Any, *, path: str) -> None:
    """Recursive comparison: floats use isclose; all other types exact."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        assert set(actual.keys()) == set(expected.keys()), f"{path}: key mismatch"
        for key in expected:
            _assert_deep_equal(actual[key], expected[key], path=f"{path}/{key}")
    elif isinstance(expected, list) and isinstance(actual, list):
        assert len(actual) == len(expected), f"{path}: length mismatch"
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            _assert_deep_equal(a, e, path=f"{path}[{i}]")
    elif isinstance(expected, float) and isinstance(actual, (float, int)):
        assert math.isclose(float(actual), expected, rel_tol=_RTOL, abs_tol=_ATOL), (
            f"{path}: float mismatch actual={actual}, expected={expected}"
        )
    else:
        assert actual == expected, f"{path}: mismatch actual={actual!r}, expected={expected!r}"


# ---------------------------------------------------------------------------
# verify_fixtures
# ---------------------------------------------------------------------------


class TestVerifyFixtures:
    def test_verify_returns_zero_after_rebuild(
        self,
        rebuilt_fixture_root: tuple[Path, Path],
    ) -> None:
        """verify_fixtures must return 0 when expected dir contains a fresh rebuild."""
        repo_root, _ = rebuilt_fixture_root
        rc = verify_fixtures(repo_root)
        assert rc == 0

    def test_verify_returns_two_when_file_missing(self, tmp_path: Path) -> None:
        (tmp_path / _EXPECTED_SUBDIR).mkdir(parents=True, exist_ok=True)
        rc = verify_fixtures(tmp_path)
        assert rc == 2

    def test_verify_returns_two_on_tampered_outcome(self, tmp_path: Path) -> None:
        """Mutating a discrete outcome field should cause verify to report failure."""
        dest_dir = _prepare_rebuild_root(tmp_path)
        rebuild_fixtures(tmp_path)

        # Tamper with one outcome in the panel fixture.
        panel_path = dest_dir / _SYNTHETIC_PANEL_FILE
        panel = json.loads(panel_path.read_text(encoding="utf-8"))
        assert isinstance(panel, list) and len(panel) > 0
        original_outcome = panel[0]["outcome"]
        tampered_outcome = "fail" if original_outcome != "fail" else "pass"
        panel[0]["outcome"] = tampered_outcome
        panel_path.write_text(json.dumps(panel, indent=2) + "\n", encoding="utf-8")

        rc = verify_fixtures(tmp_path)
        assert rc == 2


# ---------------------------------------------------------------------------
# Calibration (slow — skip in fast CI)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestCalibrateNearThresholdAmplitude:
    def test_calibration_finds_amplitude_in_target_band(
        self,
        calibration_result: dict[str, Any],
    ) -> None:
        cfg = RoutingPolicyAuditConfig()
        target_low = 0.5 * cfg.tau_margin_medium
        target_high = 0.5 * cfg.tau_margin
        amp = calibration_result["calibrated_amplitude"]
        margin = calibration_result["threshold_margin_at_calibration"]
        assert 0.5 < amp < 3.0, f"Calibrated amplitude {amp} is outside plausible range"
        assert target_low <= margin <= target_high, (
            f"d_theta={margin:.6f} not in [{target_low:.4f}, {target_high:.4f}]"
        )

    def test_calibration_result_has_expected_keys(
        self,
        calibration_result: dict[str, Any],
    ) -> None:
        expected_keys = {
            "calibrated_amplitude",
            "threshold_margin_at_calibration",
            "target_range_low",
            "target_range_high",
            "tau_margin",
            "tau_margin_medium",
            "sweep_seed",
            "sweep_n",
        }
        assert expected_keys <= calibration_result.keys()
