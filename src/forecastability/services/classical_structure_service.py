"""Phase 0 scaffold for the extended classical-structure diagnostic."""

from __future__ import annotations

from numpy.typing import ArrayLike

from forecastability.triage.extended_forecastability import ClassicalStructureResult

_PHASE_0_SCAFFOLD_MESSAGE = (
    "Phase 0 scaffold only: compute_classical_structure() is not implemented yet."
)


def compute_classical_structure(
    values: ArrayLike,
    *,
    period: int | None = None,
    max_lag: int = 40,
) -> ClassicalStructureResult:
    """Return the Phase 0 classical-structure scaffold.

    Args:
        values: Univariate series values to analyze.
        period: Optional seasonal period for period-aware summaries.
        max_lag: Maximum lag used by deterministic autocorrelation summaries.

    Returns:
        The future classical structure result contract.

    Raises:
        NotImplementedError: Always raised in Phase 0 scaffolding.
    """
    del values, period, max_lag
    raise NotImplementedError(_PHASE_0_SCAFFOLD_MESSAGE)
