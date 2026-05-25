# Migration shim — canonical location is forecastability.domain.models.forecastability_profile
# Remove this shim in v0.6.0
from __future__ import annotations

import warnings as _warnings

from forecastability.domain.models.forecastability_profile import (
    ForecastabilityProfile,  # noqa: F401
)

_warnings.warn(
    "forecastability.triage.forecastability_profile is deprecated in v0.5.0; "
    "use forecastability.domain.models.forecastability_profile instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
