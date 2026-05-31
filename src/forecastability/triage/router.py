# Migration shim — canonical location is forecastability.domain.models.router
# Remove this shim in v0.6.0
from __future__ import annotations

import warnings as _warnings

from forecastability.domain.models.router import plan_method  # noqa: F401

_warnings.warn(
    "forecastability.triage.router is deprecated in v0.5.0; "
    "use forecastability.domain.models.router instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
