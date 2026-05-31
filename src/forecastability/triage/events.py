# Migration shim — canonical location is forecastability.domain.models.events
# Remove this shim in v0.6.0
from __future__ import annotations

import warnings as _warnings

from forecastability.domain.models.events import (  # noqa: F401
    TriageError,
    TriageEvent,
    TriageStageCompleted,
    TriageStageStarted,
)

_warnings.warn(
    "forecastability.triage.events is deprecated in v0.5.0; "
    "use forecastability.domain.models.events instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
