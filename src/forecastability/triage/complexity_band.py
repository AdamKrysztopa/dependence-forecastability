"""Domain model for Entropy-Based Complexity Triage result (F6)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ComplexityBandResult(BaseModel):
    """Entropy-based complexity classification for a single time series.

    Combines normalised permutation entropy (PE) and normalised spectral
    entropy (SE) to assign a complexity band.  The band is informational
    only and must not be used as the sole triage decision-maker.

    Complexity band interpretation:

    * ``"low"`` — regular / periodic structure; simple models likely sufficient.
    * ``"medium"`` — moderate complexity; linear models with some structure.
    * ``"high"`` — stochastic or chaotic-like dynamics; rich feature engineering
      or ensemble methods may be warranted.

    Attributes:
        permutation_entropy: Normalised PE in [0, 1].  Value near 0 means
            highly regular ordinal patterns; near 1 means maximum ordinal
            disorder.
        spectral_entropy: Normalised SE in [0, 1].  Value near 0 means
            spectrally concentrated (predictable); near 1 means flat spectrum.
        embedding_order: Embedding order *m* used for the PE computation.
        complexity_band: Derived complexity classification.
        interpretation: One-sentence human-readable explanation of the band.
        pe_reliability_warning: Warning when the series is too short for the
            chosen embedding order to give reliable estimates; ``None`` when
            no concern.
    """

    model_config = ConfigDict(frozen=True)

    permutation_entropy: float
    spectral_entropy: float
    embedding_order: int
    complexity_band: Literal["low", "medium", "high"]
    interpretation: str
    pe_reliability_warning: str | None
