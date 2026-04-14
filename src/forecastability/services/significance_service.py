"""Surrogate-based significance band computation for generic scorers."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from typing import cast

import numpy as np

from forecastability.diagnostics.surrogates import phase_surrogates
from forecastability.metrics.scorers import DependenceScorer, ScorerInfo
from forecastability.services.partial_curve_service import compute_partial_curve
from forecastability.services.raw_curve_service import compute_raw_curve


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

    Returns:
        ``(lower_band, upper_band)`` arrays of shape ``(max_lag,)``.
    """
    surr = phase_surrogates(series, n_surrogates=n_surrogates, random_state=random_state)
    compute_fn = compute_raw_curve if which == "raw" else compute_partial_curve
    n_workers = (os.cpu_count() or 1) if n_jobs == -1 else n_jobs
    bivariate_scorer = cast(DependenceScorer, info.scorer)

    def _eval(idx: int) -> np.ndarray:
        seed = random_state + idx + 1
        return compute_fn(
            surr[idx], max_lag, bivariate_scorer, exog=exog, min_pairs=min_pairs, random_state=seed
        )

    if n_workers == 1:
        values: list[np.ndarray] = [_eval(i) for i in range(surr.shape[0])]
    else:
        with ThreadPoolExecutor(max_workers=min(n_workers, surr.shape[0])) as pool:
            values = list(pool.map(_eval, range(surr.shape[0])))

    stacked = np.vstack(values)
    lower = np.percentile(stacked, 2.5, axis=0)
    upper = np.percentile(stacked, 97.5, axis=0)
    return lower, upper
