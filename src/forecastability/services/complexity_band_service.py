"""Application service for Entropy-Based Complexity Triage (F6).

Maps normalised permutation entropy (PE) and normalised spectral entropy (SE)
to a three-level complexity band: ``low``, ``medium``, or ``high``.

Band assignment uses a composite score ``c = (pe_norm + se_norm) / 2``:

* ``c < 0.40`` → ``"low"`` (regular / periodic dynamics)
* ``c > 0.65`` → ``"high"`` (complex / stochastic-like dynamics)
* otherwise   → ``"medium"``

These thresholds are heuristic and configurable.  They must not override
forecastability decisions derived from the AMI/pAMI pipeline.
"""

from __future__ import annotations

import numpy as np

from forecastability.scorers import (
    _choose_embedding_order,
    _permutation_entropy_scorer,
    _spectral_entropy_scorer,
)
from forecastability.triage.complexity_band import ComplexityBandResult

# Composite-score band thresholds (configurable via named constants)
_LOW_THRESHOLD: float = 0.40
_HIGH_THRESHOLD: float = 0.65

# Minimum series length for a reliability-assured estimate at m=4
_MIN_N_FOR_M4: int = 100
_MIN_N_FOR_M5: int = 1000


def _build_interpretation(
    band: str,
    pe: float,
    se: float,
) -> str:
    """Produce a one-sentence interpretation for a complexity band.

    Args:
        band: Complexity band: ``"low"``, ``"medium"``, or ``"high"``.
        pe: Normalised permutation entropy in [0, 1].
        se: Normalised spectral entropy in [0, 1].

    Returns:
        Human-readable interpretation string.
    """
    if band == "low":
        return (
            f"Low complexity (PE={pe:.2f}, SE={se:.2f}): regular or periodic structure; "
            "simple linear or seasonal models are likely adequate."
        )
    if band == "high":
        return (
            f"High complexity (PE={pe:.2f}, SE={se:.2f}): stochastic or chaotic-like dynamics; "
            "nonlinear or ensemble models may add value, but uncertainty is elevated."
        )
    return (
        f"Medium complexity (PE={pe:.2f}, SE={se:.2f}): moderate ordinal and spectral disorder; "
        "structured statistical models are a reasonable starting point."
    )


def _reliability_warning(n: int, m: int) -> str | None:
    """Return a reliability warning text or ``None`` when no concern.

    Rules follow development plan sample-size guidance:

    * m=5 requires n >= 1000
    * m=4 requires n >= 100
    * m=3 is considered reliable for n >= 20

    Args:
        n: Number of observations in the series.
        m: Embedding order used.

    Returns:
        Warning string or ``None``.
    """
    if m >= 5 and n < _MIN_N_FOR_M5:
        return (
            f"PE reliability: n={n} < 1000 with m={m}. "
            "Permutation entropy estimates may be biased; interpret with caution."
        )
    if m >= 4 and n < _MIN_N_FOR_M4:
        return (
            f"PE reliability: n={n} < 100 with m={m}. "
            "Pattern frequency estimates are noisy; treat as indicative only."
        )
    return None


def build_complexity_band(
    series: np.ndarray,
    *,
    low_threshold: float = _LOW_THRESHOLD,
    high_threshold: float = _HIGH_THRESHOLD,
) -> ComplexityBandResult:
    """Build a :class:`ComplexityBandResult` from a raw time series.

    Computes normalised permutation entropy and normalised spectral entropy,
    then assigns a complexity band based on the composite score.

    Args:
        series: 1-D float array, length >= 8.
        low_threshold: Composite score below which the band is ``"low"``.
            Default 0.40.
        high_threshold: Composite score above which the band is ``"high"``.
            Default 0.65.

    Returns:
        :class:`ComplexityBandResult` with all fields populated.

    Raises:
        ValueError: When ``series`` is not 1-D or has fewer than 8 samples.
        ValueError: When ``low_threshold >= high_threshold``.
    """
    if low_threshold >= high_threshold:
        raise ValueError(
            f"low_threshold ({low_threshold}) must be < high_threshold ({high_threshold})"
        )

    n = len(series)
    m = _choose_embedding_order(n)

    pe = _permutation_entropy_scorer(series)
    se = _spectral_entropy_scorer(series)

    composite = (pe + se) / 2.0

    if composite < low_threshold:
        band: str = "low"
    elif composite > high_threshold:
        band = "high"
    else:
        band = "medium"

    return ComplexityBandResult(
        permutation_entropy=pe,
        spectral_entropy=se,
        embedding_order=m,
        complexity_band=band,
        interpretation=_build_interpretation(band, pe, se),
        pe_reliability_warning=_reliability_warning(n, m),
    )
