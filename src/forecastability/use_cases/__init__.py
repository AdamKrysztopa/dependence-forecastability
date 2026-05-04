"""Use-case modules for pipeline orchestration."""

from __future__ import annotations

from numpy.typing import ArrayLike

from forecastability.services.extended_forecastability_profile_service import (
    ExtendedForecastabilityRoutingConfig,
)
from forecastability.services.routing_policy_service import RoutingPolicyConfig
from forecastability.triage.extended_forecastability import (
    ExtendedForecastabilityAnalysisResult,
)
from forecastability.use_cases.build_forecast_prep_contract import build_forecast_prep_contract
from forecastability.use_cases.run_batch_forecastability_workbench import (
    run_batch_forecastability_workbench,
)
from forecastability.use_cases.run_batch_triage import (
    rank_batch_items,
    run_batch_triage,
    run_batch_triage_with_details,
)
from forecastability.use_cases.run_covariant_analysis import run_covariant_analysis
from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.use_cases.run_lagged_exogenous_triage import (
    run_lagged_exogenous_triage,
)
from forecastability.use_cases.run_routing_validation import run_routing_validation
from forecastability.use_cases.run_triage import run_triage


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
    """Resolve the extended analysis use case lazily while preserving the stable API."""
    from forecastability.use_cases.run_extended_forecastability_analysis import (
        run_extended_forecastability_analysis as _run_extended_forecastability_analysis,
    )

    globals()["run_extended_forecastability_analysis"] = (
        _run_extended_forecastability_analysis_public
    )

    return _run_extended_forecastability_analysis(
        series,
        name=name,
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
        random_state=random_state,
        routing_config=routing_config,
    )


_run_extended_forecastability_analysis_public = run_extended_forecastability_analysis


__all__ = [
    "build_forecast_prep_contract",
    "run_triage",
    "run_batch_triage",
    "run_batch_triage_with_details",
    "run_batch_forecastability_workbench",
    "rank_batch_items",
    "run_covariant_analysis",
    "run_lagged_exogenous_triage",
    "run_forecastability_fingerprint",
    "run_extended_forecastability_analysis",
    "run_routing_validation",
    "RoutingPolicyConfig",
]
