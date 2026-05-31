# Migration shim — canonical location is forecastability.domain.models.complexity_band
# Remove this shim in v0.6.0
from __future__ import annotations

import warnings as _warnings

from forecastability.domain.models.complexity_band import ComplexityBandResult  # noqa: F401

_warnings.warn(
    "forecastability.triage.complexity_band is deprecated in v0.5.0; "
    "use forecastability.domain.models.complexity_band instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
