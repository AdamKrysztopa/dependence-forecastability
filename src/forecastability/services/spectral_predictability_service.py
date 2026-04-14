"""Application service for Spectral Predictability (F4).

Computes the spectral predictability score Ω from a raw time series using
the Welch PSD estimate and normalised spectral entropy.

Ω = 1 − H_nat(p) / log(N_bins)

where H_nat is the natural-log spectral entropy and N_bins is the number of
frequency bins in the Welch estimate.
"""

from __future__ import annotations

import numpy as np

from forecastability.diagnostics.spectral_utils import compute_normalised_psd, spectral_entropy
from forecastability.triage.spectral_predictability import SpectralPredictabilityResult


def _build_interpretation(score: float) -> str:
    """Produce a one-sentence interpretation for a spectral predictability score.

    Args:
        score: Spectral predictability Ω ∈ [0, 1].

    Returns:
        Human-readable interpretation string.
    """
    if score >= 0.70:
        return (
            f"High spectral predictability (Ω={score:.2f}): spectrally concentrated dynamics; "
            "strong periodic or trend structure detected."
        )
    if score >= 0.40:
        return (
            f"Moderate spectral predictability (Ω={score:.2f}): mixed frequency content; "
            "some exploitable structure present."
        )
    return (
        f"Low spectral predictability (Ω={score:.2f}): flat spectrum; "
        "dynamics resemble white noise."
    )


def build_spectral_predictability(
    series: np.ndarray,
    *,
    detrend: str = "constant",
    nperseg: int | None = None,
) -> SpectralPredictabilityResult:
    """Build a :class:`SpectralPredictabilityResult` from a raw time series.

    Computes Welch PSD, normalises by bin count, and derives the spectral
    predictability score Ω = 1 − H_nat / log(N_bins).

    Args:
        series: 1-D float array, length >= 8.
        detrend: Detrending mode passed to ``scipy.signal.welch``.  Default
            ``"constant"`` mean-centres the segments.
        nperseg: Segment length passed to ``scipy.signal.welch``.  Defaults to
            ``min(len(series), 256)``.

    Returns:
        :class:`SpectralPredictabilityResult` with all fields populated.

    Raises:
        ValueError: When ``series`` is not 1-D or has fewer than 8 samples.
    """
    _, p = compute_normalised_psd(series, nperseg=nperseg, detrend=detrend)
    h = spectral_entropy(p, base=np.e)
    n_bins = len(p)
    h_max = float(np.log(n_bins))
    if h_max < 1e-15:
        normalised_entropy = 0.0
    else:
        normalised_entropy = min(h / h_max, 1.0)
    score = 1.0 - normalised_entropy
    return SpectralPredictabilityResult(
        score=score,
        normalised_entropy=normalised_entropy,
        n_bins=n_bins,
        detrend=detrend,
        interpretation=_build_interpretation(score),
    )
