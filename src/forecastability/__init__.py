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
from forecastability.triage.forecastability_profile import ForecastabilityProfile
from forecastability.triage.models import (
    TriageRequest,
    TriageResult,
)
from forecastability.triage.predictive_info_learning_curve import PredictiveInfoLearningCurve
from forecastability.triage.spectral_predictability import SpectralPredictabilityResult
from forecastability.use_cases import run_batch_triage, run_covariant_analysis, run_triage
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
from forecastability.utils.types import (
    BackendComparisonResult,
    CanonicalExampleResult,
    CanonicalSummary,
    CausalGraphResult,
    CovariantAnalysisBundle,
    CovariantSummaryRow,
    Diagnostics,
    ExogenousBenchmarkResult,
    ForecastResult,
    GcmiResult,
    InterpretationResult,
    MetricCurve,
    PcmciAmiResult,
    Phase0MiScore,
    RobustnessStudyResult,
    SampleSizeStressResult,
    SeriesEvaluationResult,
    TransferEntropyResult,
)
from forecastability.utils.validation import validate_time_series

__version__ = "0.2.0"

__all__ = [
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
    "DependenceScorer",
    "ExogenousBenchmarkConfig",
    "ExogenousBenchmarkResult",
    "ForecastabilityAnalyzer",
    "ForecastabilityAnalyzerExog",
    "ForecastabilityProfile",
    "ForecastResult",
    "GcmiResult",
    "gcmi_scorer",
    "compute_gcmi",
    "generate_ar1",
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
    "run_batch_triage",
    "run_covariant_analysis",
    "run_triage",
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
    "validate_time_series",
]
