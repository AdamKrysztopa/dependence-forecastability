"""Raw cross-dependence curve computation for exogenous (CCF-style) analysis."""

from __future__ import annotations

import numpy as np

from forecastability.metrics.scorers import DependenceScorer
from forecastability.services.raw_curve_service import compute_raw_curve


def compute_exog_raw_curve(
    target: np.ndarray,
    exog: np.ndarray,
    max_lag: int,
    scorer: DependenceScorer,
    *,
    min_pairs: int = 30,
    random_state: int = 42,
    lag_range: tuple[int, int] | None = None,
) -> np.ndarray:
    """Compute raw cross-dependence curve (exog_t → target_{t+h}).

    Args:
        target: Target univariate time series.
        exog: Exogenous series of the same length as *target*.
        max_lag: Maximum lag to evaluate.
        scorer: Callable dependence scorer.
        min_pairs: Minimum number of sample pairs required per lag.
        random_state: Base random seed for the scorer.
        lag_range: Optional inclusive lag bounds ``(start_lag, end_lag)``.
            ``None`` preserves the legacy predictive-only domain ``1..max_lag``.
            Use ``(0, max_lag)`` to include a zero-lag contemporaneous row.

    Returns:
        1-D array aligned to the evaluated lag range.
    """
    return compute_raw_curve(
        target,
        max_lag,
        scorer,
        exog=exog,
        min_pairs=min_pairs,
        random_state=random_state,
        lag_range=lag_range,
    )


def compute_exog_raw_curve_with_zero_lag(
    target: np.ndarray,
    exog: np.ndarray,
    max_lag: int,
    scorer: DependenceScorer,
    *,
    min_pairs: int = 30,
    random_state: int = 42,
) -> np.ndarray:
    """Compute cross-AMI profile on ``0..max_lag`` for diagnostic lag-0 reporting.

    This helper is additive to :func:`compute_exog_raw_curve` and intentionally
    includes a contemporaneous ``lag=0`` row. The lag-0 score captures
    same-timestep association and should be treated as an instant-impact
    diagnostic rather than predictive evidence.

    Args:
        target: Target univariate time series.
        exog: Exogenous series of the same length as *target*.
        max_lag: Maximum lag to evaluate.
        scorer: Callable dependence scorer.
        min_pairs: Minimum number of sample pairs required per lag.
        random_state: Base random seed for the scorer.

    Returns:
        1-D array of shape ``(max_lag + 1,)`` aligned to lags ``0..max_lag``.
    """
    return compute_exog_raw_curve(
        target,
        exog,
        max_lag,
        scorer,
        min_pairs=min_pairs,
        random_state=random_state,
        lag_range=(0, max_lag),
    )
