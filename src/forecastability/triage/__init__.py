"""Public API of the triage subsystem."""

from __future__ import annotations

from forecastability.triage.batch_models import (
    BatchFailureRow,
    BatchSeriesRequest,
    BatchSummaryRow,
    BatchTriageItemResult,
    BatchTriageRequest,
    BatchTriageResponse,
    FAILURE_TABLE_COLUMNS,
    SUMMARY_TABLE_COLUMNS,
)
from forecastability.triage.events import (
    TriageError,
    TriageEvent,
    TriageStageCompleted,
    TriageStageStarted,
)
from forecastability.triage.models import (
    AnalysisGoal,
    MethodPlan,
    ReadinessReport,
    ReadinessStatus,
    ReadinessWarning,
    TriageRequest,
    TriageResult,
)
from forecastability.triage.readiness import assess_readiness
from forecastability.triage.router import plan_method
from forecastability.triage.run_batch_triage import rank_batch_items, run_batch_triage
from forecastability.triage.run_triage import run_triage

__all__ = [
    "AnalysisGoal",
    "BatchSeriesRequest",
    "BatchTriageRequest",
    "BatchTriageItemResult",
    "BatchSummaryRow",
    "BatchFailureRow",
    "BatchTriageResponse",
    "SUMMARY_TABLE_COLUMNS",
    "FAILURE_TABLE_COLUMNS",
    "ReadinessStatus",
    "ReadinessWarning",
    "ReadinessReport",
    "MethodPlan",
    "TriageRequest",
    "TriageResult",
    "TriageStageStarted",
    "TriageStageCompleted",
    "TriageError",
    "TriageEvent",
    "assess_readiness",
    "plan_method",
    "rank_batch_items",
    "run_batch_triage",
    "run_triage",
]
