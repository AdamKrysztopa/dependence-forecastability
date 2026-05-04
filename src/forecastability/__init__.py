"""Forecastability package implementing AMI and pAMI analysis."""

from __future__ import annotations

from importlib import import_module
from typing import Any

# ---------------------------------------------------------------------------
# Canonical eager imports — public facade, core use cases, and primary types.
# These are always loaded when the package is imported and form the minimum
# surface required for forecastability triage workflows.
# ---------------------------------------------------------------------------
from forecastability.triage.models import (
    TriageRequest,
    TriageResult,
)
from forecastability.use_cases import (
    build_forecast_prep_contract,
    run_covariant_analysis,
    run_lagged_exogenous_triage,
    run_triage,
)
from forecastability.utils.datasets import (
    generate_ar1,
    generate_white_noise,
)
from forecastability.utils.types import (
    CausalGraphResult,
    CovariantAnalysisBundle,
    CovariantSummaryRow,
    ForecastPrepContract,
    GcmiResult,
    InterpretationResult,
    LaggedExogBundle,
    LaggedExogProfileRow,
    LaggedExogSelectionRow,
    LagRecommendation,
    LagRoleLabel,
    LagSelectorLabel,
    LagSignificanceSource,
    MetricCurve,
    TransferEntropyResult,
)
from forecastability.utils.validation import validate_time_series

__version__ = "0.4.1"

# ---------------------------------------------------------------------------
# Lazy export map — loaded on first attribute access via __getattr__.
# Symbols are still in __all__ and importable; they are simply not loaded
# until first use.  This keeps the package import fast and avoids eager
# loading of matplotlib-heavy reporting modules, archetype generators,
# advanced pipeline classes, and config helpers.
# ---------------------------------------------------------------------------

# PBE-F18: CSV geometry batch adapter (matplotlib-heavy)
_LAZY_EXPORT_MAP: dict[str, tuple[str, str | None]] = {
    # CSV geometry batch adapter
    "CsvGeometryBatchItem": ("forecastability.adapters.csv", None),
    "CsvGeometryBatchResult": ("forecastability.adapters.csv", None),
    "run_ami_geometry_csv_batch": ("forecastability.adapters.csv", None),
    # Diagnostics
    "compute_gcmi": ("forecastability.diagnostics.gcmi", None),
    # Extensions
    "TargetBaselineCurves": ("forecastability.extensions", None),
    "compute_target_baseline_by_horizon": ("forecastability.extensions", None),
    # Scorers (advanced)
    "DependenceScorer": ("forecastability.metrics.scorers", None),
    "ScorerInfo": ("forecastability.metrics.scorers", None),
    "ScorerRegistry": ("forecastability.metrics.scorers", None),
    "default_registry": ("forecastability.metrics.scorers", None),
    "gcmi_scorer": ("forecastability.metrics.scorers", None),
    # Pipeline (advanced / internal)
    "AnalyzeResult": ("forecastability.pipeline.analyzer", None),
    "ForecastabilityAnalyzer": ("forecastability.pipeline.analyzer", None),
    "ForecastabilityAnalyzerExog": ("forecastability.pipeline.analyzer", None),
    # Fingerprint reporting (matplotlib-heavy)
    "build_fingerprint_markdown": ("forecastability.reporting.fingerprint_reporting", None),
    "build_fingerprint_panel_markdown": ("forecastability.reporting.fingerprint_reporting", None),
    "build_fingerprint_summary_dict": ("forecastability.reporting.fingerprint_reporting", None),
    "build_fingerprint_summary_row": ("forecastability.reporting.fingerprint_reporting", None),
    "render_fingerprint_summary_dict": ("forecastability.reporting.fingerprint_reporting", None),
    "save_fingerprint_bundle_json": ("forecastability.reporting.fingerprint_reporting", None),
    # Workbench reporting
    "build_batch_forecastability_executive_markdown": (
        "forecastability.reporting.forecastability_workbench_reporting",
        None,
    ),
    "build_batch_forecastability_markdown": (
        "forecastability.reporting.forecastability_workbench_reporting",
        None,
    ),
    # Forecast prep export helpers
    "forecast_prep_contract_to_lag_table": ("forecastability.services.forecast_prep_export", None),
    "forecast_prep_contract_to_markdown": ("forecastability.services.forecast_prep_export", None),
    # Triage sub-models (not commonly needed by API users)
    "ForecastabilityProfile": ("forecastability.triage.forecastability_profile", None),
    "PredictiveInfoLearningCurve": (
        "forecastability.triage.predictive_info_learning_curve",
        None,
    ),
    "SpectralPredictabilityResult": ("forecastability.triage.spectral_predictability", None),
    # Non-core use cases
    "run_batch_forecastability_workbench": ("forecastability.use_cases", None),
    "run_batch_triage": ("forecastability.use_cases", None),
    "run_routing_validation": ("forecastability.use_cases", None),
    "run_forecastability_fingerprint": (
        "forecastability.use_cases.run_forecastability_fingerprint",
        None,
    ),
    # Batch workbench models
    "BatchForecastabilityWorkbenchItem": (
        "forecastability.use_cases.batch_forecastability_workbench_models",
        None,
    ),
    "BatchForecastabilityWorkbenchResult": (
        "forecastability.use_cases.batch_forecastability_workbench_models",
        None,
    ),
    "BatchForecastabilityWorkbenchSummary": (
        "forecastability.use_cases.batch_forecastability_workbench_models",
        None,
    ),
    "ForecastingNextStepPlan": (
        "forecastability.use_cases.batch_forecastability_workbench_models",
        None,
    ),
    # Config classes (not needed at import time)
    "BenchmarkDataConfig": ("forecastability.utils.config", None),
    "CMIConfig": ("forecastability.utils.config", None),
    "ExogenousBenchmarkConfig": ("forecastability.utils.config", None),
    "MetricConfig": ("forecastability.utils.config", None),
    "ModelConfig": ("forecastability.utils.config", None),
    "OutputConfig": ("forecastability.utils.config", None),
    "RobustnessStudyConfig": ("forecastability.utils.config", None),
    "RollingOriginConfig": ("forecastability.utils.config", None),
    "SensitivityConfig": ("forecastability.utils.config", None),
    "UncertaintyConfig": ("forecastability.utils.config", None),
    # Datasets (less common)
    "ar1_theoretical_ami": ("forecastability.utils.datasets", None),
    # Synthetic archetype generators (rarely needed at package-import time)
    "ExpectedFamilyMetadata": ("forecastability.utils.synthetic", None),
    "generate_ar1_archetype": ("forecastability.utils.synthetic", None),
    "generate_ar1_monotonic": ("forecastability.utils.synthetic", None),
    "generate_contemporaneous_only_pair": ("forecastability.utils.synthetic", None),
    "generate_covariant_benchmark": ("forecastability.utils.synthetic", None),
    "generate_directional_pair": ("forecastability.utils.synthetic", None),
    "generate_exogenous_driven_archetype": ("forecastability.utils.synthetic", None),
    "generate_fingerprint_archetypes": ("forecastability.utils.synthetic", None),
    "generate_known_future_calendar_pair": ("forecastability.utils.synthetic", None),
    "generate_lagged_exog_panel": ("forecastability.utils.synthetic", None),
    "generate_long_memory_archetype": ("forecastability.utils.synthetic", None),
    "generate_low_directness_high_penalty_archetype": ("forecastability.utils.synthetic", None),
    "generate_mediated_directness_drop": ("forecastability.utils.synthetic", None),
    "generate_mediated_low_directness_archetype": ("forecastability.utils.synthetic", None),
    "generate_nonlinear_mixed": ("forecastability.utils.synthetic", None),
    "generate_nonlinear_mixed_archetype": ("forecastability.utils.synthetic", None),
    "generate_routing_validation_archetypes": ("forecastability.utils.synthetic", None),
    "generate_seasonal_archetype": ("forecastability.utils.synthetic", None),
    "generate_seasonal_periodic": ("forecastability.utils.synthetic", None),
    "generate_structural_break_archetype": ("forecastability.utils.synthetic", None),
    "generate_weak_seasonal_near_threshold_archetype": ("forecastability.utils.synthetic", None),
    "generate_white_noise_archetype": ("forecastability.utils.synthetic", None),
    # Less-common result types from utils.types
    "AmiGeometryCurvePoint": ("forecastability.utils.types", None),
    "AmiInformationGeometry": ("forecastability.utils.types", None),
    "BackendComparisonResult": ("forecastability.utils.types", None),
    "CanonicalExampleResult": ("forecastability.utils.types", None),
    "CanonicalSummary": ("forecastability.utils.types", None),
    "CovariateRecommendation": ("forecastability.utils.types", None),
    "Diagnostics": ("forecastability.utils.types", None),
    "ExogenousBenchmarkResult": ("forecastability.utils.types", None),
    "FamilyRecommendation": ("forecastability.utils.types", None),
    "FingerprintBundle": ("forecastability.utils.types", None),
    "ForecastabilityFingerprint": ("forecastability.utils.types", None),
    "ForecastPrepConfidence": ("forecastability.utils.types", None),
    "ForecastPrepContractConfidence": ("forecastability.utils.types", None),
    "ForecastPrepCovariateRole": ("forecastability.utils.types", None),
    "ForecastPrepFamilyTier": ("forecastability.utils.types", None),
    "ForecastPrepLagRole": ("forecastability.utils.types", None),
    "ForecastResult": ("forecastability.utils.types", None),
    "PcmciAmiResult": ("forecastability.utils.types", None),
    "Phase0MiScore": ("forecastability.utils.types", None),
    "RobustnessStudyResult": ("forecastability.utils.types", None),
    "RoutingPolicyAudit": ("forecastability.utils.types", None),
    "RoutingPolicyAuditConfig": ("forecastability.utils.types", None),
    "RoutingRecommendation": ("forecastability.utils.types", None),
    "RoutingValidationBundle": ("forecastability.utils.types", None),
    "RoutingValidationCase": ("forecastability.utils.types", None),
    "RoutingValidationOutcome": ("forecastability.utils.types", None),
    "RoutingValidationSourceKind": ("forecastability.utils.types", None),
    "SampleSizeStressResult": ("forecastability.utils.types", None),
    "SeriesEvaluationResult": ("forecastability.utils.types", None),
    "TensorRoleLabel": ("forecastability.utils.types", None),
}

_NOTEBOOK_COMPAT_EXPORTS: dict[str, tuple[str, str | None]] = {
    "build_canonical_markdown": ("forecastability.reporting", None),
    "build_case_summary": ("forecastability.exog_benchmark", None),
    "build_complexity_band": ("forecastability.services.complexity_band_service", None),
    "build_expanding_window_splits": ("forecastability.pipeline.rolling_origin", None),
    "build_fingerprint_showcase_record": ("forecastability.reporting.fingerprint_showcase", None),
    "build_plain_language_math_summary": ("forecastability.reporting.fingerprint_showcase", None),
    "build_report_markdown": ("forecastability.exog_benchmark", None),
    "build_theoretical_limit_diagnostics": (
        "forecastability.services.theoretical_limit_diagnostics_service",
        None,
    ),
    "build_largest_lyapunov_exponent": ("forecastability.services.lyapunov_service", None),
    "build_predictive_info_learning_curve": (
        "forecastability.services.predictive_info_learning_curve_service",
        None,
    ),
    "build_spectral_predictability": (
        "forecastability.services.spectral_predictability_service",
        None,
    ),
    "causal_parent_frame": ("forecastability.reporting.covariant_walkthrough", None),
    "CollectingEventEmitter": ("forecastability.adapters.event_emitter", None),
    "compute_linear_information_curve": (
        "forecastability.services.linear_information_service",
        None,
    ),
    "conditioning_scope_frame": ("forecastability.reporting.covariant_walkthrough", None),
    "create_screening_agent": ("forecastability.adapters.llm.screening_agent", None),
    "create_triage_agent": ("forecastability.adapters.pydantic_ai_agent", None),
    "driver_role_frame": ("forecastability.reporting.covariant_walkthrough", None),
    "exog_benchmark": ("forecastability.exog_benchmark", ""),
    "F1ProfilePayload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "F5LyapunovPayload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "F7BatchRankPayload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "FeatureScreeningReport": ("forecastability.adapters.llm.screening_agent", None),
    "f1_profile_payload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "f2_limits_payload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "f6_complexity_payload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "f7_batch_rank_payload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "fingerprint_profile_frame": ("forecastability.reporting.fingerprint_showcase", None),
    "forecast_linear_autoreg": ("forecastability.models", None),
    "forecast_naive": ("forecastability.models", None),
    "generate_henon_map": ("forecastability.utils.datasets", None),
    "generate_simulated_stock_returns": ("forecastability.utils.datasets", None),
    "generate_sine_wave": ("forecastability.utils.datasets", None),
    "InfraSettings": ("forecastability.adapters.settings", None),
    "interpret_canonical_result": ("forecastability.reporting.interpretation", None),
    "interpret_covariant_bundle": (
        "forecastability.services.covariant_interpretation_service",
        None,
    ),
    "interpret_payload": (
        "forecastability.adapters.agents.triage_agent_interpretation_adapter",
        None,
    ),
    "load_air_passengers": ("forecastability.utils.datasets", None),
    "load_benchmark_slice": ("forecastability.exog_benchmark", None),
    "PcmciAmiAdapter": ("forecastability.adapters.pcmci_ami_adapter", None),
    "plot_exog_benchmark_curves": ("forecastability.utils.plots", None),
    "present_triage_result": ("forecastability.adapters.triage_presenter", None),
    "pydantic_ai_available": ("forecastability.adapters.llm.screening_agent", None),
    "routing_table_frame": ("forecastability.reporting.fingerprint_showcase", None),
    "run_canonical_example": ("forecastability.pipeline", None),
    "run_backend_comparison": ("forecastability.utils.robustness", None),
    "run_exogenous_rolling_origin_evaluation": ("forecastability.pipeline", None),
    "run_sample_size_stress": ("forecastability.utils.robustness", None),
    "save_canonical_result_json": ("forecastability.reporting", None),
    "save_causal_parent_heatmap": ("forecastability.reporting.covariant_walkthrough", None),
    "save_directionality_plot": ("forecastability.reporting.covariant_walkthrough", None),
    "save_metric_heatmap": ("forecastability.reporting.covariant_walkthrough", None),
    "save_metric_overview": ("forecastability.reporting.fingerprint_showcase", None),
    "save_phase0_overview": ("forecastability.reporting.covariant_walkthrough", None),
    "save_showcase_profile_grid": ("forecastability.reporting.fingerprint_showcase", None),
    "ScreeningDeps": ("forecastability.adapters.llm.screening_agent", None),
    "SerialisedTriageSummary": ("forecastability.adapters.agents.triage_summary_serializer", None),
    "serialise_batch": ("forecastability.adapters.agents.triage_summary_serializer", None),
    "serialise_batch_to_json": ("forecastability.adapters.agents.triage_summary_serializer", None),
    "serialise_payload": ("forecastability.adapters.agents.triage_summary_serializer", None),
    "serialise_to_json": ("forecastability.adapters.agents.triage_summary_serializer", None),
    "showcase_summary_frame": ("forecastability.reporting.fingerprint_showcase", None),
    "smape": ("forecastability.models", None),
    "summarize_canonical_result": ("forecastability.utils.aggregation", None),
    "summary_table_frame": ("forecastability.reporting.covariant_walkthrough", None),
    "synthetic_benchmark_role_frame": ("forecastability.reporting.covariant_walkthrough", None),
    "TriageAgentInterpretation": (
        "forecastability.adapters.agents.triage_agent_interpretation_adapter",
        None,
    ),
    "TriageAgentPayload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "triage_agent_payload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "TriageDeps": ("forecastability.adapters.pydantic_ai_agent", None),
    "verify_showcase_records": ("forecastability.reporting.fingerprint_showcase", None),
    "write_frame_csv": ("forecastability.reporting.covariant_walkthrough", None),
}


def __getattr__(name: str) -> Any:
    """Resolve lazily-loaded symbols on first attribute access.

    Handles both PBE-F18 heavy-import symbols (_LAZY_EXPORT_MAP) and
    migrated notebook compatibility exports (_NOTEBOOK_COMPAT_EXPORTS).
    """
    target = _LAZY_EXPORT_MAP.get(name) or _NOTEBOOK_COMPAT_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module 'forecastability' has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name)
    if attr_name == "":
        value: Any = module
    else:
        value = getattr(module, attr_name or name)
    globals()[name] = value
    return value


__all__ = [
    "AmiGeometryCurvePoint",
    "AmiInformationGeometry",
    "AnalyzeResult",
    "ar1_theoretical_ami",
    "BackendComparisonResult",
    "BatchForecastabilityWorkbenchItem",
    "BatchForecastabilityWorkbenchResult",
    "BatchForecastabilityWorkbenchSummary",
    "CanonicalExampleResult",
    "CanonicalSummary",
    "CausalGraphResult",
    "CMIConfig",
    "CovariateRecommendation",
    "CovariantAnalysisBundle",
    "CovariantSummaryRow",
    "Diagnostics",
    "build_batch_forecastability_executive_markdown",
    "build_batch_forecastability_markdown",
    "build_forecast_prep_contract",
    "build_fingerprint_markdown",
    "build_fingerprint_panel_markdown",
    "build_fingerprint_summary_dict",
    "build_fingerprint_summary_row",
    "CsvGeometryBatchItem",
    "CsvGeometryBatchResult",
    "DependenceScorer",
    "ExpectedFamilyMetadata",
    "ExogenousBenchmarkConfig",
    "ExogenousBenchmarkResult",
    "FamilyRecommendation",
    "FingerprintBundle",
    "ForecastPrepConfidence",
    "ForecastPrepContract",
    "ForecastPrepContractConfidence",
    "ForecastPrepCovariateRole",
    "ForecastPrepFamilyTier",
    "ForecastPrepLagRole",
    "ForecastabilityAnalyzer",
    "ForecastabilityAnalyzerExog",
    "ForecastabilityFingerprint",
    "ForecastingNextStepPlan",
    "ForecastabilityProfile",
    "ForecastResult",
    "GcmiResult",
    "gcmi_scorer",
    "compute_gcmi",
    "compute_target_baseline_by_horizon",
    "generate_ar1",
    "generate_ar1_archetype",
    "generate_ar1_monotonic",
    "generate_contemporaneous_only_pair",
    "generate_covariant_benchmark",
    "generate_directional_pair",
    "generate_exogenous_driven_archetype",
    "generate_fingerprint_archetypes",
    "generate_known_future_calendar_pair",
    "generate_lagged_exog_panel",
    "generate_long_memory_archetype",
    "generate_low_directness_high_penalty_archetype",
    "generate_mediated_directness_drop",
    "generate_mediated_low_directness_archetype",
    "generate_nonlinear_mixed",
    "generate_nonlinear_mixed_archetype",
    "generate_routing_validation_archetypes",
    "generate_seasonal_archetype",
    "generate_seasonal_periodic",
    "generate_structural_break_archetype",
    "generate_weak_seasonal_near_threshold_archetype",
    "generate_white_noise",
    "generate_white_noise_archetype",
    "BenchmarkDataConfig",
    "InterpretationResult",
    "LagRecommendation",
    "LaggedExogBundle",
    "LaggedExogProfileRow",
    "LaggedExogSelectionRow",
    "LagRoleLabel",
    "LagSelectorLabel",
    "LagSignificanceSource",
    "MetricConfig",
    "MetricCurve",
    "ModelConfig",
    "OutputConfig",
    "PcmciAmiResult",
    "Phase0MiScore",
    "PredictiveInfoLearningCurve",
    "RobustnessStudyConfig",
    "RobustnessStudyResult",
    "RollingOriginConfig",
    "RoutingPolicyAudit",
    "RoutingPolicyAuditConfig",
    "RoutingRecommendation",
    "RoutingValidationBundle",
    "RoutingValidationCase",
    "RoutingValidationOutcome",
    "RoutingValidationSourceKind",
    "run_batch_triage",
    "run_batch_forecastability_workbench",
    "run_covariant_analysis",
    "run_lagged_exogenous_triage",
    "run_forecastability_fingerprint",
    "run_routing_validation",
    "run_ami_geometry_csv_batch",
    "forecast_prep_contract_to_lag_table",
    "forecast_prep_contract_to_markdown",
    "run_triage",
    "render_fingerprint_summary_dict",
    "SampleSizeStressResult",
    "ScorerInfo",
    "ScorerRegistry",
    "SensitivityConfig",
    "SeriesEvaluationResult",
    "SpectralPredictabilityResult",
    "TensorRoleLabel",
    "TargetBaselineCurves",
    "TransferEntropyResult",
    "TriageRequest",
    "TriageResult",
    "UncertaintyConfig",
    "default_registry",
    "save_fingerprint_bundle_json",
    "validate_time_series",
]
