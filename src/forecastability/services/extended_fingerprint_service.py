"""Phase 0 scaffold for the extended forecastability fingerprint composer."""

from __future__ import annotations

from numpy.typing import ArrayLike

from forecastability.triage.extended_forecastability import ExtendedForecastabilityFingerprint

_PHASE_0_SCAFFOLD_MESSAGE = (
    "Phase 0 scaffold only: build_extended_forecastability_fingerprint() is not implemented yet."
)


def build_extended_forecastability_fingerprint(
    values: ArrayLike,
    *,
    max_lag: int = 40,
    period: int | None = None,
    include_ami_geometry: bool = True,
    include_spectral: bool = True,
    include_ordinal: bool = True,
    include_classical: bool = True,
    include_memory: bool = True,
) -> ExtendedForecastabilityFingerprint:
    """Return the Phase 0 extended fingerprint scaffold.

    Args:
        values: Univariate series values to analyze.
        max_lag: Maximum lag used by lag-aware diagnostics.
        period: Optional seasonal period for period-aware diagnostics.
        include_ami_geometry: Whether to include the existing AMI geometry block.
        include_spectral: Whether to include the spectral diagnostics block.
        include_ordinal: Whether to include the ordinal diagnostics block.
        include_classical: Whether to include the classical diagnostics block.
        include_memory: Whether to include the memory diagnostics block.

    Returns:
        The future composite extended fingerprint contract.

    Raises:
        NotImplementedError: Always raised in Phase 0 scaffolding.
    """
    del (
        values,
        max_lag,
        period,
        include_ami_geometry,
        include_spectral,
        include_ordinal,
        include_classical,
        include_memory,
    )
    raise NotImplementedError(_PHASE_0_SCAFFOLD_MESSAGE)
