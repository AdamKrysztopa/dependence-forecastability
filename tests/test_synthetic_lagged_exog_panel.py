"""Tests for the Phase 0 lagged-exogenous synthetic benchmark panel."""

from __future__ import annotations

import numpy as np
import pandas as pd

from forecastability import generate_lagged_exog_panel


def _abs_pearson_at_lag(
    driver: np.ndarray,
    target: np.ndarray,
    *,
    lag: int,
) -> float:
    """Compute absolute Pearson correlation for driver lag k against current target."""
    if lag < 0:
        raise ValueError("lag must be >= 0")
    if lag == 0:
        x = driver
        y = target
    else:
        x = driver[:-lag]
        y = target[lag:]
    return float(abs(np.corrcoef(x, y)[0, 1]))


def test_generate_lagged_exog_panel_is_deterministic_by_seed() -> None:
    """Panel generation should be deterministic for a fixed seed."""
    first = generate_lagged_exog_panel(n=1500, seed=42)
    second = generate_lagged_exog_panel(n=1500, seed=42)
    third = generate_lagged_exog_panel(n=1500, seed=43)

    pd.testing.assert_frame_equal(first, second)
    assert not first.equals(third)


def test_nonlinear_lag1_pearson_is_small_across_tested_lags() -> None:
    """Nonlinear driver should retain near-zero Pearson at tested lags."""
    panel = generate_lagged_exog_panel(n=1500, seed=42)
    driver = panel["nonlinear_lag1"].to_numpy()
    target = panel["target"].to_numpy()

    for lag in range(0, 7):
        rho_abs = _abs_pearson_at_lag(driver, target, lag=lag)
        assert rho_abs < 0.10, f"expected |rho| < 0.10 at lag {lag}, got {rho_abs:.4f}"


def test_instant_only_lag0_dominates_lagged_correlations() -> None:
    """The instant-only driver should be strongest at lag 0."""
    panel = generate_lagged_exog_panel(n=1500, seed=42)
    driver = panel["instant_only"].to_numpy()
    target = panel["target"].to_numpy()

    lag0 = _abs_pearson_at_lag(driver, target, lag=0)
    lagged = max(_abs_pearson_at_lag(driver, target, lag=lag) for lag in range(1, 7))

    assert lag0 > 0.15
    # Absolute gap guards robustness without being sensitive to exact ratio.
    assert (lag0 - lagged) > 0.10, (
        f"expected lag0 to exceed lagged by >0.10; got lag0={lag0:.4f}, lagged={lagged:.4f}"
    )


def test_direct_lag2_has_peak_abs_pearson_at_lag2() -> None:
    """The direct lag-2 driver should peak at lag 2 in absolute Pearson."""
    panel = generate_lagged_exog_panel(n=1500, seed=42)
    driver = panel["direct_lag2"].to_numpy()
    target = panel["target"].to_numpy()

    lag_scores = {lag: _abs_pearson_at_lag(driver, target, lag=lag) for lag in range(0, 7)}
    best_lag = max(lag_scores.items(), key=lambda item: item[1])[0]

    assert best_lag == 2, f"expected best lag 2, got {best_lag} with scores {lag_scores}"


def test_nonlinear_lag1_squared_transform_reveals_signal() -> None:
    """Squaring nonlinear_lag1 exposes quadratic coupling invisible to Pearson.

    Low raw Pearson does not imply no signal; the DGP has a quadratic term
    0.45 * (nonlinear_lag1[t-1]^2 - var).  After the nonlinear transform
    corr((x_{t-1})^2, y_t) should be materially positive.
    """
    panel = generate_lagged_exog_panel(n=1500, seed=42)
    driver = panel["nonlinear_lag1"].to_numpy()
    target = panel["target"].to_numpy()

    # Lag-1 transform: driver[:-1] aligned with target[1:]
    x_sq = driver[:-1] ** 2
    y_lagged = target[1:]

    rho = float(np.corrcoef(x_sq, y_lagged)[0, 1])
    assert rho > 0.10, (
        f"expected corr((x_lag1)^2, y) > 0.10 to confirm quadratic signal; got {rho:.4f}"
    )
