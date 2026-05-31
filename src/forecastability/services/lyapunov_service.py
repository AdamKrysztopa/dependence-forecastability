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

# Maximum lag used when estimating the dominant orbital period from AMI.
# Kept short (20) so the overhead is negligible for the LLE service.
_AMI_MAX_LAG_FOR_ORBITAL_PERIOD: int = 20


def _estimate_dominant_orbital_period(series: np.ndarray) -> int | None:
    """Estimate the dominant orbital period via the first AMI minimum.

    Uses a short KSG-II AMI curve (max_lag=20) to find the lag at which AMI
    first dips below its value at lag 1, which is a standard proxy for the
    mean orbital period in Rosenstein et al. (1993).  Returns ``None`` when
    the series is too short or no minimum is found.

    Args:
        series: 1-D float array.

    Returns:
        Lag index (1-based) of the first AMI minimum, or ``None``.
    """
    n = len(series)
    max_lag = min(_AMI_MAX_LAG_FOR_ORBITAL_PERIOD, n // 4)
    if max_lag < 2:
        return None
    try:
        # local import avoids top-level circularity risk
        from forecastability.metrics.metrics import compute_ami

        ami = compute_ami(series, max_lag, min_pairs=10, random_state=0)
    except Exception:
        return None

    # Find the first local minimum within the non-zero region of the AMI curve.
    # compute_ami clips all values to >= 0, so exact zero marks break-truncated
    # or zero-information lags; searching beyond the last nonzero entry would
    # set orbital_period at the truncation point rather than a dynamic feature.
    non_zero_idx = np.flatnonzero(ami > 0)
    if non_zero_idx.size == 0:
        return None
    last_nonzero = int(non_zero_idx[-1])
    for i in range(1, last_nonzero):
        if ami[i] < ami[i - 1] and ami[i] < ami[i + 1]:
            return i + 1  # 1-based lag
    # Fallback: global minimum within non-zero region
    return int(np.argmin(ami[: last_nonzero + 1])) + 1


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
    linear_window_steps: int | None = None,
) -> tuple[float, int]:
    """Compute LLE and return ``(lambda_estimate, n_embedded_points)``.

    Returns ``(nan, 0)`` when series is too short or all-constant after
    embedding.

    Args:
        series: 1-D float array.
        embedding_dim: Embedding dimension *m*.
        delay: Time delay *tau*.
        linear_window_steps: Maximum number of divergence-tracking steps to
            use when fitting the linear slope (RVH-F07).  When ``None`` the
            full ``n // 20`` budget is used.  Rosenstein et al. (1993)
            recommend fitting only the initial linear region of the
            log-divergence curve; this argument enforces that bound.

    Returns:
        Tuple of ``(lambda_estimate, n_embedded_points)``.
    """
    embedded = _embed_series(series, m=embedding_dim, tau=delay)
    n_e = len(embedded)
    if n_e < _MIN_EMBEDDED:
        return float("nan"), n_e
    n = len(series)
    theiler_window = max(1, int(0.1 * n))
    full_steps = max(1, n // 20)
    if linear_window_steps is not None:
        evolution_steps = max(1, min(full_steps, linear_window_steps))
    else:
        evolution_steps = full_steps
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

    The linear slope is fitted only over the initial linear region of the
    log-divergence curve (RVH-F07).  The window is bounded to
    ``min(n_steps, mean_orbital_period)`` steps (floor 2), where
    ``mean_orbital_period`` is derived from the first AMI minimum within the
    non-zero AMI region — the standard Rosenstein et al. (1993) heuristic.
    This prevents the slope estimate from being distorted by the saturation
    regime of the divergence curve that appears beyond one orbital period.

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
    full_steps = max(1, n // 20)

    # RVH-F07: cap the linear-fit window at one orbital period (Rosenstein 1993:
    # fit only the initial linear divergence region, up to ~one mean orbital period).
    # Floor of 2 ensures polyfit has >= 2 points; the old `// 3` was too aggressive
    # and collapsed to 0 for n < 60 (CR-08 fix).
    orbital_period = _estimate_dominant_orbital_period(series)
    if orbital_period is not None:
        linear_window = max(2, min(full_steps, orbital_period))
    else:
        linear_window = max(2, full_steps)

    evolution_steps = linear_window

    try:
        lambda_val, n_embedded_actual = _compute_lle_safe(
            series,
            embedding_dim=embedding_dim,
            delay=delay,
            linear_window_steps=linear_window,
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
