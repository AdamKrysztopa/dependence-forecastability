"""Application service for Largest Lyapunov Exponent estimation (F5).

Implements the Rosenstein et al. (1993) algorithm on a delay-embedded
phase-space reconstruction (Takens' theorem).

This is an experimental diagnostic — results must be combined with other
forecastability evidence and must not drive triage decisions in isolation.
"""

from __future__ import annotations

import math

import numpy as np

from forecastability.metrics.scorers import _embed_series, _estimate_lle_rosenstein
from forecastability.triage.lyapunov import LargestLyapunovExponentResult

# Minimum number of embedded points required for a meaningful estimate.
_MIN_EMBEDDED: int = 10

# Thresholds for lambda interpretation.
_CHAOTIC_THRESHOLD: float = 0.1
_STABLE_THRESHOLD: float = -0.1


def _interpret_lle(lambda_estimate: float) -> str:
    """Map a lambda estimate to a human-readable interpretation string.

    Args:
        lambda_estimate: Estimated LLE, may be ``nan``.

    Returns:
        One-sentence interpretation.
    """
    if math.isnan(lambda_estimate):
        return "Insufficient data for reliable LLE estimation"
    if lambda_estimate > _CHAOTIC_THRESHOLD:
        return (
            f"Positive divergence rate (λ̂={lambda_estimate:.4f}); consistent with "
            "chaotic dynamics but stochastic noise can also produce positive λ̂ — "
            "do not interpret as chaos without corroborating evidence "
            "(experimental)"
        )
    if lambda_estimate < _STABLE_THRESHOLD:
        return f"Converging trajectories — stable attractor region (λ̂={lambda_estimate:.4f})"
    return f"Marginally stable or near-zero divergence (λ̂={lambda_estimate:.4f})"


def _lle_reliability_warning(n: int, *, m: int) -> str:
    """Return a mandatory reliability warning for the LLE estimate.

    Rules (from Rosenstein et al., 1993):

    * n should be far larger than ``10**m`` for reliable phase-space coverage.
    * Always warn that the result is experimental.

    Args:
        n: Original series length.
        m: Embedding dimension used.

    Returns:
        Warning string; always non-empty.
    """
    min_n = 10**m
    if n < min_n:
        return (
            f"EXPERIMENTAL — LLE unreliable: n={n} is below the recommended "
            f"minimum of 10^m={min_n} for m={m}. "
            "Do not use as a sole triage decision-maker."
        )
    return (
        f"EXPERIMENTAL — LLE is sensitive to noise, non-stationarity, and "
        f"embedding parameters (m={m}). "
        "Do not use as a sole triage decision-maker."
    )


def _compute_lle_safe(
    series: np.ndarray,
    *,
    embedding_dim: int,
    delay: int,
) -> tuple[float, int]:
    """Compute LLE and return ``(lambda_estimate, n_embedded_points)``.

    Returns ``(nan, 0)`` when series is too short or all-constant after
    embedding.

    Args:
        series: 1-D float array.
        embedding_dim: Embedding dimension *m*.
        delay: Time delay *tau*.

    Returns:
        Tuple of ``(lambda_estimate, n_embedded_points)``.
    """
    embedded = _embed_series(series, m=embedding_dim, tau=delay)
    n_e = len(embedded)
    if n_e < _MIN_EMBEDDED:
        return float("nan"), n_e
    n = len(series)
    theiler_window = max(1, int(0.1 * n))
    evolution_steps = max(1, n // 20)
    lambda_val = _estimate_lle_rosenstein(
        embedded,
        theiler_window=theiler_window,
        evolution_steps=evolution_steps,
    )
    return lambda_val, n_e


def build_largest_lyapunov_exponent(
    series: np.ndarray,
    *,
    embedding_dim: int = 3,
    delay: int = 1,
) -> LargestLyapunovExponentResult:
    """Run Rosenstein LLE estimation on a univariate series.

    Returns a safe result with ``lambda_estimate=nan`` and a reliability
    warning when estimation fails due to insufficient data or numerical
    issues.  Unexpected errors propagate to the caller (the triage stage
    wraps calls in a broad try/except for experimental safety).

    Args:
        series: 1-D float array of observations.
        embedding_dim: Embedding dimension *m* (default 3).
        delay: Time delay *tau* between embedding elements (default 1).

    Returns:
        :class:`~forecastability.triage.lyapunov.LargestLyapunovExponentResult`
        with all fields populated.
    """
    n = len(series)
    n_embedded = max(0, n - (embedding_dim - 1) * delay)
    evolution_steps = max(1, n // 20)

    try:
        lambda_val, n_embedded_actual = _compute_lle_safe(
            series,
            embedding_dim=embedding_dim,
            delay=delay,
        )
    except (ValueError, OverflowError):
        lambda_val = float("nan")
        n_embedded_actual = n_embedded

    return LargestLyapunovExponentResult(
        lambda_estimate=lambda_val,
        embedding_dim=embedding_dim,
        delay=delay,
        evolution_steps=evolution_steps,
        n_embedded_points=n_embedded_actual,
        interpretation=_interpret_lle(lambda_val),
        reliability_warning=_lle_reliability_warning(n, m=embedding_dim),
    )
