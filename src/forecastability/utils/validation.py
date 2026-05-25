# Migration shim — canonical location is forecastability.domain.value_objects.validation
# Remove this shim in v0.6.0
from __future__ import annotations

import warnings as _warnings

from forecastability.domain.value_objects.validation import validate_time_series  # noqa: F401

_warnings.warn(
    "forecastability.utils.validation is deprecated in v0.5.0; "
    "use forecastability.domain.value_objects.validation instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
