# Migration shim — canonical location is forecastability.domain.models.batch_models
# Remove this shim in v0.6.0
from __future__ import annotations

import warnings as _warnings

from forecastability.domain.models.batch_models import (  # noqa: F401
    FAILURE_TABLE_COLUMNS,
    SUMMARY_TABLE_COLUMNS,
    BatchFailureRow,
    BatchOutcome,
    BatchSeriesRequest,
    BatchSummaryRow,
    BatchTriageExecution,
    BatchTriageExecutionItem,
    BatchTriageItemResult,
    BatchTriageRequest,
    BatchTriageResponse,
)

_warnings.warn(
    "forecastability.triage.batch_models is deprecated in v0.5.0; "
    "use forecastability.domain.models.batch_models instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
