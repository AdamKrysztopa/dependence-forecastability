"""Domain model for Spectral Predictability result (F4)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SpectralPredictabilityResult(BaseModel):
    """Spectral predictability score for a single time series.

    Quantifies how much predictable (periodic/trend) structure exists in the
    frequency domain.  Ω near 1 indicates a spectrally concentrated series;
    Ω near 0 indicates a flat spectrum resembling white noise.

    The score is computed as ``Ω = 1 − H_nat(p) / log(N_bins)`` where
    ``p`` is the Welch-PSD normalised probability vector.

    Attributes:
        score: Spectral predictability Ω ∈ [0, 1].  Near 1 means predictable
            (concentrated spectrum).  Near 0 means flat spectrum (white noise).
        normalised_entropy: Normalised spectral entropy H / log(N_bins) ∈ [0, 1].
        n_bins: Number of frequency bins from the Welch PSD estimate.
        detrend: Detrending mode used (passed to Welch, e.g. ``"constant"``).
        interpretation: One-sentence human-readable explanation of the score.
    """

    model_config = ConfigDict(frozen=True)

    score: float
    normalised_entropy: float
    n_bins: int
    detrend: str
    interpretation: str
