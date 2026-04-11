"""Domain models for the triage subsystem."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict


class AnalysisGoal(StrEnum):
    """High-level intent of a triage request."""

    univariate = "univariate"
    exogenous = "exogenous"
    comparison = "comparison"


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
    n_surrogates: int = 99
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
        analyze_result: Runtime ``AnalyzeResult`` from the analyzer; typed as
            ``Any`` to avoid circular imports — validated by duck-typing at use-
            case level.
        interpretation: Runtime ``InterpretationResult``; typed as ``Any`` for
            the same reason.
        recommendation: Human-readable triage recommendation string.
        blocked: Convenience flag, ``True`` when readiness status is blocked.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    request: TriageRequest
    readiness: ReadinessReport
    method_plan: MethodPlan | None = None
    analyze_result: Any | None = None  # AnalyzeResult at runtime
    interpretation: Any | None = None  # InterpretationResult at runtime
    recommendation: str | None = None
    blocked: bool
