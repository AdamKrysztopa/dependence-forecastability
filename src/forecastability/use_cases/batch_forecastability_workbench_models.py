"""Typed models for the batch forecastability workbench use case."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from forecastability.triage.batch_models import BatchTriageItemResult, BatchTriageRequest
from forecastability.triage.models import TriageResult
from forecastability.utils.types import FingerprintBundle

ForecastingNextStepAction = Literal[
    "investigate_failure",
    "resolve_readiness",
    "baseline_monitoring",
    "seasonal_benchmark",
    "linear_benchmark",
    "nonlinear_benchmark",
    "hybrid_review",
]

PriorityTier = Literal["high", "review", "low"]


class ForecastingNextStepPlan(BaseModel):
    """Deterministic next-step plan for one series."""

    model_config = ConfigDict(frozen=True)

    action: ForecastingNextStepAction
    priority_tier: PriorityTier
    recommended_model_families: list[str] = Field(default_factory=list)
    why_this_action: str
    validation_focus: str
    stakeholder_message: str


class BatchForecastabilityWorkbenchItem(BaseModel):
    """One ranked series item in the batch forecastability workbench."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    rank: int | None
    series_id: str
    triage_item: BatchTriageItemResult
    triage_result: TriageResult | None = None
    fingerprint_bundle: FingerprintBundle | None = None
    next_step: ForecastingNextStepPlan


class BatchForecastabilityWorkbenchSummary(BaseModel):
    """Top-level summary for technical and executive reporting."""

    model_config = ConfigDict(frozen=True)

    n_series: int
    n_model_ready: int
    n_baseline_only: int
    n_needs_review: int
    n_blocked_or_failed: int
    top_priority_series_ids: list[str] = Field(default_factory=list)
    baseline_series_ids: list[str] = Field(default_factory=list)
    blocked_or_failed_series_ids: list[str] = Field(default_factory=list)
    technical_summary: str
    executive_summary: str


class BatchForecastabilityWorkbenchResult(BaseModel):
    """Composite output for batch triage, routing, and next-step planning."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    request: BatchTriageRequest
    items: list[BatchForecastabilityWorkbenchItem]
    summary: BatchForecastabilityWorkbenchSummary
