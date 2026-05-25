# Migration shim — canonical location is forecastability.domain.models.result_bundle
# Remove this shim in v0.6.0
from __future__ import annotations

import warnings as _warnings

from forecastability.domain.models.result_bundle import (  # noqa: F401
    MetadataValue,
    TriageBundleProvenance,
    TriageBundleWarning,
    TriageConfigSnapshot,
    TriageInputMetadata,
    TriageNumericOutputs,
    TriageResultBundle,
    TriageVersions,
    build_triage_result_bundle,
)

_warnings.warn(
    "forecastability.triage.result_bundle is deprecated in v0.5.0; "
    "use forecastability.domain.models.result_bundle instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
