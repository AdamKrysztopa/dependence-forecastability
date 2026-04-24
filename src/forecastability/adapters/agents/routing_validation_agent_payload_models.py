"""Deterministic agent payloads for routing-validation review (plan v0.3.3 V3_4-F09).

This module defines the deterministic payload consumed by the optional routing-
validation narration layer. It maps a :class:`RoutingValidationBundle` to a
frozen, JSON-safe A3 payload without recomputing any policy or audit fields.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from forecastability.utils.types import (
    RoutingPolicyAudit,
    RoutingValidationBundle,
    RoutingValidationCase,
)

__all__ = [
    "RoutingValidationAgentPayload",
    "routing_validation_agent_payload",
]

_DEFAULT_CAVEATS: tuple[str, ...] = (
    "Primary families are family-level guidance, not optimal-model claims.",
    "Abstain means no opinion, not failure.",
    "Downgrade means borderline-confident, not wrong.",
    (
        "threshold_margin and rule_stability are policy fragility signals, "
        "not forecasting-quality signals."
    ),
)


class RoutingValidationAgentPayload(BaseModel):
    """Evidence-bearing deterministic payload for one validation bundle.

    Attributes:
        bundle_audit: Aggregate pass / fail / downgrade / abstain counts.
        case_summaries: Per-case audit rows copied from the deterministic bundle.
        headline_findings: Deterministic bullet-style findings derived only from
            aggregate counts and case fields.
        caveats: Hard caveats that must survive any optional LLM narration
            verbatim.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    bundle_audit: RoutingPolicyAudit
    case_summaries: list[RoutingValidationCase]
    headline_findings: list[str] = Field(
        description=(
            "Deterministic short statements derived from the validation bundle "
            "without calling any LLM."
        )
    )
    caveats: list[str] = Field(
        default_factory=lambda: list(_DEFAULT_CAVEATS),
        description="Hard caveats that must be reproduced verbatim in narration.",
    )


def _headline_findings(bundle: RoutingValidationBundle) -> list[str]:
    """Build stable headline findings from a routing-validation bundle.

    Args:
        bundle: Deterministic routing-validation bundle.

    Returns:
        Ordered list of short findings derived from counts and case fields only.
    """
    audit = bundle.audit
    findings = [
        (
            f"Evaluated {audit.total_cases} case(s): {audit.passed_cases} pass, "
            f"{audit.downgraded_cases} downgrade, {audit.failed_cases} fail, "
            f"{audit.abstained_cases} abstain."
        )
    ]

    low_conf_cases = sorted(
        case.case_name for case in bundle.cases if case.confidence_label in {"low", "abstain"}
    )
    if low_conf_cases:
        findings.append("Low-confidence review cases: " + ", ".join(low_conf_cases) + ".")

    failed_cases = sorted(case.case_name for case in bundle.cases if case.outcome == "fail")
    if failed_cases:
        findings.append("Expected-family mismatches detected in: " + ", ".join(failed_cases) + ".")

    abstained_cases = sorted(case.case_name for case in bundle.cases if case.outcome == "abstain")
    if abstained_cases:
        findings.append("Abstained cases: " + ", ".join(abstained_cases) + ".")

    downgraded_real_cases = sorted(
        case.case_name
        for case in bundle.cases
        if case.outcome == "downgrade" and case.source_kind == "real"
    )
    if downgraded_real_cases:
        findings.append(
            "Real-series downgrades observed in: " + ", ".join(downgraded_real_cases) + "."
        )

    weakest_case = min(bundle.cases, key=lambda case: case.rule_stability)
    findings.append(
        f"Weakest rule-stability case: {weakest_case.case_name} "
        f"(rule_stability={weakest_case.rule_stability:.4f}, "
        f"threshold_margin={weakest_case.threshold_margin:.4f})."
    )
    return findings


def routing_validation_agent_payload(
    bundle: RoutingValidationBundle,
) -> RoutingValidationAgentPayload:
    """Build a deterministic routing-validation agent payload.

    Args:
        bundle: Deterministic routing-validation bundle from the use case.

    Returns:
        Frozen payload ready for serialisation or narration.
    """
    return RoutingValidationAgentPayload(
        bundle_audit=bundle.audit,
        case_summaries=list(bundle.cases),
        headline_findings=_headline_findings(bundle),
    )
