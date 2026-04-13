"""Forecastability package implementing AMI and pAMI analysis."""

from forecastability.analyzer import (
    AnalyzeResult,
    ForecastabilityAnalyzer,
    ForecastabilityAnalyzerExog,
)
from forecastability.config import (
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
from forecastability.datasets import (
    ar1_theoretical_ami,
    generate_ar1,
    generate_white_noise,
)
from forecastability.scorers import (
    DependenceScorer,
    ScorerInfo,
    ScorerRegistry,
    default_registry,
)
from forecastability.triage.forecastability_profile import ForecastabilityProfile
from forecastability.triage.models import (
    TriageRequest,
    TriageResult,
)
from forecastability.triage.predictive_info_learning_curve import PredictiveInfoLearningCurve
from forecastability.triage.spectral_predictability import SpectralPredictabilityResult
from forecastability.types import (
    BackendComparisonResult,
    CanonicalExampleResult,
    CanonicalSummary,
    Diagnostics,
    ExogenousBenchmarkResult,
    ForecastResult,
    InterpretationResult,
    MetricCurve,
    RobustnessStudyResult,
    SampleSizeStressResult,
    SeriesEvaluationResult,
)
from forecastability.use_cases import run_batch_triage, run_triage
from forecastability.validation import validate_time_series

__all__ = [
    "AnalyzeResult",
    "ar1_theoretical_ami",
    "BackendComparisonResult",
    "CanonicalExampleResult",
    "CanonicalSummary",
    "CMIConfig",
    "Diagnostics",
    "DependenceScorer",
    "ExogenousBenchmarkConfig",
    "ExogenousBenchmarkResult",
    "ForecastabilityAnalyzer",
    "ForecastabilityAnalyzerExog",
    "ForecastabilityProfile",
    "ForecastResult",
    "generate_ar1",
    "generate_white_noise",
    "BenchmarkDataConfig",
    "InterpretationResult",
    "MetricConfig",
    "MetricCurve",
    "ModelConfig",
    "OutputConfig",
    "PredictiveInfoLearningCurve",
    "RobustnessStudyConfig",
    "RobustnessStudyResult",
    "RollingOriginConfig",
    "run_batch_triage",
    "run_triage",
    "SampleSizeStressResult",
    "ScorerInfo",
    "ScorerRegistry",
    "SensitivityConfig",
    "SeriesEvaluationResult",
    "SpectralPredictabilityResult",
    "TriageRequest",
    "TriageResult",
    "UncertaintyConfig",
    "default_registry",
    "validate_time_series",
]
