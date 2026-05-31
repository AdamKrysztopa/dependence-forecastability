# Migration shim — see forecastability.domain.models.predictive_info_learning_curve
# Remove this shim in v0.6.0
from __future__ import annotations

import warnings as _warnings

from forecastability.domain.models.predictive_info_learning_curve import (  # noqa: F401
    PredictiveInfoLearningCurve,
)

_warnings.warn(
    "forecastability.triage.predictive_info_learning_curve is deprecated in v0.5.0; "
    "use forecastability.domain.models.predictive_info_learning_curve instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
