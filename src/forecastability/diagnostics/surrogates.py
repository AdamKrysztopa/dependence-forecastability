"""Surrogate generation and significance bands."""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from forecastability.metrics.metrics import compute_ami, compute_pami_linear_residual
from forecastability.utils.validation import validate_time_series


def _eval_surrogate(
    args: tuple[np.ndarray, str, int, int, int],
) -> np.ndarray:
    """Evaluate one surrogate curve (top-level so it is picklable).

    Args:
        args: Tuple of ``(surrogate, metric_name, max_lag, n_neighbors, seed)``.

    Returns:
        1-D dependence curve for this surrogate.
    """
    surrogate, metric_name, max_lag, n_neighbors, seed = args
    if metric_name == "ami":
        return compute_ami(surrogate, max_lag, n_neighbors=n_neighbors, random_state=seed)
    return compute_pami_linear_residual(
        surrogate, max_lag, n_neighbors=n_neighbors, random_state=seed
    )


def phase_surrogates(
    ts: np.ndarray,
    *,
    n_surrogates: int,
    random_state: int = 42,
) -> np.ndarray:
    """Generate phase-randomized surrogates preserving amplitude spectrum."""
    if n_surrogates < 1:
        raise ValueError("n_surrogates must be >= 1")

    arr = validate_time_series(ts, min_length=16)
    rng = np.random.default_rng(random_state)

    spectrum = np.fft.rfft(arr)
    n_freq = spectrum.size

    surrogates = np.empty((n_surrogates, arr.size), dtype=float)
    for idx in range(n_surrogates):
        phase = np.ones(n_freq, dtype=complex)
        if arr.size % 2 == 0:
            random_count = max(n_freq - 2, 0)
            if random_count > 0:
                phase[1:-1] = np.exp(1j * rng.uniform(0.0, 2.0 * np.pi, random_count))
        else:
            random_count = max(n_freq - 1, 0)
            if random_count > 0:
                phase[1:] = np.exp(1j * rng.uniform(0.0, 2.0 * np.pi, random_count))

        surrogates[idx] = np.fft.irfft(spectrum * phase, n=arr.size)

    return surrogates


def compute_significance_bands(
    ts: np.ndarray,
    *,
    metric_name: str,
    max_lag: int,
    n_surrogates: int = 99,
    alpha: float = 0.05,
    n_neighbors: int = 8,
    random_state: int = 42,
    n_jobs: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute surrogate lower/upper significance bands.

    Args:
        ts: Univariate time series.
        metric_name: ``"ami"`` or ``"pami_linear_residual"``.
        max_lag: Maximum lag to evaluate.
        n_surrogates: Number of phase-randomised surrogates (≥ 99).
        alpha: Two-sided significance level (default 0.05).
        n_neighbors: Number of kNN neighbours for MI estimation.
        random_state: Base random seed.
        n_jobs: Number of parallel workers.  ``1`` = serial (default).
            ``-1`` = all CPUs.  Parallelism uses :class:`ProcessPoolExecutor`.

    Returns:
        ``(lower_band, upper_band)`` arrays of shape ``(max_lag,)``.
    """
    if n_surrogates < 99:
        raise ValueError("n_surrogates must be >= 99")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    if metric_name not in {"ami", "pami_linear_residual"}:
        raise ValueError(
            "metric_name must be 'ami' or 'pami_linear_residual', "
            f"got {metric_name!r}"
        )
    if max_lag < 1:
        raise ValueError(f"max_lag must be >= 1, got {max_lag}")
    if n_jobs != -1 and n_jobs < 1:
        raise ValueError("n_jobs must be -1 or >= 1")

    surrogates = phase_surrogates(
        ts,
        n_surrogates=n_surrogates,
        random_state=random_state,
    )

    args_list = [
        (surrogates[i], metric_name, max_lag, n_neighbors, random_state + i + 1)
        for i in range(n_surrogates)
    ]

    result = np.empty((n_surrogates, max_lag), dtype=float)
    if n_jobs == 1:
        for i, args in enumerate(args_list):
            result[i] = _eval_surrogate(args)
    else:
        n_workers = (os.cpu_count() or 1) if n_jobs == -1 else n_jobs
        with ProcessPoolExecutor(max_workers=min(n_workers, n_surrogates)) as pool:
            for i, row in enumerate(pool.map(_eval_surrogate, args_list)):
                result[i] = row

    lower = np.percentile(result, 100.0 * alpha / 2.0, axis=0)
    upper = np.percentile(result, 100.0 * (1.0 - alpha / 2.0), axis=0)
    return lower, upper
