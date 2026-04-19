"""Forecastability package implementing AMI and pAMI analysis."""

from forecastability.diagnostics.gcmi import compute_gcmi
from forecastability.metrics.scorers import (
    DependenceScorer,
    ScorerInfo,
    ScorerRegistry,
    default_registry,
    gcmi_scorer,
)
from forecastability.pipeline.analyzer import (
    AnalyzeResult,
    ForecastabilityAnalyzer,
    ForecastabilityAnalyzerExog,
)
from forecastability.reporting.fingerprint_reporting import (
    build_fingerprint_markdown,
    build_fingerprint_panel_markdown,
    build_fingerprint_summary_dict,
    build_fingerprint_summary_row,
    render_fingerprint_summary_dict,
    save_fingerprint_bundle_json,
)
from forecastability.triage.forecastability_profile import ForecastabilityProfile
from forecastability.triage.models import (
    TriageRequest,
    TriageResult,
)
from forecastability.triage.predictive_info_learning_curve import PredictiveInfoLearningCurve
from forecastability.triage.spectral_predictability import SpectralPredictabilityResult
from forecastability.use_cases import run_batch_triage, run_covariant_analysis, run_triage
from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.utils.config import (
    BenchmarkDataConfig,
    CMIConfig,
    ExogenousBenchmarkConfig,
    MetricConfig,
    ModelConfig,
    OutputConfig,
    RobustnessStudyConfig,
    RollingOriginConfig,
    SensitivityConfig,
    UncertaintyConfig,
)
from forecastability.utils.datasets import (
    ar1_theoretical_ami,
    generate_ar1,
    generate_white_noise,
)
from forecastability.utils.synthetic import (
    generate_ar1_monotonic,
    generate_covariant_benchmark,
    generate_directional_pair,
    generate_fingerprint_archetypes,
    generate_mediated_directness_drop,
    generate_nonlinear_mixed,
    generate_seasonal_periodic,
)
from forecastability.utils.types import (
    AmiGeometryCurvePoint,
    AmiInformationGeometry,
    BackendComparisonResult,
    CanonicalExampleResult,
    CanonicalSummary,
    CausalGraphResult,
    CovariantAnalysisBundle,
    CovariantSummaryRow,
    Diagnostics,
    ExogenousBenchmarkResult,
    FingerprintBundle,
    ForecastabilityFingerprint,
    ForecastResult,
    GcmiResult,
    InterpretationResult,
    MetricCurve,
    PcmciAmiResult,
    Phase0MiScore,
    RobustnessStudyResult,
    RoutingRecommendation,
    SampleSizeStressResult,
    SeriesEvaluationResult,
    TransferEntropyResult,
)
from forecastability.utils.validation import validate_time_series

__version__ = "0.3.0"

__all__ = [
    "AmiGeometryCurvePoint",
    "AmiInformationGeometry",
    "AnalyzeResult",
    "ar1_theoretical_ami",
    "BackendComparisonResult",
    "CanonicalExampleResult",
    "CanonicalSummary",
    "CausalGraphResult",
    "CMIConfig",
    "CovariantAnalysisBundle",
    "CovariantSummaryRow",
    "Diagnostics",
    "build_fingerprint_markdown",
    "build_fingerprint_panel_markdown",
    "build_fingerprint_summary_dict",
    "build_fingerprint_summary_row",
    "DependenceScorer",
    "ExogenousBenchmarkConfig",
    "ExogenousBenchmarkResult",
    "FingerprintBundle",
    "ForecastabilityAnalyzer",
    "ForecastabilityAnalyzerExog",
    "ForecastabilityFingerprint",
    "ForecastabilityProfile",
    "ForecastResult",
    "GcmiResult",
    "gcmi_scorer",
    "compute_gcmi",
    "generate_ar1",
    "generate_ar1_monotonic",
    "generate_covariant_benchmark",
    "generate_directional_pair",
    "generate_fingerprint_archetypes",
    "generate_mediated_directness_drop",
    "generate_nonlinear_mixed",
    "generate_seasonal_periodic",
    "generate_white_noise",
    "BenchmarkDataConfig",
    "InterpretationResult",
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
    "RoutingRecommendation",
    "run_batch_triage",
    "run_covariant_analysis",
    "run_forecastability_fingerprint",
    "run_triage",
    "render_fingerprint_summary_dict",
    "SampleSizeStressResult",
    "ScorerInfo",
    "ScorerRegistry",
    "SensitivityConfig",
    "SeriesEvaluationResult",
    "SpectralPredictabilityResult",
    "TransferEntropyResult",
    "TriageRequest",
    "TriageResult",
    "UncertaintyConfig",
    "default_registry",
    "save_fingerprint_bundle_json",
    "validate_time_series",
]
