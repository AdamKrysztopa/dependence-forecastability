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
) -> np.ndarray:
    """Compute raw cross-dependence curve (exog_t → target_{t+h}).

    Args:
        target: Target univariate time series.
        exog: Exogenous series of the same length as *target*.
        max_lag: Maximum lag to evaluate.
        scorer: Callable dependence scorer.
        min_pairs: Minimum number of sample pairs required per lag.
        random_state: Base random seed for the scorer.

    Returns:
        1-D array of shape ``(max_lag,)`` with raw cross-dependence at each lag.
    """
    return compute_raw_curve(
        target,
        max_lag,
        scorer,
        exog=exog,
        min_pairs=min_pairs,
        random_state=random_state,
    )
