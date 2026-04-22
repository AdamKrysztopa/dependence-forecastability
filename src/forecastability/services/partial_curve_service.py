"""Partial (residualized) per-lag dependence curve computation."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LinearRegression

from forecastability.metrics import _scale_series
from forecastability.metrics.scorers import DependenceScorer


def _resolve_lag_range(
    *,
    max_lag: int,
    lag_range: tuple[int, int] | None,
) -> tuple[int, int]:
    """Resolve and validate the evaluated lag domain.

    Args:
        max_lag: Maximum lag accepted by the caller.
        lag_range: Optional inclusive ``(start_lag, end_lag)`` range.

    Returns:
        Inclusive ``(start_lag, end_lag)`` lag bounds.

    Raises:
        ValueError: If lag bounds are invalid.
    """
    if max_lag < 0:
        raise ValueError(f"max_lag must be >= 0, got {max_lag}")

    if lag_range is None:
        return 1, max_lag

    lag_start, lag_end = lag_range
    if lag_start < 0:
        raise ValueError(f"lag_range start must be >= 0, got {lag_start}")
    if lag_end < lag_start:
        raise ValueError(f"lag_range end must be >= start, got start={lag_start}, end={lag_end}")
    if lag_end > max_lag:
        raise ValueError(f"lag_range end must be <= max_lag, got end={lag_end}, max_lag={max_lag}")
    return lag_start, lag_end


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
    lag_range: tuple[int, int] | None = None,
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
        lag_range: Optional inclusive lag bounds ``(start_lag, end_lag)``.
            ``None`` preserves the legacy predictive-only domain ``1..max_lag``.
            Use ``(0, max_lag)`` to include a zero-lag contemporaneous row.

    Returns:
        1-D array with one score per evaluated lag.

        - ``lag_range is None``: shape ``(max_lag,)`` aligned to ``1..max_lag``
          (legacy behavior).
        - explicit ``lag_range``: shape ``(end_lag - start_lag + 1)`` aligned to
          ``start_lag..end_lag``.
    """
    scaled = _scale_series(series)
    predictor = _scale_series(exog) if exog is not None else scaled
    lag_start, lag_end = _resolve_lag_range(max_lag=max_lag, lag_range=lag_range)

    if lag_end < lag_start:
        return np.zeros(0, dtype=float)

    curve = np.zeros(lag_end - lag_start + 1, dtype=float)
    for h in range(lag_start, lag_end + 1):
        if scaled.size - h < min_pairs:
            break
        if h == 0:
            past = predictor
            future = scaled
        else:
            past = predictor[:-h]
            future = scaled[h:]
        res_past, res_future = _residualize(scaled, h, past, future, exog=exog)
        curve[h - lag_start] = scorer(res_past, res_future, random_state=random_state + h)
    return curve
