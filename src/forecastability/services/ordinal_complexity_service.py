"""Phase 0 scaffold for the extended ordinal complexity diagnostic."""

from __future__ import annotations

from numpy.typing import ArrayLike

from forecastability.triage.extended_forecastability import OrdinalComplexityResult

_PHASE_0_SCAFFOLD_MESSAGE = (
    "Phase 0 scaffold only: compute_ordinal_complexity() is not implemented yet."
)


def compute_ordinal_complexity(
    values: ArrayLike,
    *,
    embedding_dimension: int = 3,
    delay: int = 1,
    include_weighted: bool = True,
    eps: float = 1e-12,
) -> OrdinalComplexityResult:
    """Return the Phase 0 ordinal complexity scaffold.

    Args:
        values: Univariate series values to analyze.
        embedding_dimension: Ordinal embedding dimension.
        delay: Delay between successive embedding coordinates.
        include_weighted: Whether the weighted entropy variant should be computed.
        eps: Small numerical floor for safe normalization.

    Returns:
        The future ordinal complexity result contract.

    Raises:
        NotImplementedError: Always raised in Phase 0 scaffolding.
    """
    del values, embedding_dimension, delay, include_weighted, eps
    raise NotImplementedError(_PHASE_0_SCAFFOLD_MESSAGE)
