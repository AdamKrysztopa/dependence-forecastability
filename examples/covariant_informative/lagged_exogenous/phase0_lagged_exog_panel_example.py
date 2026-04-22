"""Phase 0 lagged-exogenous panel example.

Demonstrates the expected lag behavior using the stable forecastability facade
and the deterministic synthetic lagged-exogenous generator.
"""

from __future__ import annotations

import numpy as np

from forecastability import generate_lagged_exog_panel


def _abs_pearson_at_lag(
    driver: np.ndarray,
    target: np.ndarray,
    *,
    lag: int,
) -> float:
    """Compute absolute Pearson correlation for a specific nonnegative lag."""
    if lag < 0:
        raise ValueError("lag must be >= 0")
    if lag == 0:
        x = driver
        y = target
    else:
        x = driver[:-lag]
        y = target[lag:]
    return float(abs(np.corrcoef(x, y)[0, 1]))


def _peak_lag(
    driver: np.ndarray,
    target: np.ndarray,
    *,
    max_lag: int,
) -> tuple[int, float]:
    """Return the lag with the strongest absolute Pearson score."""
    scores = {lag: _abs_pearson_at_lag(driver, target, lag=lag) for lag in range(max_lag + 1)}
    peak_lag = max(scores.items(), key=lambda item: item[1])[0]
    return peak_lag, scores[peak_lag]


def main() -> None:
    panel = generate_lagged_exog_panel(n=1500, seed=42)
    target = panel["target"].to_numpy()

    direct_peak_lag, direct_peak = _peak_lag(
        panel["direct_lag2"].to_numpy(),
        target,
        max_lag=6,
    )
    instant_lag0 = _abs_pearson_at_lag(panel["instant_only"].to_numpy(), target, lag=0)
    instant_lagged_max = max(
        _abs_pearson_at_lag(panel["instant_only"].to_numpy(), target, lag=lag)
        for lag in range(1, 7)
    )
    nonlinear_scores = [
        _abs_pearson_at_lag(panel["nonlinear_lag1"].to_numpy(), target, lag=lag)
        for lag in range(0, 7)
    ]

    # Nonlinear diagnostic: squared transform exposes quadratic coupling.
    nonlinear_driver = panel["nonlinear_lag1"].to_numpy()
    x_sq = nonlinear_driver[:-1] ** 2
    y_lagged = target[1:]
    rho_sq_lag1 = float(abs(np.corrcoef(x_sq, y_lagged)[0, 1]))

    print("Phase 0 lagged exogenous diagnostics")
    print("=" * 48)
    print(f"direct_lag2 peak lag in [0..6]: {direct_peak_lag} (|rho|={direct_peak:.3f})")
    print(f"instant_only |rho| lag0 vs max lag>=1: {instant_lag0:.3f} vs {instant_lagged_max:.3f}")
    print(f"nonlinear_lag1 max |rho| across lags [0..6]: {max(nonlinear_scores):.3f}")
    print(
        f"nonlinear_lag1 corr((x_lag1)^2, y): {rho_sq_lag1:.3f}"
        " [nonlinear signal, low raw Pearson does not mean no signal]"
    )


if __name__ == "__main__":
    main()
