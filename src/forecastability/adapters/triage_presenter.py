"""Shared presenter for converting ``TriageResult`` to a canonical view.

Centralises the ``TriageResult → JSON-safe dict`` serialisation that was
previously duplicated across four adapters (api, cli, mcp_server,
pydantic_ai_agent).  Each adapter now delegates to this module and extends
or subsets the canonical view as needed.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from forecastability.triage.models import TriageResult


class TriageResultView(BaseModel):
    """Canonical JSON-safe view of a :class:`TriageResult`.

    All fields are plain Python types — no numpy arrays.

    Attributes:
        blocked: ``True`` when the readiness gate blocked processing.
        readiness_status: Readiness gate status string.
        readiness_warnings: List of ``{"code": ..., "message": ...}`` dicts.
        route: Compute route selected; ``None`` when blocked.
        compute_surrogates: Whether surrogates were computed; ``None`` when blocked.
        recommendation: Deterministic triage recommendation; ``None`` when blocked.
        forecastability_class: High-level forecastability class; ``None`` when blocked.
        directness_class: Directness class; ``None`` when blocked.
        modeling_regime: Recommended modeling regime; ``None`` when blocked.
        primary_lags: Key lags identified; empty list when blocked or none found.
        n_sig_raw_lags: Count of raw significant lags.
        n_sig_partial_lags: Count of partial significant lags.
        method: Analyzer method identifier; ``None`` when blocked.
        method_plan_rationale: Rationale for the routing decision; ``None`` when blocked.
        method_plan_assumptions: Assumptions of the routing decision; ``None`` when blocked.
        pattern_class: Pattern class from interpretation; ``None`` when absent.
    """

    model_config = ConfigDict(frozen=True)

    blocked: bool
    readiness_status: str
    readiness_warnings: list[dict[str, str]]
    route: str | None = None
    compute_surrogates: bool | None = None
    recommendation: str | None = None
    forecastability_class: str | None = None
    directness_class: str | None = None
    modeling_regime: str | None = None
    primary_lags: list[int] = []
    n_sig_raw_lags: int = 0
    n_sig_partial_lags: int = 0
    method: str | None = None
    method_plan_rationale: str | None = None
    method_plan_assumptions: list[str] | None = None
    pattern_class: str | None = None
    extended_forecastability_analysis: dict[str, object] | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )


class TriageAnalyticsView(BaseModel):
    """Extended analytics view for the PydanticAI agent adapter.

    Contains summary statistics from the raw/partial MI curves and
    interpretation diagnostics that the LLM needs for narrative generation.

    Attributes:
        raw_curve_mean: Mean of the first 20 raw-curve values (or all if < 20).
        partial_curve_mean: Mean of the first 20 partial-curve values.
        raw_curve_max: Maximum raw-curve value.
        partial_curve_max: Maximum partial-curve value.
        narrative: Interpretation narrative; ``None`` when absent.
        diagnostics: Interpretation diagnostics dict; ``None`` when absent.
    """

    model_config = ConfigDict(frozen=True)

    raw_curve_mean: float
    partial_curve_mean: float
    raw_curve_max: float
    partial_curve_max: float
    narrative: str | None = None
    diagnostics: dict[str, float | int] | None = None


def present_triage_result(result: TriageResult) -> TriageResultView:
    """Convert a :class:`TriageResult` to a canonical JSON-safe view.

    Args:
        result: Full composite result from a triage run.

    Returns:
        :class:`TriageResultView` with all common fields populated.
    """
    warnings = [{"code": w.code, "message": w.message} for w in result.readiness.warnings]

    if result.blocked:
        return TriageResultView(
            blocked=True,
            readiness_status=result.readiness.status.value,
            readiness_warnings=warnings,
        )

    ar = result.analyze_result
    interp = result.interpretation
    mp = result.method_plan

    return TriageResultView(
        blocked=False,
        readiness_status=result.readiness.status.value,
        readiness_warnings=warnings,
        route=mp.route if mp else None,
        compute_surrogates=mp.compute_surrogates if mp else None,
        recommendation=result.recommendation,
        forecastability_class=interp.forecastability_class if interp else None,
        directness_class=interp.directness_class if interp else None,
        modeling_regime=interp.modeling_regime if interp else None,
        primary_lags=list(interp.primary_lags) if interp and interp.primary_lags else [],
        n_sig_raw_lags=(
            int(ar.sig_raw_lags.size) if ar is not None and ar.sig_raw_lags is not None else 0
        ),
        n_sig_partial_lags=(
            int(ar.sig_partial_lags.size)
            if ar is not None and ar.sig_partial_lags is not None
            else 0
        ),
        method=ar.method if ar is not None else None,
        method_plan_rationale=mp.rationale if mp else None,
        method_plan_assumptions=mp.assumptions if mp else None,
        pattern_class=getattr(interp, "pattern_class", None) if interp else None,
        extended_forecastability_analysis=(
            result.extended_forecastability_analysis.model_dump(mode="json")
            if result.extended_forecastability_analysis is not None
            else None
        ),
    )


def present_triage_analytics(result: TriageResult) -> TriageAnalyticsView | None:
    """Extract analytics summary for the PydanticAI agent adapter.

    Args:
        result: Full composite result from a triage run.

    Returns:
        :class:`TriageAnalyticsView` when an analyze result is available,
        ``None`` otherwise.
    """
    ar = result.analyze_result
    if ar is None:
        return None

    interp = result.interpretation

    diagnostics: dict[str, float | int] | None = None
    if interp is not None:
        diagnostics = {
            "peak_ami_first_5": interp.diagnostics.peak_ami_first_5,
            "directness_ratio": interp.diagnostics.directness_ratio,
            "n_sig_ami": interp.diagnostics.n_sig_ami,
            "n_sig_pami": interp.diagnostics.n_sig_pami,
        }

    return TriageAnalyticsView(
        raw_curve_mean=float(np.mean(ar.raw[:20]) if ar.raw.size >= 20 else np.mean(ar.raw)),
        partial_curve_mean=float(
            np.mean(ar.partial[:20]) if ar.partial.size >= 20 else np.mean(ar.partial)
        ),
        raw_curve_max=float(np.max(ar.raw)),
        partial_curve_max=float(np.max(ar.partial)),
        narrative=interp.narrative if interp is not None else None,
        diagnostics=diagnostics,
    )
