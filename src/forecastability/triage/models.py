"""Domain models for the triage subsystem."""

from __future__ import annotations

from enum import StrEnum

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from forecastability.analyzer import AnalyzeResult
from forecastability.triage.complexity_band import ComplexityBandResult
from forecastability.triage.forecastability_profile import ForecastabilityProfile
from forecastability.triage.lyapunov import LargestLyapunovExponentResult
from forecastability.triage.theoretical_limit_diagnostics import TheoreticalLimitDiagnostics
from forecastability.types import InterpretationResult


class AnalysisGoal(StrEnum):
    """High-level intent of a triage request.

    ``comparison`` was removed in E9 (AGT-022) because no second reference
    series exists in :class:`TriageRequest`.  Multi-scorer comparison remains
    on the backlog as AGT-017 (re-opened, Could Have).
    """

    univariate = "univariate"
    exogenous = "exogenous"


class ReadinessStatus(StrEnum):
    """Outcome of the readiness gate."""

    blocked = "blocked"
    warning = "warning"
    clear = "clear"


class TriageRequest(BaseModel):
    """Inbound triage request.

    Attributes:
        series: Univariate target time series.
        exog: Optional exogenous series, must match ``series`` length.
        goal: Analysis goal, controls method routing.
        max_lag: Maximum lag to evaluate.
        n_surrogates: Number of surrogates for significance estimation.
        random_state: Seed for deterministic execution.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    series: np.ndarray
    exog: np.ndarray | None = None
    goal: AnalysisGoal = AnalysisGoal.univariate
    max_lag: int = 40
    n_surrogates: int = Field(default=99, ge=99)
    random_state: int = 42


class ReadinessWarning(BaseModel):
    """A single readiness warning.

    Attributes:
        code: Machine-readable warning code (e.g. ``"LAG_FEASIBILITY"``).
        message: Human-readable description of the warning.
    """

    model_config = ConfigDict(frozen=True)

    code: str
    message: str


class ReadinessReport(BaseModel):
    """Outcome from the readiness gate.

    Attributes:
        status: Overall readiness status.
        warnings: List of individual warnings, may be empty.
    """

    model_config = ConfigDict(frozen=True)

    status: ReadinessStatus
    warnings: list[ReadinessWarning]


class MethodPlan(BaseModel):
    """Compute path selected by the method router.

    Attributes:
        route: Selected route identifier.
        compute_surrogates: Whether to run surrogate significance estimation.
        assumptions: List of assumptions made when selecting this route.
        rationale: Human-readable explanation of the routing decision.
    """

    model_config = ConfigDict(frozen=True)

    route: str
    compute_surrogates: bool
    assumptions: list[str]
    rationale: str


class TriageResult(BaseModel):
    """Full composite result from a triage run.

    Attributes:
        request: Original triage request.
        readiness: Readiness gate outcome.
        method_plan: Selected compute path; ``None`` when blocked.
        analyze_result: :class:`~forecastability.analyzer.AnalyzeResult` from
            the analyzer; ``None`` when blocked (AGT-025).
        interpretation: :class:`~forecastability.types.InterpretationResult`;
            ``None`` when blocked (AGT-025).
        recommendation: Human-readable triage recommendation string.
        blocked: Convenience flag, ``True`` when readiness status is blocked.
        narrative: Optional LLM-generated explanation; always ``None`` for
            deterministic ``run_triage()`` runs (owned by agent adapter,
            AGT-028).
        timing: Per-stage wall-clock durations in milliseconds when an
            ``event_emitter`` is active; ``None`` otherwise.
        forecastability_profile: Derived forecastability profile with
            informative horizons and actionable recommendations; ``None``
            when blocked or when no analyze result is available.
        theoretical_limit_diagnostics: Information-theoretic ceiling on
            predictive improvement per horizon, derived from the AMI curve;
            ``None`` when blocked or when no analyze result is available.
        complexity_band: Entropy-based complexity classification for the
            target series (F6); ``None`` when blocked.
        largest_lyapunov_exponent: Estimated largest Lyapunov exponent from
            Rosenstein algorithm (F5, experimental); ``None`` when blocked or
            when estimation is skipped.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    request: TriageRequest
    readiness: ReadinessReport
    method_plan: MethodPlan | None = None
    analyze_result: AnalyzeResult | None = None
    interpretation: InterpretationResult | None = None
    recommendation: str | None = None
    blocked: bool
    narrative: str | None = None
    timing: dict[str, float] | None = None  # stage_name -> duration_ms (AGT-013)
    forecastability_profile: ForecastabilityProfile | None = None
    theoretical_limit_diagnostics: TheoreticalLimitDiagnostics | None = None
    complexity_band: ComplexityBandResult | None = None
    largest_lyapunov_exponent: LargestLyapunovExponentResult | None = None
