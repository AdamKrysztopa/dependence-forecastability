"""Tests for exogenous raw/partial curve service wrappers."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from forecastability.metrics import _scale_series
from forecastability.metrics.scorers import DependenceScorer, default_registry
from forecastability.services.exog_partial_curve_service import compute_exog_partial_curve
from forecastability.services.exog_raw_curve_service import (
    compute_exog_raw_curve,
    compute_exog_raw_curve_with_zero_lag,
)
from forecastability.utils.synthetic import generate_covariant_benchmark

_COVARIANT_AMI_PAMI_EXPECTED = Path(
    "docs/fixtures/covariant_regression/expected/benchmark_ami_pami.json"
)


def _length_scorer(
    past: np.ndarray,
    future: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Return aligned sample length to validate lag indexing."""
    del future, random_state
    return float(past.size)


def _load_expected_cross_ami_curve(*, driver_name: str, max_lag: int) -> list[float]:
    """Load frozen expected cross_ami values for one driver and lag range."""
    payload_obj = json.loads(_COVARIANT_AMI_PAMI_EXPECTED.read_text())
    assert isinstance(payload_obj, dict), "Fixture payload must be a JSON object"
    rows_obj = payload_obj.get("rows")
    assert isinstance(rows_obj, dict), "Fixture payload must include a 'rows' object"

    curve: list[float] = []
    for lag in range(1, max_lag + 1):
        row_obj = rows_obj.get(f"{driver_name}:{lag}")
        assert isinstance(row_obj, dict), f"Missing fixture row for {driver_name}:{lag}"
        value = row_obj.get("cross_ami")
        assert isinstance(value, (int, float)), f"Invalid cross_ami fixture value at lag {lag}"
        curve.append(float(value))
    return curve


def test_compute_exog_raw_curve_default_matches_explicit_predictive_range() -> None:
    """Default exog raw wrapper should match explicit ``(1, max_lag)``."""
    target = np.linspace(0.0, 1.0, 20)
    exog = np.linspace(1.0, 2.0, 20)
    max_lag = 5

    baseline = compute_exog_raw_curve(
        target,
        exog,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=42,
    )
    explicit = compute_exog_raw_curve(
        target,
        exog,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=42,
        lag_range=(1, max_lag),
    )

    np.testing.assert_allclose(baseline, explicit)


def test_compute_exog_raw_curve_with_zero_lag_shape_and_indexing() -> None:
    """Zero-lag helper should emit ``0..max_lag`` and match legacy rows on ``1..``."""
    target = np.linspace(0.0, 1.0, 20)
    exog = np.linspace(1.0, 2.0, 20)
    max_lag = 4

    curve_with_zero = compute_exog_raw_curve_with_zero_lag(
        target,
        exog,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=7,
    )
    legacy = compute_exog_raw_curve(
        target,
        exog,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=7,
    )

    assert curve_with_zero.shape == (max_lag + 1,)
    assert curve_with_zero[0] == 20.0
    np.testing.assert_allclose(curve_with_zero[1:], legacy)


def test_compute_exog_raw_curve_with_zero_lag_accepts_max_lag_zero() -> None:
    """Zero-lag helper should support the ``max_lag=0`` one-point domain."""
    target = np.linspace(0.0, 1.0, 20)
    exog = np.linspace(1.0, 2.0, 20)

    curve = compute_exog_raw_curve_with_zero_lag(
        target,
        exog,
        0,
        _length_scorer,
        min_pairs=1,
        random_state=17,
    )

    assert curve.shape == (1,)
    np.testing.assert_allclose(curve, np.array([20.0]))


def test_exog_wrappers_allow_max_lag_zero_default_predictive_path() -> None:
    """Default predictive wrappers should remain compatible for ``max_lag=0``."""
    target = np.linspace(0.0, 1.0, 20)
    exog = np.linspace(1.0, 2.0, 20)

    raw_curve = compute_exog_raw_curve(
        target,
        exog,
        0,
        _length_scorer,
        min_pairs=1,
        random_state=5,
    )
    partial_curve = compute_exog_partial_curve(
        target,
        exog,
        0,
        _length_scorer,
        min_pairs=1,
        random_state=5,
    )

    assert raw_curve.shape == (0,)
    assert partial_curve.shape == (0,)


def test_exog_wrappers_accept_zero_lag_only_range() -> None:
    """Explicit ``lag_range=(0, 0)`` should yield one score for both wrappers."""
    target = np.linspace(0.0, 1.0, 20)
    exog = np.linspace(1.0, 2.0, 20)

    raw_curve = compute_exog_raw_curve(
        target,
        exog,
        0,
        _length_scorer,
        min_pairs=1,
        random_state=6,
        lag_range=(0, 0),
    )
    partial_curve = compute_exog_partial_curve(
        target,
        exog,
        0,
        _length_scorer,
        min_pairs=1,
        random_state=6,
        lag_range=(0, 0),
    )

    assert raw_curve.shape == (1,)
    assert partial_curve.shape == (1,)
    np.testing.assert_allclose(raw_curve, np.array([20.0]))
    np.testing.assert_allclose(partial_curve, np.array([20.0]))


def test_exog_wrappers_reject_invalid_lag_ranges() -> None:
    """Raw/partial wrappers should reject malformed lag ranges consistently."""
    target = np.linspace(0.0, 1.0, 20)
    exog = np.linspace(1.0, 2.0, 20)
    invalid_ranges = [(-1, 1), (2, 1), (0, 3)]

    for lag_range in invalid_ranges:
        for compute_fn in (compute_exog_raw_curve, compute_exog_partial_curve):
            try:
                _ = compute_fn(
                    target,
                    exog,
                    2,
                    _length_scorer,
                    min_pairs=1,
                    random_state=8,
                    lag_range=lag_range,
                )
            except ValueError as exc:
                assert "lag_range" in str(exc)
            else:
                raise AssertionError(f"Expected ValueError for lag_range={lag_range}")


def test_compute_exog_raw_curve_matches_frozen_predictive_fixture() -> None:
    """Default predictive-only exog raw path should match frozen regression values."""
    assert _COVARIANT_AMI_PAMI_EXPECTED.exists(), (
        f"Missing expected covariant fixture: {_COVARIANT_AMI_PAMI_EXPECTED}"
    )

    benchmark_df = generate_covariant_benchmark(n=900, seed=42)
    scorer = default_registry().get("mi").scorer
    assert isinstance(scorer, DependenceScorer)
    max_lag = 3

    curve = compute_exog_raw_curve(
        benchmark_df["target"].to_numpy(),
        benchmark_df["driver_direct"].to_numpy(),
        max_lag,
        scorer,
        min_pairs=30,
        random_state=42,
    )
    expected_curve = _load_expected_cross_ami_curve(driver_name="driver_direct", max_lag=max_lag)

    assert curve.shape == (max_lag,)
    for lag, (actual, expected) in enumerate(zip(curve, expected_curve, strict=True), start=1):
        assert math.isclose(float(actual), expected, rel_tol=1e-9, abs_tol=1e-6), (
            f"cross_ami drift at lag {lag}: actual={actual}, expected={expected}"
        )


def test_compute_exog_partial_curve_default_matches_explicit_predictive_range() -> None:
    """Default exog partial wrapper should match explicit ``(1, max_lag)``."""
    target = np.linspace(0.0, 1.0, 30)
    exog = np.linspace(1.0, 2.0, 30)
    max_lag = 6

    baseline = compute_exog_partial_curve(
        target,
        exog,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=9,
    )
    explicit = compute_exog_partial_curve(
        target,
        exog,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=9,
        lag_range=(1, max_lag),
    )

    np.testing.assert_allclose(baseline, explicit)


def test_compute_exog_partial_curve_supports_zero_lag_pass_through() -> None:
    """Exogenous partial wrapper should support additive ``lag=0`` requests."""
    target = np.linspace(0.0, 1.0, 20)
    exog = np.linspace(1.0, 2.0, 20)
    max_lag = 3

    with_zero = compute_exog_partial_curve(
        target,
        exog,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=15,
        lag_range=(0, max_lag),
    )

    assert with_zero.shape == (max_lag + 1,)
    np.testing.assert_allclose(with_zero, np.array([20.0, 19.0, 18.0, 17.0]))


def test_compute_exog_partial_curve_keeps_predictor_target_only_conditioning() -> None:
    """Exogenous partial path must not residualize the predictor on target history."""
    n = 80
    t = np.linspace(0.0, 6.0 * np.pi, n)
    target = np.sin(t) + 0.1 * np.cos(2.0 * t)
    exog = np.cos(t) + 0.2 * np.sin(3.0 * t)

    seen_past: dict[int, np.ndarray] = {}

    def _recording_scorer(
        past: np.ndarray,
        future: np.ndarray,
        *,
        random_state: int = 42,
    ) -> float:
        lag = random_state - 100
        seen_past[lag] = past.copy()
        return float(np.mean(past * future))

    max_lag = 4
    _ = compute_exog_partial_curve(
        target,
        exog,
        max_lag,
        _recording_scorer,
        min_pairs=1,
        random_state=100,
    )

    scaled_exog = _scale_series(exog)
    assert sorted(seen_past) == [1, 2, 3, 4]
    for lag in range(1, max_lag + 1):
        np.testing.assert_allclose(seen_past[lag], scaled_exog[:-lag])
