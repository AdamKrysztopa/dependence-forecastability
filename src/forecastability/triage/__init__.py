"""Public API of the triage subsystem."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from forecastability.adapters.result_bundle_io import (
    load_result_bundle,
    save_result_bundle,
    save_triage_result_bundle,
)
from forecastability.services.forecast_prep_export import (
    forecast_prep_contract_to_lag_table,
    forecast_prep_contract_to_markdown,
)
from forecastability.triage.batch_models import (
    FAILURE_TABLE_COLUMNS,
    SUMMARY_TABLE_COLUMNS,
    BatchFailureRow,
    BatchSeriesRequest,
    BatchSummaryRow,
    BatchTriageExecution,
    BatchTriageExecutionItem,
    BatchTriageItemResult,
    BatchTriageRequest,
    BatchTriageResponse,
)
from forecastability.triage.complexity_band import ComplexityBandResult
from forecastability.triage.events import (
    TriageError,
    TriageEvent,
    TriageStageCompleted,
    TriageStageStarted,
)
from forecastability.triage.extended_forecastability import (
    ClassicalStructureResult,
    ExtendedForecastabilityAnalysisResult,
    ExtendedForecastabilityFingerprint,
    ExtendedForecastabilityProfile,
    MemoryStructureResult,
    OrdinalComplexityResult,
    SpectralForecastabilityResult,
)
from forecastability.triage.forecastability_profile import ForecastabilityProfile
from forecastability.triage.lag_aware_mod_mrmr import (
    BlockedLagAwareFeature,
    ForecastSafeLagCandidate,
    KnownFutureProvenance,
    LagAwareModMRMRConfig,
    LagAwareModMRMRResult,
    LagLegalityLabel,
    NormalizationStrategy,
    PairwiseScorerSpec,
    RejectedLagAwareFeature,
    RejectionReason,
    ScorerDiagnostics,
    SelectedLagAwareFeature,
    SignificanceMethod,
)
from forecastability.triage.lyapunov import LargestLyapunovExponentResult
from forecastability.triage.models import (
    AnalysisGoal,
    MethodPlan,
    ReadinessReport,
    ReadinessStatus,
    ReadinessWarning,
    TriageRequest,
    TriageResult,
)
from forecastability.triage.predictive_info_learning_curve import PredictiveInfoLearningCurve
from forecastability.triage.readiness import assess_readiness
from forecastability.triage.result_bundle import (
    TriageBundleProvenance,
    TriageBundleWarning,
    TriageConfigSnapshot,
    TriageInputMetadata,
    TriageNumericOutputs,
    TriageResultBundle,
    TriageVersions,
    build_triage_result_bundle,
)
from forecastability.triage.router import plan_method
from forecastability.triage.spectral_predictability import SpectralPredictabilityResult
from forecastability.triage.theoretical_limit_diagnostics import TheoreticalLimitDiagnostics
from forecastability.use_cases.build_forecast_prep_contract import build_forecast_prep_contract
from forecastability.use_cases.run_batch_triage import (
    rank_batch_items,
    run_batch_triage,
    run_batch_triage_with_details,
)
from forecastability.use_cases.run_triage import run_triage
from forecastability.utils.types import (
    CovariateRecommendation,
    FamilyRecommendation,
    ForecastPrepBundle,
    ForecastPrepConfidence,
    ForecastPrepContract,
    ForecastPrepContractConfidence,
    ForecastPrepCovariateRole,
    ForecastPrepFamilyTier,
    ForecastPrepLagRole,
    LagRecommendation,
)

_LAZY_EXPORT_MAP: dict[str, tuple[str, str | None]] = {
    "run_extended_forecastability_analysis": (
        "forecastability.use_cases",
        "_run_extended_forecastability_analysis_public",
    ),
    "run_lag_aware_mod_mrmr": (
        "forecastability.use_cases.lag_aware_mod_mrmr",
        None,
    ),
}


def __getattr__(name: str) -> Any:
    """Resolve heavier triage exports on first attribute access."""
    target = _LAZY_EXPORT_MAP.get(name)
    if target is None:
        raise AttributeError(f"module 'forecastability.triage' has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name)
    value: Any = getattr(module, attr_name or name)
    globals()[name] = value
    return value


__all__ = [
    "AnalysisGoal",
    "BatchSeriesRequest",
    "BatchTriageRequest",
    "BatchTriageItemResult",
    "BatchSummaryRow",
    "BatchFailureRow",
    "BatchTriageResponse",
    "BatchTriageExecutionItem",
    "BatchTriageExecution",
    "SUMMARY_TABLE_COLUMNS",
    "FAILURE_TABLE_COLUMNS",
    "ReadinessStatus",
    "ReadinessWarning",
    "ReadinessReport",
    "MethodPlan",
    "TriageRequest",
    "TriageResult",
    "TriageBundleWarning",
    "TriageInputMetadata",
    "TriageConfigSnapshot",
    "TriageVersions",
    "TriageNumericOutputs",
    "TriageBundleProvenance",
    "TriageResultBundle",
    "TriageStageStarted",
    "TriageStageCompleted",
    "TriageError",
    "TriageEvent",
    "ForecastPrepBundle",
    "ForecastPrepConfidence",
    "ForecastPrepContract",
    "ForecastPrepContractConfidence",
    "ForecastPrepCovariateRole",
    "ForecastPrepFamilyTier",
    "ForecastPrepLagRole",
    "LagRecommendation",
    "CovariateRecommendation",
    "FamilyRecommendation",
    "ClassicalStructureResult",
    "ExtendedForecastabilityAnalysisResult",
    "ExtendedForecastabilityFingerprint",
    "ExtendedForecastabilityProfile",
    "ForecastabilityProfile",
    "ComplexityBandResult",
    "LargestLyapunovExponentResult",
    "MemoryStructureResult",
    "OrdinalComplexityResult",
    "PredictiveInfoLearningCurve",
    "SpectralForecastabilityResult",
    "SpectralPredictabilityResult",
    "TheoreticalLimitDiagnostics",
    # Lag-Aware ModMRMR domain contracts (v0.4.3)
    "BlockedLagAwareFeature",
    "ForecastSafeLagCandidate",
    "KnownFutureProvenance",
    "LagAwareModMRMRConfig",
    "LagAwareModMRMRResult",
    "LagLegalityLabel",
    "NormalizationStrategy",
    "PairwiseScorerSpec",
    "RejectedLagAwareFeature",
    "RejectionReason",
    "ScorerDiagnostics",
    "SelectedLagAwareFeature",
    "SignificanceMethod",
    "assess_readiness",
    "plan_method",
    "build_forecast_prep_contract",
    "forecast_prep_contract_to_lag_table",
    "forecast_prep_contract_to_markdown",
    "rank_batch_items",
    "run_batch_triage",
    "run_batch_triage_with_details",
    "run_extended_forecastability_analysis",
    "run_lag_aware_mod_mrmr",
    "run_triage",
    "build_triage_result_bundle",
    "save_result_bundle",
    "load_result_bundle",
    "save_triage_result_bundle",
]
