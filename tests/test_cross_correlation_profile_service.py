"""Tests for the signed cross-correlation profile service."""

from __future__ import annotations

import numpy as np

from forecastability.metrics.scorers import DependenceScorer, default_registry
from forecastability.services.cross_correlation_profile_service import (
    compute_cross_correlation_profile,
)
from forecastability.services.exog_raw_curve_service import compute_exog_raw_curve_with_zero_lag
from forecastability.utils.synthetic import generate_lagged_exog_panel


def test_cross_correlation_profile_preserves_sign() -> None:
    """Lag-0 anti-correlation should remain negative (no abs collapse)."""
    n = 400
    signal = np.linspace(-2.0, 2.0, n)
    target = -signal + 0.05 * np.sin(np.linspace(0.0, 4.0 * np.pi, n))
    driver = signal

    profile = compute_cross_correlation_profile(target, driver, max_lag=4)

    assert profile.shape == (5,)
    assert profile[0] < -0.95


def test_cross_correlation_nonlinear_driver_is_small_but_cross_ami_detects_lag1() -> None:
    """Linear Pearson can miss nonlinear lag-1 signal captured by cross-AMI."""
    panel = generate_lagged_exog_panel(n=1500, seed=42)
    target = panel["target"].to_numpy()
    driver = panel["nonlinear_lag1"].to_numpy()

    corr_profile = compute_cross_correlation_profile(target, driver, max_lag=6)
    assert float(np.max(np.abs(corr_profile))) < 0.10

    registry = default_registry()
    mi_scorer = registry.get("mi").scorer
    assert isinstance(mi_scorer, DependenceScorer)

    ami_profile = compute_exog_raw_curve_with_zero_lag(
        target,
        driver,
        6,
        mi_scorer,
        min_pairs=30,
        random_state=42,
    )
    assert ami_profile.shape == (7,)
    assert ami_profile[1] > 0.03
