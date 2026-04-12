"""Domain model for Largest Lyapunov Exponent result (F5)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LargestLyapunovExponentResult(BaseModel):
    """Estimated largest Lyapunov exponent (LLE) from delay embedding.

    Experimental — do NOT use as sole triage decision-maker.
    Reliable only for ``n >> 10**m`` and stationary, noise-free series.

    Attributes:
        lambda_estimate: Estimated LLE.  ``nan`` if estimation failed.
        embedding_dim: Embedding dimension *m* used for Takens reconstruction.
        delay: Time delay *tau* used in the embedding.
        evolution_steps: Number of divergence-tracking steps in Rosenstein algorithm.
        n_embedded_points: Number of delay vectors in the reconstructed attractor.
        interpretation: Human-readable characterisation of the lambda estimate.
        reliability_warning: Mandatory caution text; always populated.
        is_experimental: Always ``True``; signals that this result must not drive
            triage decisions in isolation.
    """

    model_config = ConfigDict(frozen=True)

    lambda_estimate: float
    embedding_dim: int
    delay: int
    evolution_steps: int
    n_embedded_points: int
    interpretation: str
    reliability_warning: str
    is_experimental: bool = True
