"""Composite extended forecastability fingerprint builder."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

from forecastability.services._extended_diagnostic_validation import (
    coerce_univariate_values,
    validate_optional_period,
    validate_positive_argument,
)
from forecastability.services.ami_information_geometry_service import (
    AmiInformationGeometryConfig,
    compute_ami_information_geometry,
)
from forecastability.services.classical_structure_service import compute_classical_structure
from forecastability.services.memory_structure_service import compute_memory_structure
from forecastability.services.ordinal_complexity_service import compute_ordinal_complexity
from forecastability.services.spectral_forecastability_service import (
    compute_spectral_forecastability,
)
from forecastability.triage.extended_forecastability import ExtendedForecastabilityFingerprint
from forecastability.utils.types import AmiInformationGeometry


def _validate_shared_inputs(
    values: ArrayLike,
    *,
    max_lag: int,
    period: int | None,
) -> np.ndarray:
    """Validate shared composite-builder arguments regardless of enabled blocks."""
    arr = coerce_univariate_values(values)
    validate_positive_argument(max_lag, name="max_lag")
    validate_optional_period(period)
    return arr


def _is_ami_geometry_feasible(
    values: np.ndarray,
    *,
    config: AmiInformationGeometryConfig,
) -> bool:
    """Return whether the AMI geometry block is locally feasible to evaluate."""
    return values.size >= config.min_n and float(np.std(values)) > 0.0


def _compute_optional_ami_geometry(
    values: np.ndarray,
    *,
    max_lag: int,
) -> AmiInformationGeometry | None:
    """Reuse the existing AMI geometry service when the input is feasible."""
    config = AmiInformationGeometryConfig(max_horizon=max_lag)
    if not _is_ami_geometry_feasible(values, config=config):
        return None
    return compute_ami_information_geometry(values, config=config)


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
    """Compose the extended forecastability fingerprint from enabled diagnostics.

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
        Composite fingerprint with disabled diagnostics preserved as ``None``.
    """
    arr = _validate_shared_inputs(values, max_lag=max_lag, period=period)
    ami_geometry = None
    if include_ami_geometry:
        ami_geometry = _compute_optional_ami_geometry(arr, max_lag=max_lag)

    spectral = compute_spectral_forecastability(arr) if include_spectral else None
    ordinal = compute_ordinal_complexity(arr) if include_ordinal else None
    classical = (
        compute_classical_structure(arr, period=period, max_lag=max_lag)
        if include_classical
        else None
    )
    memory = compute_memory_structure(arr) if include_memory else None

    return ExtendedForecastabilityFingerprint(
        information_geometry=ami_geometry,
        spectral=spectral,
        ordinal=ordinal,
        classical=classical,
        memory=memory,
    )
