"""Tests for raw/partial lag-domain plumbing services."""

from __future__ import annotations

import numpy as np

from forecastability.services.partial_curve_service import compute_partial_curve
from forecastability.services.raw_curve_service import compute_raw_curve


def _length_scorer(
    past: np.ndarray,
    future: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Return aligned sample length to validate lag-domain indexing."""
    del future, random_state
    return float(past.size)


def test_compute_raw_curve_default_matches_explicit_predictive_range() -> None:
    """Default raw-curve behavior should match explicit ``(1, max_lag)``."""
    series = np.linspace(0.0, 1.0, 20)
    max_lag = 5

    baseline = compute_raw_curve(
        series,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=42,
    )
    explicit = compute_raw_curve(
        series,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=42,
        lag_range=(1, max_lag),
    )

    np.testing.assert_allclose(baseline, explicit)
    np.testing.assert_allclose(baseline, np.array([19.0, 18.0, 17.0, 16.0, 15.0]))


def test_compute_raw_curve_supports_zero_lag_opt_in() -> None:
    """Zero-lag opt-in should prepend the contemporaneous row."""
    series = np.linspace(0.0, 1.0, 20)
    max_lag = 4

    with_zero = compute_raw_curve(
        series,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=7,
        lag_range=(0, max_lag),
    )

    assert with_zero.shape == (max_lag + 1,)
    np.testing.assert_allclose(with_zero, np.array([20.0, 19.0, 18.0, 17.0, 16.0]))


def test_compute_raw_curve_allows_max_lag_zero_default_path() -> None:
    """Default predictive path should stay compatible when ``max_lag=0``."""
    series = np.linspace(0.0, 1.0, 20)

    curve = compute_raw_curve(
        series,
        0,
        _length_scorer,
        min_pairs=1,
        random_state=19,
    )

    assert curve.shape == (0,)


def test_compute_raw_curve_accepts_zero_lag_only_range() -> None:
    """Explicit ``lag_range=(0, 0)`` should yield one contemporaneous score."""
    series = np.linspace(0.0, 1.0, 20)

    curve = compute_raw_curve(
        series,
        0,
        _length_scorer,
        min_pairs=1,
        random_state=23,
        lag_range=(0, 0),
    )

    assert curve.shape == (1,)
    np.testing.assert_allclose(curve, np.array([20.0]))


def test_compute_partial_curve_default_matches_explicit_predictive_range() -> None:
    """Default partial-curve behavior should match explicit ``(1, max_lag)``."""
    series = np.linspace(0.0, 1.0, 30)
    max_lag = 6

    baseline = compute_partial_curve(
        series,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=11,
    )
    explicit = compute_partial_curve(
        series,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=11,
        lag_range=(1, max_lag),
    )

    np.testing.assert_allclose(baseline, explicit)


def test_compute_partial_curve_supports_zero_lag_opt_in() -> None:
    """Partial curve should support additive zero-lag opt-in for diagnostics."""
    series = np.linspace(0.0, 1.0, 20)
    max_lag = 3

    with_zero = compute_partial_curve(
        series,
        max_lag,
        _length_scorer,
        min_pairs=1,
        random_state=13,
        lag_range=(0, max_lag),
    )

    assert with_zero.shape == (max_lag + 1,)
    np.testing.assert_allclose(with_zero, np.array([20.0, 19.0, 18.0, 17.0]))


def test_compute_partial_curve_allows_max_lag_zero_default_path() -> None:
    """Default predictive partial path should stay compatible when ``max_lag=0``."""
    series = np.linspace(0.0, 1.0, 20)

    curve = compute_partial_curve(
        series,
        0,
        _length_scorer,
        min_pairs=1,
        random_state=29,
    )

    assert curve.shape == (0,)


def test_compute_partial_curve_accepts_zero_lag_only_range() -> None:
    """Explicit ``lag_range=(0, 0)`` should yield one partial contemporaneous score."""
    series = np.linspace(0.0, 1.0, 20)

    curve = compute_partial_curve(
        series,
        0,
        _length_scorer,
        min_pairs=1,
        random_state=31,
        lag_range=(0, 0),
    )

    assert curve.shape == (1,)
    np.testing.assert_allclose(curve, np.array([20.0]))
