# Migration shim — see forecastability.domain.models.theoretical_limit_diagnostics
# Remove this shim in v0.6.0
from __future__ import annotations

import warnings as _warnings

from forecastability.domain.models.theoretical_limit_diagnostics import (  # noqa: F401
    TheoreticalLimitDiagnostics,
)

_warnings.warn(
    "forecastability.triage.theoretical_limit_diagnostics is deprecated in v0.5.0; "
    "use forecastability.domain.models.theoretical_limit_diagnostics instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
