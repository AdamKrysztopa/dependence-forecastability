"""Surrogate-based significance band computation for generic scorers."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from typing import cast

import numpy as np

from forecastability.diagnostics.surrogates import phase_surrogates
from forecastability.diagnostics.transfer_entropy import compute_transfer_entropy_curve
from forecastability.metrics import _scale_series
from forecastability.metrics.scorers import DependenceScorer, ScorerInfo
from forecastability.services.partial_curve_service import (
    _compute_partial_curve_prescaled,
)
from forecastability.services.raw_curve_service import (
    _compute_raw_curve_prescaled,
    _resolve_lag_range,
)

_MIN_SIGNIFICANCE_SURROGATES = 99


def _validate_significance_surrogate_count(n_surrogates: int) -> None:
    if n_surrogates < _MIN_SIGNIFICANCE_SURROGATES:
        raise ValueError("n_surrogates must be >= 99")


def _validate_n_jobs(n_jobs: int) -> None:
    if n_jobs != -1 and n_jobs < 1:
        raise ValueError("n_jobs must be -1 or >= 1")


def compute_significance_bands_generic(
    series: np.ndarray,
    n_surrogates: int,
    random_state: int,
    max_lag: int,
    info: ScorerInfo,
    which: str,
    *,
    exog: np.ndarray | None = None,
    min_pairs: int,
    n_jobs: int,
    lag_range: tuple[int, int] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute surrogate significance bands for any scorer.

    Uses :class:`~concurrent.futures.ThreadPoolExecutor` for parallelism
    (scorer callables may not be picklable, so processes cannot be used here;
    sklearn's kNN estimator partially releases the GIL).

    Args:
        series: Cached time series (target).
        n_surrogates: Number of phase-randomised surrogates.
        random_state: Base random seed.
        max_lag: Number of lags to evaluate.
        info: Scorer metadata from the registry.
        which: ``"raw"`` or ``"partial"``.
        exog: Optional cached exogenous series.
        min_pairs: Minimum sample pairs per horizon.
        n_jobs: Thread-pool workers.  ``-1`` = all CPUs.  ``1`` = serial.
        lag_range: Optional inclusive lag bounds passed to curve computation.
            ``None`` preserves legacy ``1..max_lag`` behavior. Use
            ``(0, max_lag)`` to include a lag-0 surrogate band.

    Returns:
        ``(lower_band, upper_band)`` arrays aligned to the evaluated lag range.
    """
    if which not in {"raw", "partial"}:
        raise ValueError(f"which must be 'raw' or 'partial', got {which!r}")
    if max_lag < 0:
        raise ValueError(f"max_lag must be >= 0, got {max_lag}")
    if min_pairs < 1:
        raise ValueError(f"min_pairs must be >= 1, got {min_pairs}")
    _validate_n_jobs(n_jobs)
    if exog is not None and exog.shape != series.shape:
        raise ValueError("exog must match series shape for significance bands")
    _validate_significance_surrogate_count(n_surrogates)
    lag_start, lag_end = _resolve_lag_range(max_lag=max_lag, lag_range=lag_range)
    curve_size = max(lag_end - lag_start + 1, 0)

    surr = phase_surrogates(series, n_surrogates=n_surrogates, random_state=random_state)
    n_workers = (os.cpu_count() or 1) if n_jobs == -1 else n_jobs
    bivariate_scorer = cast(DependenceScorer, info.scorer)

    # Hoist exog scaling outside the per-surrogate loop (Invariant F: each
    # surrogate target is still scaled once, but the exog predictor is scaled
    # exactly once per band call).
    scaled_exog = _scale_series(exog) if exog is not None else None
    exog_present = exog is not None

    def _eval_raw(idx: int) -> np.ndarray:
        seed = random_state + idx + 1
        scaled_surr = _scale_series(surr[idx])
        predictor = scaled_exog if scaled_exog is not None else scaled_surr
        return _compute_raw_curve_prescaled(
            scaled_surr,
            predictor,
            max_lag,
            bivariate_scorer,
            min_pairs=min_pairs,
            random_state=seed,
            lag_range=lag_range,
        )

    def _eval_partial(idx: int) -> np.ndarray:
        seed = random_state + idx + 1
        scaled_surr = _scale_series(surr[idx])
        predictor = scaled_exog if scaled_exog is not None else scaled_surr
        return _compute_partial_curve_prescaled(
            scaled_surr,
            predictor,
            max_lag,
            bivariate_scorer,
            exog_present=exog_present,
            min_pairs=min_pairs,
            random_state=seed,
            lag_range=lag_range,
        )

    eval_fn = _eval_raw if which == "raw" else _eval_partial

    n_surr = surr.shape[0]
    result = np.empty((n_surr, curve_size), dtype=float)
    if n_workers == 1:
        for i in range(n_surr):
            result[i] = eval_fn(i)
    else:
        with ThreadPoolExecutor(max_workers=min(n_workers, n_surr)) as pool:
            for i, row in enumerate(pool.map(eval_fn, range(n_surr))):
                result[i] = row

    lower = np.percentile(result, 2.5, axis=0)
    upper = np.percentile(result, 97.5, axis=0)
    return lower, upper


def compute_significance_bands_transfer_entropy(
    series: np.ndarray,
    n_surrogates: int,
    random_state: int,
    max_lag: int,
    *,
    source: np.ndarray | None = None,
    min_pairs: int,
    n_jobs: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute surrogate significance bands for directional transfer entropy.

    The TE curve is evaluated directly at each lag on full source/target
    series (or surrogate targets), preserving lag semantics:

    ``TE(X -> Y | lag=h) = I(Y_t ; X_{t-h} | Y_{t-1}, ..., Y_{t-h+1})``.

    Args:
        series: Target series ``Y``.
        n_surrogates: Number of phase-randomized surrogates.
        random_state: Base random seed.
        max_lag: Maximum lag to evaluate.
        source: Optional source series ``X``. When ``None``, uses each
            surrogate as both source and target (auto-TE setting).
        min_pairs: Minimum aligned pairs per lag.
        n_jobs: Thread-pool workers. ``-1`` = all CPUs. ``1`` = serial.

    Returns:
        ``(lower_band, upper_band)`` arrays of shape ``(max_lag,)``.
    """
    if max_lag < 1:
        raise ValueError(f"max_lag must be >= 1, got {max_lag}")
    if min_pairs < 1:
        raise ValueError(f"min_pairs must be >= 1, got {min_pairs}")
    _validate_n_jobs(n_jobs)
    if source is not None and source.shape != series.shape:
        raise ValueError("source must match target shape for TE significance bands")
    _validate_significance_surrogate_count(n_surrogates)

    surr = phase_surrogates(series, n_surrogates=n_surrogates, random_state=random_state)
    n_workers = (os.cpu_count() or 1) if n_jobs == -1 else n_jobs

    def _eval(idx: int) -> np.ndarray:
        seed = random_state + idx + 1
        surrogate_target = surr[idx]
        surrogate_source = source if source is not None else surrogate_target
        return compute_transfer_entropy_curve(
            surrogate_source,
            surrogate_target,
            max_lag=max_lag,
            min_pairs=min_pairs,
            random_state=seed,
        )

    n_surr = surr.shape[0]
    result = np.empty((n_surr, max_lag), dtype=float)
    if n_workers == 1:
        for i in range(n_surr):
            result[i] = _eval(i)
    else:
        with ThreadPoolExecutor(max_workers=min(n_workers, n_surr)) as pool:
            for i, row in enumerate(pool.map(_eval, range(n_surr))):
                result[i] = row

    lower = np.percentile(result, 2.5, axis=0)
    upper = np.percentile(result, 97.5, axis=0)
    return lower, upper
