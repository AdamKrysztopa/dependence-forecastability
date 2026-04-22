"""Phase 1 lagged-exogenous methods example.

Demonstrates:
1) signed cross-correlation profile on 0..max_lag,
2) cross-AMI profile with explicit lag-0 row,
3) sparse predictive lag selection via xami_sparse.
"""

from __future__ import annotations

import numpy as np

from forecastability import default_registry, generate_lagged_exog_panel
from forecastability.metrics.scorers import DependenceScorer
from forecastability.services.cross_correlation_profile_service import (
    compute_cross_correlation_profile,
)
from forecastability.services.exog_raw_curve_service import compute_exog_raw_curve_with_zero_lag
from forecastability.services.sparse_lag_selection_service import select_sparse_lags


def _top_signed_lag(profile: np.ndarray) -> tuple[int, float]:
    """Return lag index and signed value with the largest absolute magnitude."""
    lag = int(np.argmax(np.abs(profile)))
    return lag, float(profile[lag])


def main() -> None:
    panel = generate_lagged_exog_panel(n=1500, seed=42)
    target = panel["target"].to_numpy()
    direct_driver = panel["direct_lag2"].to_numpy()
    nonlinear_driver = panel["nonlinear_lag1"].to_numpy()

    registry = default_registry()
    mi_scorer = registry.get("mi").scorer
    assert isinstance(mi_scorer, DependenceScorer)

    max_lag = 6

    direct_corr = compute_cross_correlation_profile(target, direct_driver, max_lag=max_lag)
    direct_ami = compute_exog_raw_curve_with_zero_lag(
        target,
        direct_driver,
        max_lag,
        mi_scorer,
        min_pairs=30,
        random_state=42,
    )
    direct_sparse = select_sparse_lags(
        target,
        direct_driver,
        max_lag=max_lag,
        scorer=mi_scorer,
        random_state=42,
        target_name="target",
        driver_name="direct_lag2",
    )

    nonlinear_corr = compute_cross_correlation_profile(target, nonlinear_driver, max_lag=max_lag)
    nonlinear_ami = compute_exog_raw_curve_with_zero_lag(
        target,
        nonlinear_driver,
        max_lag,
        mi_scorer,
        min_pairs=30,
        random_state=42,
    )

    direct_best_lag, direct_best_corr = _top_signed_lag(direct_corr)
    nonlinear_best_lag, nonlinear_best_corr = _top_signed_lag(nonlinear_corr)

    selected_rows = [row for row in direct_sparse if row.selected_for_tensor]
    selected_rows = sorted(selected_rows, key=lambda row: row.selection_order or 0)
    selected_summary = [f"lag={row.lag} (score={row.score:.3f})" for row in selected_rows]

    print("Phase 1 lagged exogenous methods demo")
    print("=" * 44)
    print(f"direct_lag2 signed xcorr peak: lag={direct_best_lag}, rho={direct_best_corr:.3f}")
    print(
        "direct_lag2 cross_ami peak over 0..6: "
        f"lag={int(np.argmax(direct_ami))}, score={float(np.max(direct_ami)):.3f}"
    )
    print("direct_lag2 selected sparse lags: " + ", ".join(selected_summary))
    print(
        "nonlinear_lag1 max |signed xcorr| over 0..6: "
        f"lag={nonlinear_best_lag}, rho={nonlinear_best_corr:.3f}"
    )
    print(f"nonlinear_lag1 cross_ami at lag1 (0-based index 1): {nonlinear_ami[1]:.3f}")


if __name__ == "__main__":
    main()
