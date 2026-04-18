"""Tests for the linear Gaussian-information baseline service (V3_1-F01)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from forecastability.services.linear_information_service import (
    _gaussian_information_from_rho,
    compute_linear_information_curve,
)
from forecastability.utils.synthetic import (
    generate_ar1_monotonic,
    generate_nonlinear_mixed,
    generate_seasonal_periodic,
    generate_white_noise,
)


def test_white_noise_gives_near_zero_gaussian_information() -> None:
    """White noise has no autocorrelation so I_G should be near zero at all horizons."""
    series = generate_white_noise(n=500, seed=42)
    curve = compute_linear_information_curve(series, horizons=list(range(1, 11)))
    valid_values = [gi for _, gi in curve.valid_gaussian_values()]
    assert len(valid_values) > 0, "Expected some valid horizons"
    for gi in valid_values:
        assert gi < 0.05, f"Expected near-zero I_G for white noise, got {gi}"


def test_ar1_gives_positive_gaussian_information() -> None:
    """Strong AR(1) has high autocorrelation so I_G at h=1 should exceed 0.1."""
    series = generate_ar1_monotonic(n=500, phi=0.85, seed=42)
    curve = compute_linear_information_curve(series, horizons=list(range(1, 11)))
    valid_map = dict(curve.valid_gaussian_values())
    assert 1 in valid_map, "Horizon 1 should be valid for AR(1)"
    assert valid_map[1] > 0.1, f"Expected I_G > 0.1 at h=1 for AR(1) φ=0.85, got {valid_map[1]}"
    for gi in valid_map.values():
        assert gi >= 0.0, f"Gaussian information must be non-negative, got {gi}"


def test_ar1_monotonic_decay() -> None:
    """AR(1) φ=0.85: I_G should decay with horizon — h=1 > h=5 > h=10."""
    series = generate_ar1_monotonic(n=500, phi=0.85, seed=42)
    curve = compute_linear_information_curve(series, horizons=[1, 5, 10])
    valid_map = dict(curve.valid_gaussian_values())
    assert {1, 5, 10} <= valid_map.keys(), "All three horizons should be valid"
    assert valid_map[1] > valid_map[5], (
        f"I_G should decay: h=1 ({valid_map[1]:.4f}) > h=5 ({valid_map[5]:.4f})"
    )
    assert valid_map[5] > valid_map[10], (
        f"I_G should decay: h=5 ({valid_map[5]:.4f}) > h=10 ({valid_map[10]:.4f})"
    )


def test_clipping_near_rho_one() -> None:
    """A near-perfect linear series should give finite, non-inf I_G at h=1."""
    series = np.arange(200, dtype=float)
    curve = compute_linear_information_curve(series, horizons=[1])
    assert len(curve.points) == 1
    point = curve.points[0]
    assert point.valid, "Should be valid for a linear trend"
    assert point.gaussian_information is not None
    assert math.isfinite(point.gaussian_information), (
        f"Expected finite I_G for near-rho=1 series, got {point.gaussian_information}"
    )


def test_insufficient_data_returns_invalid() -> None:
    """Too few data pairs (series length 5, horizon 3) should return valid=False."""
    series = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    curve = compute_linear_information_curve(series, horizons=[3])
    assert len(curve.points) == 1
    point = curve.points[0]
    assert not point.valid, "Expected valid=False when < 3 pairs remain"


def test_zero_variance_returns_invalid() -> None:
    """A constant series has zero std; autocorrelation is undefined."""
    series = np.ones(100)
    curve = compute_linear_information_curve(series, horizons=[1])
    assert len(curve.points) == 1
    point = curve.points[0]
    assert not point.valid
    assert point.caution == "undefined_autocorrelation"


def test_horizon_beyond_series_returns_invalid() -> None:
    """Horizon >= series length should return valid=False."""
    series = np.arange(10, dtype=float)
    for horizon in [10, 11]:
        curve = compute_linear_information_curve(series, horizons=[horizon])
        point = curve.points[0]
        assert not point.valid, f"Expected valid=False for horizon={horizon} with len=10"


def test_curve_point_count_matches_horizons() -> None:
    """Output curve must have exactly as many points as input horizons."""
    series = generate_ar1_monotonic(n=200, phi=0.7, seed=0)
    horizons = [1, 2, 3, 5, 8]
    curve = compute_linear_information_curve(series, horizons=horizons)
    assert len(curve.points) == len(horizons)


def test_valid_gaussian_values_helper() -> None:
    """valid_gaussian_values should return only (int, float) tuples with gi >= 0."""
    series = generate_ar1_monotonic(n=300, phi=0.7, seed=1)
    curve = compute_linear_information_curve(series, horizons=list(range(1, 8)))
    pairs = curve.valid_gaussian_values()
    assert len(pairs) > 0
    for h, gi in pairs:
        assert isinstance(h, int)
        assert isinstance(gi, float)
        assert gi >= 0.0, f"I_G must be non-negative, got {gi} at h={h}"


def test_gaussian_information_formula_correctness() -> None:
    """Verify the formula directly: for rho=0.5, I_G = -0.5 * log(0.75)."""
    expected = -0.5 * math.log(1.0 - 0.5**2)
    result = _gaussian_information_from_rho(0.5, epsilon=1e-12)
    assert result == pytest.approx(expected, rel=1e-9)


def test_seasonal_series_has_periodic_gaussian_peaks() -> None:
    """I_G at h=12 should exceed h=6 for a seasonal period-12 series."""
    series = generate_seasonal_periodic(n=500, period=12, seed=42)
    curve = compute_linear_information_curve(series, horizons=list(range(1, 25)))
    valid_map = dict(curve.valid_gaussian_values())
    assert 6 in valid_map and 12 in valid_map, "Horizons 6 and 12 must be valid"
    assert valid_map[12] > valid_map[6], (
        f"Expected seasonal peak at h=12: I_G(12)={valid_map[12]:.4f} vs I_G(6)={valid_map[6]:.4f}"
    )


def test_nonlinear_mixed_has_low_gaussian_at_some_horizons() -> None:
    """Nonlinear mixed series: linear baseline provides finite I_G values at valid horizons."""
    series = generate_nonlinear_mixed(n=500, seed=42)
    curve = compute_linear_information_curve(series, horizons=list(range(1, 11)))
    valid_pairs = curve.valid_gaussian_values()
    assert len(valid_pairs) > 0, "Expected some valid horizons for nonlinear_mixed"
    for _, gi in valid_pairs:
        assert math.isfinite(gi), f"Expected finite I_G, got {gi}"
