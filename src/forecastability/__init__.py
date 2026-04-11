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
from forecastability.extensions import TargetBaselineCurves, compute_target_baseline_by_horizon
from forecastability.scorers import (
    DependenceScorer,
    ScorerInfo,
    ScorerRegistry,
    default_registry,
)
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
    "ForecastResult",
    "generate_ar1",
    "generate_white_noise",
    "BenchmarkDataConfig",
    "InterpretationResult",
    "MetricConfig",
    "MetricCurve",
    "ModelConfig",
    "OutputConfig",
    "RobustnessStudyConfig",
    "RobustnessStudyResult",
    "RollingOriginConfig",
    "SampleSizeStressResult",
    "ScorerInfo",
    "ScorerRegistry",
    "SensitivityConfig",
    "SeriesEvaluationResult",
    "TargetBaselineCurves",
    "UncertaintyConfig",
    "default_registry",
    "compute_target_baseline_by_horizon",
    "validate_time_series",
]
