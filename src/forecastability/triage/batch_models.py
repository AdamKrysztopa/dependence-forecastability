"""Pydantic models for deterministic batch triage screening."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from forecastability.triage.models import AnalysisGoal, TriageResult

BatchOutcome = Literal["ok", "blocked", "failed"]

SUMMARY_TABLE_COLUMNS: tuple[str, ...] = (
    "rank",
    "series_id",
    "outcome",
    "readiness_status",
    "warning_codes",
    "forecastability_profile",
    "forecastability_class",
    "directness_class",
    "directness_ratio",
    "exogenous_usefulness",
    "recommended_next_action",
    "recommendation",
    "error_code",
    "error_message",
)

FAILURE_TABLE_COLUMNS: tuple[str, ...] = (
    "series_id",
    "error_code",
    "error_message",
)


class BatchSeriesRequest(BaseModel):
    """One series input for batch triage.

    Attributes:
        series_id: Stable identifier for this series in outputs.
        series: Target series values.
        exog: Optional exogenous series values.
        goal: Analysis goal for this item.
        max_lag: Optional per-item max lag override.
        n_surrogates: Optional per-item surrogate-count override.
        random_state: Optional per-item random-state override.
    """

    model_config = ConfigDict(frozen=True)

    series_id: str
    series: list[float]
    exog: list[float] | None = None
    goal: AnalysisGoal = AnalysisGoal.univariate
    max_lag: int | None = None
    n_surrogates: int | None = None
    random_state: int | None = None

    @field_validator("series")
    @classmethod
    def series_not_empty(cls, value: list[float]) -> list[float]:
        """Ensure each batch item has at least one observation."""
        if len(value) == 0:
            raise ValueError("series must not be empty")
        return value


class BatchTriageRequest(BaseModel):
    """Inbound request for batch triage screening.

    Attributes:
        items: Batch entries to evaluate.
        max_lag: Default max lag used when an item does not override it.
        n_surrogates: Default surrogate count for items without an override.
        random_state: Default random state for items without an override.
    """

    model_config = ConfigDict(frozen=True)

    items: list[BatchSeriesRequest]
    max_lag: int = 40
    n_surrogates: int = 99
    random_state: int = 42

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, value: list[BatchSeriesRequest]) -> list[BatchSeriesRequest]:
        """Require at least one item in the batch payload."""
        if len(value) == 0:
            raise ValueError("items must contain at least one batch entry")
        return value


class BatchTriageItemResult(BaseModel):
    """Per-series batch triage result used for ranking and exports.

    Attributes:
        rank: 1-based rank assigned after deterministic sorting.
        series_id: Series identifier from the request.
        outcome: ``"ok"``, ``"blocked"``, or ``"failed"``.
        blocked: Convenience flag mirroring readiness blocking.
        readiness_status: Readiness label (or ``"failed"`` on hard failure).
        warning_codes: Readiness warning codes.
        forecastability_profile: Combined profile string when available.
        forecastability_class: Forecastability class when available.
        directness_class: Directness class when available.
        directness_ratio: pAMI/AMI directness ratio when available.
        exogenous_usefulness: Exogenous usefulness bucket or ``"not_applicable"``.
        recommended_next_action: Deterministic next-action label for routing.
        recommendation: Original deterministic recommendation text.
        error_code: Error type for failed items.
        error_message: Error message for failed items.
    """

    model_config = ConfigDict(frozen=True)

    rank: int | None = None
    series_id: str
    outcome: BatchOutcome
    blocked: bool
    readiness_status: str
    warning_codes: list[str] = Field(default_factory=list)
    forecastability_profile: str | None = None
    forecastability_class: str | None = None
    directness_class: str | None = None
    directness_ratio: float | None = None
    exogenous_usefulness: str = "not_applicable"
    recommended_next_action: str
    recommendation: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class BatchSummaryRow(BaseModel):
    """Flat row schema for the batch summary export table."""

    model_config = ConfigDict(frozen=True)

    rank: int | None
    series_id: str
    outcome: BatchOutcome
    readiness_status: str
    warning_codes: str
    forecastability_profile: str | None
    forecastability_class: str | None
    directness_class: str | None
    directness_ratio: float | None
    exogenous_usefulness: str
    recommended_next_action: str
    recommendation: str | None
    error_code: str | None
    error_message: str | None


class BatchFailureRow(BaseModel):
    """Flat row schema for failed-series exports."""

    model_config = ConfigDict(frozen=True)

    series_id: str
    error_code: str
    error_message: str


class BatchTriageResponse(BaseModel):
    """Composite response for batch triage mode.

    Attributes:
        items: Ranked per-series outcomes.
        summary_table: Flat rows suitable for CSV/JSON export.
        failure_table: Failed-series rows suitable for CSV/JSON export.
    """

    model_config = ConfigDict(frozen=True)

    items: list[BatchTriageItemResult]
    summary_table: list[BatchSummaryRow]
    failure_table: list[BatchFailureRow]


class BatchTriageExecutionItem(BaseModel):
    """One ranked batch item paired with the underlying triage result.

    Attributes:
        result: Ranked batch item emitted by ``run_batch_triage``.
        triage_result: Detailed triage output for successful/blocked items,
            ``None`` for failed entries where triage raised an error.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    result: BatchTriageItemResult
    triage_result: TriageResult | None = None


class BatchTriageExecution(BaseModel):
    """Batch response plus per-item execution details.

    Attributes:
        response: Stable ranked response with summary/failure tables.
        items_with_results: Ranked items paired with optional detailed
            :class:`TriageResult` payloads.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    response: BatchTriageResponse
    items_with_results: list[BatchTriageExecutionItem]
