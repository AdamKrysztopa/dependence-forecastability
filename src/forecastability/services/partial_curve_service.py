"""Partial (residualized) per-lag dependence curve computation."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LinearRegression

from forecastability.metrics import _scale_series
from forecastability.scorers import DependenceScorer


def _residualize(
    scaled: np.ndarray,
    h: int,
    past: np.ndarray,
    future: np.ndarray,
    *,
    exog: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Linearly residualize past and future on intermediate lags.

    Residualization is linear. For nonlinear scorers (MI, distance
    correlation) this removes only linear mediation; nonlinear indirect
    dependence may remain. For Pearson this yields exact partial correlation.

    Args:
        scaled: Scaled target series of length ``N``.
        h: Lag/horizon index (1-based).
        past: Past predictor values aligned to the horizon.
        future: Future target values aligned to the horizon.
        exog: Optional exogenous series; if provided, only *future* is
            residualized (past already comes from the exogenous predictor).

    Returns:
        Tuple of ``(residualized_past, residualized_future)``.
    """
    if h <= 1:
        return past, future
    n_rows = scaled.size - h
    cols = [scaled[offset : offset + n_rows] for offset in range(1, h)]
    z = np.column_stack(cols)
    model_future = LinearRegression().fit(z, future)
    res_future = future - model_future.predict(z)
    if exog is not None:
        return past.copy(), res_future
    model_past = LinearRegression().fit(z, past)
    return past - model_past.predict(z), res_future


def compute_partial_curve(
    series: np.ndarray,
    max_lag: int,
    scorer: DependenceScorer,
    *,
    exog: np.ndarray | None = None,
    min_pairs: int,
    random_state: int,
) -> np.ndarray:
    """Compute a partial (residualized) dependence curve using *scorer*.

    Args:
        series: Target univariate time series.
        max_lag: Maximum lag to evaluate.
        scorer: Callable dependence scorer.
        exog: Optional exogenous series; if provided, only future target
            values are residualized (past comes from the exogenous predictor).
        min_pairs: Minimum number of sample pairs required per lag.
        random_state: Base random seed for the scorer.

    Returns:
        1-D array of shape ``(max_lag,)`` with partial dependence at each lag.
    """
    scaled = _scale_series(series)
    predictor = _scale_series(exog) if exog is not None else scaled
    curve = np.zeros(max_lag, dtype=float)
    for h in range(1, max_lag + 1):
        if scaled.size - h < min_pairs:
            break
        past = predictor[:-h]
        future = scaled[h:]
        res_past, res_future = _residualize(scaled, h, past, future, exog=exog)
        curve[h - 1] = scorer(res_past, res_future, random_state=random_state + h)
    return curve
