"""Public API of the triage subsystem."""

from __future__ import annotations

from forecastability.triage.batch_models import (
    FAILURE_TABLE_COLUMNS,
    SUMMARY_TABLE_COLUMNS,
    BatchFailureRow,
    BatchSeriesRequest,
    BatchSummaryRow,
    BatchTriageExecution,
    BatchTriageExecutionItem,
    BatchTriageItemResult,
    BatchTriageRequest,
    BatchTriageResponse,
)
from forecastability.triage.events import (
    TriageError,
    TriageEvent,
    TriageStageCompleted,
    TriageStageStarted,
)
from forecastability.triage.forecastability_profile import ForecastabilityProfile
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
from forecastability.triage.result_bundle import (
    TriageBundleProvenance,
    TriageBundleWarning,
    TriageConfigSnapshot,
    TriageInputMetadata,
    TriageNumericOutputs,
    TriageResultBundle,
    TriageVersions,
    build_triage_result_bundle,
    load_result_bundle,
    save_result_bundle,
    save_triage_result_bundle,
)
from forecastability.triage.router import plan_method
from forecastability.triage.run_batch_triage import (
    rank_batch_items,
    run_batch_triage,
    run_batch_triage_with_details,
)
from forecastability.triage.run_triage import run_triage

__all__ = [
    "AnalysisGoal",
    "BatchSeriesRequest",
    "BatchTriageRequest",
    "BatchTriageItemResult",
    "BatchSummaryRow",
    "BatchFailureRow",
    "BatchTriageResponse",
    "BatchTriageExecutionItem",
    "BatchTriageExecution",
    "SUMMARY_TABLE_COLUMNS",
    "FAILURE_TABLE_COLUMNS",
    "ReadinessStatus",
    "ReadinessWarning",
    "ReadinessReport",
    "MethodPlan",
    "TriageRequest",
    "TriageResult",
    "TriageBundleWarning",
    "TriageInputMetadata",
    "TriageConfigSnapshot",
    "TriageVersions",
    "TriageNumericOutputs",
    "TriageBundleProvenance",
    "TriageResultBundle",
    "TriageStageStarted",
    "TriageStageCompleted",
    "TriageError",
    "TriageEvent",
    "ForecastabilityProfile",
    "assess_readiness",
    "plan_method",
    "rank_batch_items",
    "run_batch_triage",
    "run_batch_triage_with_details",
    "run_triage",
    "build_triage_result_bundle",
    "save_result_bundle",
    "load_result_bundle",
    "save_triage_result_bundle",
]
