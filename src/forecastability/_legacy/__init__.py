"""forecastability._legacy — backward-compatibility shim (v0.5.0+).

Every name in this module was accessible from ``forecastability`` in v0.4.x
but is not part of the canonical v0.5.0 public surface defined in
``forecastability.api``.

Accessing any name here via ``forecastability.<name>`` triggers a
``DeprecationWarning``.  The warning is raised lazily (at access time, not at
``import forecastability`` time) so as not to penalise users who never touch
the legacy surface.

One name raises ``ImportError`` rather than ``DeprecationWarning`` because its
semantics changed in v0.5.0 and forward-compatibility cannot be guaranteed:

- ``compute_transfer_entropy`` — removed; use ``compute_transfer_entropy_ksg``
  from ``forecastability`` directly.

See ``docs/migration/v0.4.x_to_v0.5.0.md`` for the full migration guide.
"""

from __future__ import annotations

import importlib
import warnings
from typing import Any

# ---------------------------------------------------------------------------
# Names that raise ImportError — semantics changed, no drop-in replacement
# ---------------------------------------------------------------------------
_REMOVED_NAMES: dict[str, str] = {
    "compute_transfer_entropy": (
        "compute_transfer_entropy was removed in v0.5.0. "
        "Use compute_transfer_entropy_ksg from forecastability instead. "
        "See docs/migration/v0.4.x_to_v0.5.0.md."
    ),
}

# ---------------------------------------------------------------------------
# Legacy lazy map — (module_path, attr_name_or_None)
# attr_name=None  → use the key as the attribute name
# attr_name=""    → return the module itself
# ---------------------------------------------------------------------------
_LEGACY_MAP: dict[str, tuple[str, str | None]] = {
    # CSV geometry batch adapter
    "CsvGeometryBatchItem": ("forecastability.adapters.csv", None),
    "CsvGeometryBatchResult": ("forecastability.adapters.csv", None),
    "run_ami_geometry_csv_batch": ("forecastability.adapters.csv", None),
    # Diagnostics
    "compute_gcmi": ("forecastability.diagnostics.gcmi", None),
    # Extensions
    "TargetBaselineCurves": ("forecastability.use_cases.extensions", None),
    "compute_target_baseline_by_horizon": ("forecastability.use_cases.extensions", None),
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
    "ClassicalStructureResult": ("forecastability.triage.extended_forecastability", None),
    "ExtendedForecastabilityAnalysisResult": (
        "forecastability.triage.extended_forecastability",
        None,
    ),
    "ExtendedForecastabilityFingerprint": (
        "forecastability.triage.extended_forecastability",
        None,
    ),
    "ExtendedForecastabilityProfile": ("forecastability.triage.extended_forecastability", None),
    "ForecastabilityProfile": ("forecastability.triage.forecastability_profile", None),
    # Lag-Aware ModMRMR domain contracts (v0.4.3)
    "BlockedLagAwareFeature": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "ForecastSafeLagCandidate": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "KnownFutureProvenance": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "LagAwareModMRMRConfig": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "LagAwareModMRMRResult": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "LagLegalityLabel": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "NormalizationStrategy": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "PairwiseScorerSpec": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "RejectedLagAwareFeature": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "RejectionReason": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "ScorerDiagnostics": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "SelectedLagAwareFeature": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "SignificanceMethod": ("forecastability.triage.lag_aware_mod_mrmr", None),
    "MemoryStructureResult": ("forecastability.triage.extended_forecastability", None),
    "OrdinalComplexityResult": ("forecastability.triage.extended_forecastability", None),
    "PredictiveInfoLearningCurve": (
        "forecastability.triage.predictive_info_learning_curve",
        None,
    ),
    "SpectralForecastabilityResult": ("forecastability.triage.extended_forecastability", None),
    "SpectralPredictabilityResult": ("forecastability.triage.spectral_predictability", None),
    # Non-core use cases
    "run_lag_aware_mod_mrmr": ("forecastability.use_cases.lag_aware_mod_mrmr", None),
    "run_batch_triage": ("forecastability.use_cases", None),
    "run_extended_forecastability_analysis": (
        "forecastability.use_cases",
        "_run_extended_forecastability_analysis_public",
    ),
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
    # Config classes
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
    # Synthetic archetype generators
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
    # Less-common result types (from old utils.types shim)
    "AmiGeometryCurvePoint": ("forecastability.domain.value_objects.types", None),
    "AmiInformationGeometry": ("forecastability.domain.value_objects.types", None),
    "BackendComparisonResult": ("forecastability.domain.value_objects.types", None),
    "CanonicalExampleResult": ("forecastability.domain.value_objects.types", None),
    "CanonicalSummary": ("forecastability.domain.value_objects.types", None),
    "CausalGraphResult": ("forecastability.domain.value_objects.types", None),
    "CovariantAnalysisBundle": ("forecastability.domain.value_objects.types", None),
    "CovariantSummaryRow": ("forecastability.domain.value_objects.types", None),
    "CovariateRecommendation": ("forecastability.domain.value_objects.types", None),
    "Diagnostics": ("forecastability.domain.value_objects.types", None),
    "ExogenousBenchmarkResult": ("forecastability.domain.value_objects.types", None),
    "FamilyRecommendation": ("forecastability.domain.value_objects.types", None),
    "FingerprintBundle": ("forecastability.domain.value_objects.types", None),
    "ForecastPrepConfidence": ("forecastability.domain.value_objects.types", None),
    "ForecastPrepContractConfidence": ("forecastability.domain.value_objects.types", None),
    "ForecastPrepCovariateRole": ("forecastability.domain.value_objects.types", None),
    "ForecastPrepFamilyTier": ("forecastability.domain.value_objects.types", None),
    "ForecastPrepLagRole": ("forecastability.domain.value_objects.types", None),
    "ForecastResult": ("forecastability.domain.value_objects.types", None),
    "InterpretationResult": ("forecastability.domain.value_objects.types", None),
    "LaggedExogBundle": ("forecastability.domain.value_objects.types", None),
    "LaggedExogProfileRow": ("forecastability.domain.value_objects.types", None),
    "LaggedExogSelectionRow": ("forecastability.domain.value_objects.types", None),
    "LagRecommendation": ("forecastability.domain.value_objects.types", None),
    "LagRoleLabel": ("forecastability.domain.value_objects.types", None),
    "LagSelectorLabel": ("forecastability.domain.value_objects.types", None),
    "LagSignificanceSource": ("forecastability.domain.value_objects.types", None),
    "PcmciAmiResult": ("forecastability.domain.value_objects.types", None),
    "Phase0MiScore": ("forecastability.domain.value_objects.types", None),
    "RobustnessStudyResult": ("forecastability.domain.value_objects.types", None),
    "RoutingPolicyAudit": ("forecastability.domain.value_objects.types", None),
    "RoutingPolicyAuditConfig": ("forecastability.domain.value_objects.types", None),
    "RoutingValidationBundle": ("forecastability.domain.value_objects.types", None),
    "RoutingValidationCase": ("forecastability.domain.value_objects.types", None),
    "RoutingValidationOutcome": ("forecastability.domain.value_objects.types", None),
    "RoutingValidationSourceKind": ("forecastability.domain.value_objects.types", None),
    "SampleSizeStressResult": ("forecastability.domain.value_objects.types", None),
    "SeriesEvaluationResult": ("forecastability.domain.value_objects.types", None),
    "TensorRoleLabel": ("forecastability.domain.value_objects.types", None),
    # Notebook-compat names (large set — less commonly used)
    "build_canonical_markdown": ("forecastability.reporting", None),
    "build_case_summary": ("forecastability.use_cases.exog_benchmark", None),
    "build_complexity_band": ("forecastability.services.complexity_band_service", None),
    "build_expanding_window_splits": ("forecastability.pipeline.rolling_origin", None),
    "build_fingerprint_showcase_record": ("forecastability.reporting.fingerprint_showcase", None),
    "build_plain_language_math_summary": ("forecastability.reporting.fingerprint_showcase", None),
    "build_report_markdown": ("forecastability.use_cases.exog_benchmark", None),
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
    "create_screening_agent": ("forecastability.adapters.agents.runtime.screening_agent", None),
    "create_triage_agent": ("forecastability.adapters.agents.runtime.triage_agent", None),
    "driver_role_frame": ("forecastability.reporting.covariant_walkthrough", None),
    "exog_benchmark": ("forecastability.use_cases.exog_benchmark", ""),
    "F1ProfilePayload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "F5LyapunovPayload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "F7BatchRankPayload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "FeatureScreeningReport": ("forecastability.adapters.llm.screening_agent", None),
    "f1_profile_payload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "f2_limits_payload": ("forecastability.adapters.agents.triage_agent_payload_models", None),
    "f6_complexity_payload": (
        "forecastability.adapters.agents.triage_agent_payload_models",
        None,
    ),
    "f7_batch_rank_payload": (
        "forecastability.adapters.agents.triage_agent_payload_models",
        None,
    ),
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
    "load_benchmark_slice": ("forecastability.use_cases.exog_benchmark", None),
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
    "SerialisedTriageSummary": (
        "forecastability.adapters.agents.triage_summary_serializer",
        None,
    ),
    "serialise_batch": ("forecastability.adapters.agents.triage_summary_serializer", None),
    "serialise_batch_to_json": (
        "forecastability.adapters.agents.triage_summary_serializer",
        None,
    ),
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
    "TriageDeps": ("forecastability.adapters.agents.runtime.triage_agent", None),
    "verify_showcase_records": ("forecastability.reporting.fingerprint_showcase", None),
    "write_frame_csv": ("forecastability.reporting.covariant_walkthrough", None),
}


def __getattr__(name: str) -> Any:  # Any: legacy resolver returns heterogeneous types
    """Resolve legacy names lazily with DeprecationWarning.

    Args:
        name: Attribute name being accessed.

    Returns:
        The resolved object from the legacy source module.

    Raises:
        ImportError: If ``name`` is a removed symbol whose semantics changed in v0.5.0.
        AttributeError: If ``name`` is not in the legacy map at all.
    """
    if name in _REMOVED_NAMES:
        raise ImportError(_REMOVED_NAMES[name])

    target = _LEGACY_MAP.get(name)
    if target is None:
        raise AttributeError(
            f"module 'forecastability._legacy' has no attribute {name!r}. "
            "This name was not present in v0.4.x either. "
            "See docs/migration/v0.4.x_to_v0.5.0.md."
        )

    warnings.warn(
        f"forecastability.{name} is part of the legacy surface and will be removed "
        "in v0.6.0. Import it directly from its canonical module. "
        "See docs/migration/v0.4.x_to_v0.5.0.md.",
        DeprecationWarning,
        stacklevel=3,
    )

    module_path, attr_name = target
    module = importlib.import_module(module_path)
    if attr_name == "":
        return module
    return getattr(module, attr_name if attr_name is not None else name)
