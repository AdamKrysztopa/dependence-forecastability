"""Phase 0 scaffold for the extended memory-structure diagnostic."""

from __future__ import annotations

from numpy.typing import ArrayLike

from forecastability.triage.extended_forecastability import MemoryStructureResult

_PHASE_0_SCAFFOLD_MESSAGE = (
    "Phase 0 scaffold only: compute_memory_structure() is not implemented yet."
)


def compute_memory_structure(
    values: ArrayLike,
    *,
    min_scale: int | None = None,
    max_scale: int | None = None,
    n_scales: int = 12,
) -> MemoryStructureResult:
    """Return the Phase 0 memory-structure scaffold.

    Args:
        values: Univariate series values to analyze.
        min_scale: Optional lower DFA scale bound.
        max_scale: Optional upper DFA scale bound.
        n_scales: Number of scales that will eventually be evaluated.

    Returns:
        The future memory structure result contract.

    Raises:
        NotImplementedError: Always raised in Phase 0 scaffolding.
    """
    del values, min_scale, max_scale, n_scales
    raise NotImplementedError(_PHASE_0_SCAFFOLD_MESSAGE)
