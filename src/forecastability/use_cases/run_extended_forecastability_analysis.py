"""Public use case for the AMI-first extended forecastability workflow."""

from __future__ import annotations

from numpy.typing import ArrayLike

from forecastability.services._extended_diagnostic_validation import (
    coerce_univariate_values,
    validate_embedding_dimension,
    validate_memory_scale_bounds,
    validate_optional_period,
    validate_positive_argument,
)
from forecastability.services.extended_fingerprint_service import (
    build_extended_forecastability_fingerprint,
)
from forecastability.services.extended_forecastability_profile_service import (
    ExtendedForecastabilityRoutingConfig,
    build_extended_forecastability_profile,
)
from forecastability.triage.extended_forecastability import (
    ExtendedForecastabilityAnalysisResult,
)


def _validate_extended_analysis_inputs(
    series: ArrayLike,
    *,
    max_lag: int,
    period: int | None,
    ordinal_embedding_dimension: int,
    ordinal_delay: int,
    memory_min_scale: int | None,
    memory_max_scale: int | None,
) -> int:
    """Validate the public Phase 2 use-case seam and return input size."""
    values = coerce_univariate_values(series)
    validate_positive_argument(max_lag, name="max_lag")
    validate_optional_period(period)
    validate_embedding_dimension(ordinal_embedding_dimension)
    validate_positive_argument(ordinal_delay, name="ordinal_delay")
    validate_memory_scale_bounds(memory_min_scale, memory_max_scale)
    return int(values.size)


def run_extended_forecastability_analysis(
    series: ArrayLike,
    *,
    name: str | None = None,
    max_lag: int = 40,
    period: int | None = None,
    include_ami_geometry: bool = True,
    include_spectral: bool = True,
    include_ordinal: bool = True,
    include_classical: bool = True,
    include_memory: bool = True,
    ordinal_embedding_dimension: int = 3,
    ordinal_delay: int = 1,
    memory_min_scale: int | None = None,
    memory_max_scale: int | None = None,
    random_state: int | None = None,
    routing_config: ExtendedForecastabilityRoutingConfig | None = None,
) -> ExtendedForecastabilityAnalysisResult:
    """Run the AMI-first extended forecastability analysis workflow.

    Args:
        series: Univariate series values to analyze.
        name: Optional stable identifier for the analyzed series.
        max_lag: Maximum lag horizon requested for lag-aware diagnostics.
        period: Optional seasonal period used by classical structure diagnostics.
        include_ami_geometry: Whether to include the AMI geometry block.
        include_spectral: Whether to include the spectral diagnostics block.
        include_ordinal: Whether to include the ordinal diagnostics block.
        include_classical: Whether to include the classical diagnostics block.
        include_memory: Whether to include the memory diagnostics block.
        ordinal_embedding_dimension: Embedding dimension used by ordinal diagnostics.
        ordinal_delay: Delay used by ordinal diagnostics.
        memory_min_scale: Optional lower DFA scale bound.
        memory_max_scale: Optional upper DFA scale bound.
        random_state: Reserved for forward-compatible deterministic signatures.
        routing_config: Optional deterministic routing-threshold configuration.

    Returns:
        Additive extended forecastability analysis result with fingerprint,
        routing profile, and JSON-safe routing metadata.

    Raises:
        ValueError: If any public validation rule fails.
    """
    n_observations = _validate_extended_analysis_inputs(
        series,
        max_lag=max_lag,
        period=period,
        ordinal_embedding_dimension=ordinal_embedding_dimension,
        ordinal_delay=ordinal_delay,
        memory_min_scale=memory_min_scale,
        memory_max_scale=memory_max_scale,
    )
    fingerprint = build_extended_forecastability_fingerprint(
        series,
        max_lag=max_lag,
        period=period,
        include_ami_geometry=include_ami_geometry,
        include_spectral=include_spectral,
        include_ordinal=include_ordinal,
        include_classical=include_classical,
        include_memory=include_memory,
        ordinal_embedding_dimension=ordinal_embedding_dimension,
        ordinal_delay=ordinal_delay,
        memory_min_scale=memory_min_scale,
        memory_max_scale=memory_max_scale,
    )
    routing_decision = build_extended_forecastability_profile(
        fingerprint,
        config=routing_config,
        ami_geometry_requested=include_ami_geometry,
    )

    routing_metadata = {
        **routing_decision.metadata,
        "include_ami_geometry": include_ami_geometry,
        "include_spectral": include_spectral,
        "include_ordinal": include_ordinal,
        "include_classical": include_classical,
        "include_memory": include_memory,
        "ordinal_embedding_dimension": ordinal_embedding_dimension,
        "ordinal_delay": ordinal_delay,
    }
    if period is not None:
        routing_metadata["period_supplied"] = True
    if memory_min_scale is not None:
        routing_metadata["memory_min_scale"] = memory_min_scale
    if memory_max_scale is not None:
        routing_metadata["memory_max_scale"] = memory_max_scale
    if random_state is not None:
        routing_metadata["random_state_contract"] = "ignored_by_deterministic_phase2"

    return ExtendedForecastabilityAnalysisResult(
        series_name=name,
        n_observations=n_observations,
        max_lag=max_lag,
        period=period,
        fingerprint=fingerprint,
        profile=routing_decision.profile,
        routing_metadata=routing_metadata,
    )


__all__ = ["run_extended_forecastability_analysis"]
