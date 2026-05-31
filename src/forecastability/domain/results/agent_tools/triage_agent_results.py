"""Frozen Pydantic result models for triage agent tool returns.

Each model maps 1-to-1 to the dict keys previously returned by the
corresponding ``@agent.tool`` function in
:mod:`forecastability.adapters.agents.runtime.triage_agent`.

No new fields are added; semantics are unchanged.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = [
    "ReadinessWarningResult",
    "ValidateSeriesResult",
    "MethodPlanResult",
    "ReadinessBlockedResult",
    "AnalyzeSummaryResult",
    "InterpretationResult",
    "TriageRunResult",
    "ScorerInfoResult",
]


class ReadinessWarningResult(BaseModel):
    """A single readiness warning entry.

    Attributes:
        code: Machine-readable warning code.
        message: Human-readable warning message.
    """

    model_config = ConfigDict(frozen=True)

    code: str
    message: str


class ValidateSeriesResult(BaseModel):
    """Result returned by the ``validate_series`` tool.

    Attributes:
        status: Readiness status value (e.g. ``"ok"``, ``"blocked"``).
        warnings: List of readiness warnings.
    """

    model_config = ConfigDict(frozen=True)

    status: str
    warnings: list[ReadinessWarningResult]


class ReadinessBlockedResult(BaseModel):
    """Result returned when the series is blocked before planning.

    Attributes:
        error: Human-readable block reason.
        readiness: Nested readiness report.
    """

    model_config = ConfigDict(frozen=True)

    error: str
    readiness: ValidateSeriesResult


class MethodPlanResult(BaseModel):
    """Result returned by the ``plan_analysis`` tool when not blocked.

    Attributes:
        route: Routing key selected by the deterministic planner.
        compute_surrogates: Whether surrogate computation is needed.
        assumptions: Assumptions underlying the selected route.
        rationale: Human-readable rationale for the route selection.
    """

    model_config = ConfigDict(frozen=True)

    route: str
    compute_surrogates: bool
    assumptions: list[str]
    rationale: str


class AnalyzeSummaryResult(BaseModel):
    """Analysis summary nested inside :class:`TriageRunResult`.

    Attributes:
        method: Dependence estimator identifier.
        recommendation: Deterministic triage recommendation.
        raw_curve_mean: Mean of the raw AMI curve.
        partial_curve_mean: Mean of the partial AMI curve.
        n_sig_raw_lags: Number of significant raw lags.
        n_sig_partial_lags: Number of significant partial lags.
        raw_curve_max: Maximum of the raw AMI curve.
        partial_curve_max: Maximum of the partial AMI curve.
    """

    model_config = ConfigDict(frozen=True)

    method: str
    recommendation: str
    raw_curve_mean: float
    partial_curve_mean: float
    n_sig_raw_lags: int
    n_sig_partial_lags: int
    raw_curve_max: float
    partial_curve_max: float


class InterpretationResult(BaseModel):
    """Interpretation section nested inside :class:`TriageRunResult`.

    Attributes:
        forecastability_class: Forecastability level label.
        directness_class: Directness level label.
        primary_lags: Most important lag indices.
        modeling_regime: Recommended modeling strategy identifier.
        narrative: LLM-safe deterministic narrative fragment (optional).
        diagnostics: Optional diagnostic string (optional).
    """

    model_config = ConfigDict(frozen=True)

    forecastability_class: str
    directness_class: str
    primary_lags: list[int]
    modeling_regime: str
    narrative: str | None = None
    diagnostics: str | None = None


class TriageRunResult(BaseModel):
    """Result returned by the ``run_full_triage`` tool.

    All fields correspond 1-to-1 with the keys previously returned in the
    ``dict[str, Any]`` response.

    Attributes:
        blocked: Whether the readiness gate blocked execution.
        readiness: Readiness status dict.
        method_plan: Optional method plan (absent when blocked).
        analyze_summary: Optional analysis summary.
        interpretation: Optional interpretation section.
        recommendation: Optional triage recommendation string.
        timing_ms: Optional per-step timing dict.
    """

    model_config = ConfigDict(frozen=True)

    blocked: bool
    readiness: ValidateSeriesResult
    method_plan: MethodPlanResult | None = None
    analyze_summary: AnalyzeSummaryResult | None = None
    interpretation: InterpretationResult | None = None
    recommendation: str | None = None
    timing_ms: dict[str, float] | None = None


class ScorerInfoResult(BaseModel):
    """A single scorer entry returned by ``list_available_scorers``.

    Attributes:
        name: Scorer identifier name.
        family: Scorer family label.
        description: Human-readable scorer description.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    family: str
    description: str
