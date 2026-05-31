# Migration shim — canonical location is forecastability.domain.value_objects.config
# Remove this shim in v0.6.0
from __future__ import annotations

import warnings as _warnings

from forecastability.domain.value_objects.config import (  # noqa: F401
    BenchmarkDataConfig,
    CMIConfig,
    ExogenousBenchmarkConfig,
    ExogenousLagWindowConfig,
    ExogenousScreeningPruningConfig,
    ExogenousScreeningRecommendationConfig,
    ExogenousScreeningWorkbenchConfig,
    MetricConfig,
    ModelConfig,
    OutputConfig,
    PaperBaselineConfig,
    RobustnessStudyConfig,
    RollingOriginConfig,
    SensitivityConfig,
    UncertaintyConfig,
)

_warnings.warn(
    "forecastability.utils.config is deprecated in v0.5.0; "
    "use forecastability.domain.value_objects.config instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
