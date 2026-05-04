"""Phase 0 scaffold for the extended spectral forecastability diagnostic."""

from __future__ import annotations

from typing import Literal

from numpy.typing import ArrayLike

from forecastability.triage.extended_forecastability import SpectralForecastabilityResult

_PHASE_0_SCAFFOLD_MESSAGE = (
    "Phase 0 scaffold only: compute_spectral_forecastability() is not implemented yet."
)


def compute_spectral_forecastability(
    values: ArrayLike,
    *,
    max_periods: int = 5,
    detrend: Literal["none", "linear"] = "linear",
    eps: float = 1e-12,
) -> SpectralForecastabilityResult:
    """Return the Phase 0 spectral forecastability scaffold.

    Args:
        values: Univariate series values to analyze.
        max_periods: Maximum number of dominant periods to report.
        detrend: Deterministic detrending mode for the spectral path.
        eps: Small numerical floor for safe normalization.

    Returns:
        The future spectral forecastability result contract.

    Raises:
        NotImplementedError: Always raised in Phase 0 scaffolding.
    """
    del values, max_periods, detrend, eps
    raise NotImplementedError(_PHASE_0_SCAFFOLD_MESSAGE)
