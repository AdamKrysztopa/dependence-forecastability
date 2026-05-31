# Migration shim — canonical location is forecastability.domain.models.triage
# Remove this shim in v0.6.0
from __future__ import annotations

import warnings as _warnings

from forecastability.domain.models.triage import (  # noqa: F401
    AnalysisGoal,
    MethodPlan,
    ReadinessReport,
    ReadinessStatus,
    ReadinessWarning,
    TriageRequest,
    TriageResult,
)
from forecastability.domain.value_objects.types import InterpretationResult  # noqa: F401

_warnings.warn(
    "forecastability.triage.models is deprecated in v0.5.0; "
    "use forecastability.domain.models.triage instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
