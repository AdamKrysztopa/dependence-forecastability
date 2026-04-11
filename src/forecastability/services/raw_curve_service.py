"""Raw per-lag dependence curve computation."""

from __future__ import annotations

import numpy as np

from forecastability.metrics import _scale_series
from forecastability.scorers import DependenceScorer


def compute_raw_curve(
    series: np.ndarray,
    max_lag: int,
    scorer: DependenceScorer,
    *,
    exog: np.ndarray | None = None,
    min_pairs: int,
    random_state: int,
) -> np.ndarray:
    """Compute a raw dependence curve using *scorer*.

    Args:
        series: Target univariate time series.
        max_lag: Maximum lag to evaluate.
        scorer: Callable dependence scorer.
        exog: Optional exogenous series; if provided, cross-dependence is measured.
        min_pairs: Minimum number of sample pairs required per lag.
        random_state: Base random seed for the scorer.

    Returns:
        1-D array of shape ``(max_lag,)`` with raw dependence at each lag.
    """
    scaled = _scale_series(series)
    predictor = _scale_series(exog) if exog is not None else scaled
    curve = np.zeros(max_lag, dtype=float)
    for h in range(1, max_lag + 1):
        if scaled.size - h < min_pairs:
            break
        past = predictor[:-h]
        future = scaled[h:]
        curve[h - 1] = scorer(past, future, random_state=random_state + h)
    return curve
