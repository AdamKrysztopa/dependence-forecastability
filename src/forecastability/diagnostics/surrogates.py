"""Surrogate generation and significance bands."""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from typing import Literal

import numpy as np

from forecastability.domain.results.significance_correction import (
    SignificanceCorrectionResult,
)
from forecastability.metrics.metrics import compute_ami, compute_pami_linear_residual
from forecastability.utils.validation import validate_time_series


def _eval_surrogate(
    args: tuple[np.ndarray, str, int, int, int, str],
) -> np.ndarray:
    """Evaluate one surrogate curve (top-level so it is picklable).

    Args:
        args: Tuple of
            ``(surrogate, metric_name, max_lag, n_neighbors, seed, estimator)``.

    Returns:
        1-D dependence curve for this surrogate.
    """
    surrogate, metric_name, max_lag, n_neighbors, seed, estimator = args
    if metric_name == "ami":
        return compute_ami(
            surrogate, max_lag, n_neighbors=n_neighbors, random_state=seed,
            estimator=estimator,  # type: ignore[arg-type]
        )
    return compute_pami_linear_residual(
        surrogate, max_lag, n_neighbors=n_neighbors, random_state=seed,
        estimator=estimator,  # type: ignore[arg-type]
    )


def phase_surrogates(
    ts: np.ndarray,
    *,
    n_surrogates: int,
    random_state: int = 42,
) -> np.ndarray:
    """Generate phase-randomized surrogates preserving amplitude spectrum.

    .. note::
        Phase-randomization preserves the power spectrum (amplitude spectrum)
        but destroys higher-order moments (skewness, kurtosis, nonlinear
        structure).  The resulting surrogate null distribution is therefore
        only *approximately* exchangeable with the observed test statistic —
        it is the null for *linear* structure, not arbitrary dependence.
        This is acknowledged in the RVH-F18 methods note and the migration
        guide for v0.5.0.
    """
    if n_surrogates < 1:
        raise ValueError("n_surrogates must be >= 1")

    arr = validate_time_series(ts, min_length=16)
    rng = np.random.default_rng(random_state)

    spectrum = np.fft.rfft(arr)
    n_freq = spectrum.size

    # Batched phase matrix — one rng.uniform call for all surrogates.
    # DC bin (index 0) and Nyquist bin (index -1, even-length only) keep phase
    # 1+0j to preserve Hermitian symmetry (Invariant H).
    phase = np.ones((n_surrogates, n_freq), dtype=complex)
    if arr.size % 2 == 0:
        # Even-length: interior bins are indices 1 .. n_freq-2
        n_interior = max(n_freq - 2, 0)
        if n_interior > 0:
            phase[:, 1:-1] = np.exp(
                1j * rng.uniform(0.0, 2.0 * np.pi, (n_surrogates, n_interior))
            )
    else:
        # Odd-length: all bins after DC are interior
        n_interior = max(n_freq - 1, 0)
        if n_interior > 0:
            phase[:, 1:] = np.exp(
                1j * rng.uniform(0.0, 2.0 * np.pi, (n_surrogates, n_interior))
            )

    # Single batched irfft: shape (n_surrogates, arr.size)
    surrogates = np.fft.irfft(spectrum[None, :] * phase, n=arr.size, axis=1)
    return surrogates


def _build_surrogate_matrix(
    ts: np.ndarray,
    *,
    metric_name: str,
    max_lag: int,
    n_surrogates: int,
    n_neighbors: int,
    random_state: int,
    n_jobs: int,
    estimator: str,
) -> np.ndarray:
    """Build the surrogate curve matrix of shape ``(n_surrogates, max_lag)``.

    Internal helper shared by :func:`compute_significance_bands` and
    :func:`compute_significance_bands_corrected`.
    """
    surrogates = phase_surrogates(
        ts,
        n_surrogates=n_surrogates,
        random_state=random_state,
    )

    args_list = [
        (surrogates[i], metric_name, max_lag, n_neighbors, random_state + i + 1, estimator)
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

    return result


def _validate_significance_bands_args(
    metric_name: str,
    max_lag: int,
    n_surrogates: int,
    alpha: float,
    n_jobs: int,
) -> None:
    """Validate shared arguments for significance-band functions."""
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
    estimator: str = "ksg2",
    correction: Literal["romano_wolf", "bh", "by", "none"] = "none",
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
        estimator: MI estimator to use. ``"ksg2"`` (default) uses the v0.5.0
            KSG-II Chebyshev kernel. ``"ksg1_sklearn"`` reproduces v0.4.3 numerics.
        correction: Significance correction mode.  Default ``"none"`` preserves
            the legacy percentile-band return semantics.  Pass
            ``"romano_wolf"``, ``"bh"``, or ``"by"`` to have the surrogate
            matrix routed through :class:`SignificanceCorrectionService`
            internally (the corrected mask is embedded in the returned bands:
            lags not in the corrected mask have their upper band set to
            ``+inf`` so the observed value cannot exceed it).

    Returns:
        ``(lower_band, upper_band)`` arrays of shape ``(max_lag,)``.
        When ``correction != "none"`` the upper band for non-significant lags
        is set to ``np.inf`` (observed cannot exceed it), preserving the
        contract that a lag is significant iff ``observed > upper_band``.
    """
    _validate_significance_bands_args(metric_name, max_lag, n_surrogates, alpha, n_jobs)

    surrogate_matrix = _build_surrogate_matrix(
        ts,
        metric_name=metric_name,
        max_lag=max_lag,
        n_surrogates=n_surrogates,
        n_neighbors=n_neighbors,
        random_state=random_state,
        n_jobs=n_jobs,
        estimator=estimator,
    )

    lower = np.percentile(surrogate_matrix, 100.0 * alpha / 2.0, axis=0)
    upper = np.percentile(surrogate_matrix, 100.0 * (1.0 - alpha / 2.0), axis=0)

    if correction != "none":
        from forecastability.services.significance_correction_service import (
            SignificanceCorrectionService,
        )

        # Compute observed curve to get the corrected mask.
        if metric_name == "ami":
            observed = compute_ami(ts, max_lag, n_neighbors=n_neighbors, random_state=random_state)
        else:
            observed = compute_pami_linear_residual(
                ts, max_lag, n_neighbors=n_neighbors, random_state=random_state
            )

        svc = SignificanceCorrectionService(correction=correction, alpha=alpha)
        corr_result = svc.correct(surrogate_matrix, observed)
        # Lags not in corrected mask: set upper to +inf (not significant).
        not_significant = ~corr_result.corrected_mask
        upper = upper.copy()
        upper[not_significant] = np.inf

    return lower, upper


def compute_significance_bands_corrected(
    ts: np.ndarray,
    observed: np.ndarray,
    *,
    metric_name: str,
    max_lag: int,
    n_surrogates: int = 99,
    alpha: float = 0.05,
    n_neighbors: int = 8,
    random_state: int = 42,
    n_jobs: int = 1,
    estimator: str = "ksg2",
    correction: Literal["romano_wolf", "bh", "by", "none"] = "romano_wolf",
) -> SignificanceCorrectionResult:
    """Compute family-wise corrected significance for a pre-computed observed curve.

    This is the primary entry point for RVH-F03 significance correction.
    It builds the surrogate matrix and routes it through
    :class:`~forecastability.services.significance_correction_service.SignificanceCorrectionService`.

    The surrogate matrix is constructed using phase-randomised surrogates;
    the observed curve is supplied by the caller (already computed, no
    recomputation).

    Args:
        ts: Univariate time series (used to generate phase surrogates).
        observed: Pre-computed observed MI curve of shape ``(max_lag,)``.
        metric_name: ``"ami"`` or ``"pami_linear_residual"``.
        max_lag: Maximum lag, must equal ``observed.size``.
        n_surrogates: Number of phase-randomised surrogates (≥ 99).
        alpha: Nominal error rate (FWER for romano_wolf; FDR for bh/by).
        n_neighbors: Number of kNN neighbours for MI estimation of surrogates.
        random_state: Base random seed.
        n_jobs: Number of parallel workers.  ``1`` = serial (default).
        estimator: MI estimator for surrogate curves.
        correction: Correction method.  Default ``"romano_wolf"``.

    Returns:
        :class:`~forecastability.domain.results.significance_correction.SignificanceCorrectionResult`
        with the corrected significance mask.
    """
    _validate_significance_bands_args(metric_name, max_lag, n_surrogates, alpha, n_jobs)
    observed = np.asarray(observed, dtype=float)
    if observed.size != max_lag:
        raise ValueError(
            f"observed.size={observed.size} does not match max_lag={max_lag}"
        )

    from forecastability.services.significance_correction_service import (
        SignificanceCorrectionService,
    )

    surrogate_matrix = _build_surrogate_matrix(
        ts,
        metric_name=metric_name,
        max_lag=max_lag,
        n_surrogates=n_surrogates,
        n_neighbors=n_neighbors,
        random_state=random_state,
        n_jobs=n_jobs,
        estimator=estimator,
    )

    svc = SignificanceCorrectionService(correction=correction, alpha=alpha)
    return svc.correct(surrogate_matrix, observed)
