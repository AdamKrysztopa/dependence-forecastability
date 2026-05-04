"""Raw per-lag dependence curve computation."""

from __future__ import annotations

import numpy as np

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


def compute_raw_curve(
    series: np.ndarray,
    max_lag: int,
    scorer: DependenceScorer,
    *,
    exog: np.ndarray | None = None,
    min_pairs: int,
    random_state: int,
    lag_range: tuple[int, int] | None = None,
) -> np.ndarray:
    """Compute a raw dependence curve using *scorer*.

    Args:
        series: Target univariate time series.
        max_lag: Maximum lag to evaluate.
        scorer: Callable dependence scorer.
        exog: Optional exogenous series; if provided, cross-dependence is measured.
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
    return _compute_raw_curve_prescaled(
        scaled,
        predictor,
        max_lag,
        scorer,
        min_pairs=min_pairs,
        random_state=random_state,
        lag_range=lag_range,
    )


def _compute_raw_curve_prescaled(
    scaled: np.ndarray,
    predictor: np.ndarray,
    max_lag: int,
    scorer: DependenceScorer,
    *,
    min_pairs: int,
    random_state: int,
    lag_range: tuple[int, int] | None = None,
) -> np.ndarray:
    """Inner raw-curve loop on already-scaled inputs.

    Service-internal helper that skips ``_scale_series`` so callers (such as
    significance bands) can hoist scaling outside per-surrogate loops while
    keeping behavior bit-identical to :func:`compute_raw_curve`.

    Args:
        scaled: Pre-scaled target series (output of ``_scale_series``).
        predictor: Pre-scaled predictor series; equals ``scaled`` for the
            univariate case or pre-scaled exog otherwise.
        max_lag: Maximum lag to evaluate.
        scorer: Callable dependence scorer.
        min_pairs: Minimum number of sample pairs required per lag.
        random_state: Base random seed for the scorer.
        lag_range: Optional inclusive lag bounds ``(start_lag, end_lag)``.

    Returns:
        1-D array with one score per evaluated lag.
    """
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
        curve[h - lag_start] = scorer(past, future, random_state=random_state + h)
    return curve


def compute_raw_at_horizon(
    series: np.ndarray,
    h: int,
    scorer: DependenceScorer,
    *,
    exog: np.ndarray | None = None,
    min_pairs: int,
    random_state: int,
) -> float:
    """Compute raw dependence at a single horizon *h* (generic, compute-anyway).

    Returns the same value as
    ``compute_raw_curve(series, H, scorer, exog=exog, min_pairs=min_pairs,
    random_state=random_state)[h - 1]``
    for any ``H >= h`` with the default ``lag_range=None``
    (predictive-only domain ``1..H``).

    Unlike the legacy ``compute_ami_at_horizon``, this helper applies
    compute-anyway semantics: there is no underdetermined-conditioning break.
    It mirrors the generic ``compute_raw_curve`` path.

    Invariant F: ``_scale_series`` is called once on the full series (and exog)
    before slicing.  The aligned pair is never independently scaled.

    Args:
        series: Target univariate time series.
        h: Horizon index (1-based).
        scorer: Callable dependence scorer.
        exog: Optional exogenous series; if provided, cross-dependence is
            measured (``predictor = scaled exog``).
        min_pairs: Minimum number of aligned sample pairs.
        random_state: Base random seed; internally uses ``random_state + h``
            for the scorer (mirrors the full-curve convention).

    Returns:
        Scorer value at horizon *h*, or ``0.0`` when the series is too short.

    Raises:
        ValueError: If ``h < 1``.
    """
    if h < 1:
        raise ValueError("h must be >= 1")
    scaled = _scale_series(series)
    predictor = _scale_series(exog) if exog is not None else scaled
    if scaled.size - h < min_pairs:
        return 0.0
    past = predictor[:-h]
    future = scaled[h:]
    return float(scorer(past, future, random_state=random_state + h))
