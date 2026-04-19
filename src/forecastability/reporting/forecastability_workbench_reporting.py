"""Rendering helpers for the batch forecastability workbench."""

from __future__ import annotations

from forecastability.use_cases.batch_forecastability_workbench_models import (
    BatchForecastabilityWorkbenchItem,
    BatchForecastabilityWorkbenchResult,
)


def _executive_action_label(action: str) -> str:
    """Map internal action codes to manager-friendly decision labels."""
    labels = {
        "investigate_failure": "Fix the run before planning forecasts",
        "resolve_readiness": "Fix data readiness before model selection",
        "baseline_monitoring": "Keep a simple baseline and monitor",
        "seasonal_benchmark": "Start with season-aware forecasting",
        "linear_benchmark": "Start with compact linear models",
        "nonlinear_benchmark": "Benchmark richer models against strong baselines",
        "hybrid_review": "Review before committing to one model path",
    }
    return labels.get(action, action)


def _technical_item_section(item: BatchForecastabilityWorkbenchItem) -> str:
    """Render one technical per-series section."""
    lines = [
        f"## {item.series_id}",
        f"- batch_rank: {item.rank}",
        f"- triage_outcome: {item.triage_item.outcome}",
        f"- readiness_status: {item.triage_item.readiness_status}",
        f"- next_step_action: {item.next_step.action}",
        f"- priority_tier: {item.next_step.priority_tier}",
        (
            "- recommended_model_families: "
            f"{', '.join(item.next_step.recommended_model_families) or 'none'}"
        ),
        f"- validation_focus: {item.next_step.validation_focus}",
    ]

    if item.fingerprint_bundle is None:
        lines.extend(
            [
                "- fingerprint_status: unavailable",
                f"- why_this_action: {item.next_step.why_this_action}",
            ]
        )
        return "\n".join(lines)

    bundle = item.fingerprint_bundle
    fingerprint = bundle.fingerprint
    geometry = bundle.geometry
    recommendation = bundle.recommendation
    lines.extend(
        [
            f"- geometry_structure: {geometry.information_structure}",
            f"- signal_to_noise: {geometry.signal_to_noise:.4f}",
            f"- information_mass: {fingerprint.information_mass:.4f}",
            f"- nonlinear_share: {fingerprint.nonlinear_share:.4f}",
            f"- routing_confidence: {recommendation.confidence_label}",
            f"- caution_flags: {', '.join(recommendation.caution_flags) or 'none'}",
            f"- why_this_action: {item.next_step.why_this_action}",
        ]
    )
    return "\n".join(lines)


def build_batch_forecastability_markdown(
    result: BatchForecastabilityWorkbenchResult,
) -> str:
    """Build the technical markdown report for the batch workbench."""
    sections = [
        "# Batch Forecastability Workbench",
        "",
        "## Summary",
        f"- total_series: {result.summary.n_series}",
        f"- model_ready: {result.summary.n_model_ready}",
        f"- baseline_only: {result.summary.n_baseline_only}",
        f"- needs_review: {result.summary.n_needs_review}",
        f"- blocked_or_failed: {result.summary.n_blocked_or_failed}",
        f"- top_priority_series: {', '.join(result.summary.top_priority_series_ids) or 'none'}",
        "",
        result.summary.technical_summary,
        "",
    ]
    sections.extend(_technical_item_section(item) for item in result.items)
    return "\n\n".join(sections)


def build_batch_forecastability_executive_markdown(
    result: BatchForecastabilityWorkbenchResult,
) -> str:
    """Build a manager-friendly markdown report with minimal math vocabulary."""
    lines = [
        "# Forecasting Portfolio Brief",
        "",
        "## What We Reviewed",
        (
            f"We screened {result.summary.n_series} series in one deterministic batch to decide "
            "where forecasting effort is likely to pay off and where it is not."
        ),
        "",
        "## Decision Summary",
        f"- Ready for focused modeling now: {result.summary.n_model_ready}",
        f"- Keep on simple baselines for now: {result.summary.n_baseline_only}",
        f"- Worth review before committing: {result.summary.n_needs_review}",
        f"- Blocked or failed and needs remediation: {result.summary.n_blocked_or_failed}",
        "",
        result.summary.executive_summary,
        "",
        "## Recommended Next Moves",
    ]

    for item in result.items:
        lines.extend(
            [
                f"- {item.series_id}: {item.next_step.stakeholder_message}",
                f"  Recommended decision: {_executive_action_label(item.next_step.action)}.",
                f"  Validation focus: {item.next_step.validation_focus}",
            ]
        )

    return "\n".join(lines)
