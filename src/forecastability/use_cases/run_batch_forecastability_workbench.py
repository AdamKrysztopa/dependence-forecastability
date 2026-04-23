"""Batch workbench for triage, fingerprint routing, and forecast next steps."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from forecastability.services.ami_information_geometry_service import (
    AmiInformationGeometryConfig,
)
from forecastability.services.fingerprint_service import FingerprintThresholdConfig
from forecastability.services.routing_policy_service import RoutingPolicyConfig
from forecastability.triage.batch_models import BatchTriageRequest
from forecastability.triage.models import TriageRequest, TriageResult
from forecastability.use_cases.batch_forecastability_workbench_models import (
    BatchForecastabilityWorkbenchItem,
    BatchForecastabilityWorkbenchResult,
    BatchForecastabilityWorkbenchSummary,
    ForecastingNextStepPlan,
)
from forecastability.use_cases.run_batch_triage import run_batch_triage_with_details
from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.use_cases.run_triage import run_triage
from forecastability.utils.types import FingerprintBundle


def _directness_ratio(result: TriageResult | None) -> float | None:
    """Extract directness_ratio from triage interpretation when available."""
    if result is None or result.interpretation is None:
        return None
    return result.interpretation.diagnostics.directness_ratio


def _stringify_families(values: Sequence[object]) -> list[str]:
    """Convert routed family labels to plain string values."""
    return [str(item) for item in values]


def _build_fingerprint_bundle(
    *,
    series_id: str,
    triage_result: TriageResult,
    max_lag: int,
    n_surrogates: int,
    random_state: int,
    geometry_config: AmiInformationGeometryConfig | None,
    fingerprint_config: FingerprintThresholdConfig | None,
    routing_config: RoutingPolicyConfig | None,
) -> FingerprintBundle:
    """Run the geometry-backed fingerprint workflow for one batch item."""
    return run_forecastability_fingerprint(
        series=triage_result.request.series,
        target_name=series_id,
        max_lag=max_lag,
        n_surrogates=n_surrogates,
        random_state=random_state,
        directness_ratio=_directness_ratio(triage_result),
        geometry_config=geometry_config,
        fingerprint_config=fingerprint_config,
        routing_config=routing_config,
    )


def _next_step_from_bundle(
    *,
    series_id: str,
    bundle: FingerprintBundle,
) -> ForecastingNextStepPlan:
    """Map one fingerprint bundle to a deterministic next-step plan."""
    fingerprint = bundle.fingerprint
    recommendation = bundle.recommendation
    families = _stringify_families(recommendation.primary_families)

    if fingerprint.information_structure == "none" or "naive" in recommendation.primary_families:
        return ForecastingNextStepPlan(
            action="baseline_monitoring",
            priority_tier="low",
            recommended_model_families=families,
            why_this_action=(
                "The signal does not stay meaningfully above the surrogate-noise floor, "
                "so a simple baseline is the responsible starting point."
            ),
            validation_focus=(
                "Benchmark naive and seasonal-naive forecasts, monitor drift, and retest "
                "after more data or better segmentation is available."
            ),
            stakeholder_message=(
                f"{series_id} does not justify complex forecasting investment yet; "
                "use a baseline and monitor for change."
            ),
        )

    if (
        fingerprint.information_structure == "periodic"
        and fingerprint.nonlinear_share < 0.30
        and recommendation.confidence_label in {"high", "medium"}
    ):
        return ForecastingNextStepPlan(
            action="seasonal_benchmark",
            priority_tier="high",
            recommended_model_families=families,
            why_this_action=(
                "The informative profile shows repeated peaks with a stable seasonal route."
            ),
            validation_focus=(
                "Benchmark seasonal-naive, harmonic regression, and TBATS-style models with "
                "rolling-origin validation and season-length checks."
            ),
            stakeholder_message=(
                f"{series_id} shows recurring structure that is worth forecasting with "
                "season-aware models first."
            ),
        )

    if (
        fingerprint.information_structure == "monotonic"
        and fingerprint.nonlinear_share < 0.30
        and recommendation.confidence_label in {"high"}
    ):
        return ForecastingNextStepPlan(
            action="linear_benchmark",
            priority_tier="high",
            recommended_model_families=families,
            why_this_action=(
                "Dependence decays in a mostly linear way and the route confidence is high."
            ),
            validation_focus=(
                "Benchmark ARIMA, ETS, and linear state-space models before considering "
                "heavier architectures."
            ),
            stakeholder_message=(
                f"{series_id} is model-ready and should enter a disciplined linear-model "
                "benchmark first."
            ),
        )

    if (
        fingerprint.nonlinear_share >= 0.30
        and recommendation.confidence_label in {"high", "medium"}
    ):
        return ForecastingNextStepPlan(
            action="nonlinear_benchmark",
            priority_tier="high",
            recommended_model_families=families,
            why_this_action=(
                "Corrected AMI remains informative and the nonlinear excess is material."
            ),
            validation_focus=(
                "Run nonlinear candidates against linear and seasonal baselines, and require "
                "clear rolling-origin gains before adopting the richer route."
            ),
            stakeholder_message=(
                f"{series_id} has enough signal complexity to justify nonlinear benchmarks, "
                "but only against strong baselines."
            ),
        )

    return ForecastingNextStepPlan(
        action="hybrid_review",
        priority_tier="review",
        recommended_model_families=families,
        why_this_action=(
            "The route is usable, but mixed structure or caution flags make the choice "
            "sensitive to threshold and validation details."
        ),
        validation_focus=(
            "Compare compact linear/seasonal baselines with the routed family, inspect "
            "caution flags, and confirm the route survives backtesting."
        ),
        stakeholder_message=(
            f"{series_id} is worth review, but the evidence is not clean enough for an "
            "automatic model-family commitment."
        ),
    )


def _blocked_next_step(series_id: str, *, outcome: str) -> ForecastingNextStepPlan:
    """Return a non-modeling next-step plan for blocked or failed items."""
    if outcome == "failed":
        return ForecastingNextStepPlan(
            action="investigate_failure",
            priority_tier="low",
            recommended_model_families=[],
            why_this_action="The batch run failed before a trustworthy modeling decision existed.",
            validation_focus=(
                "Inspect the error, data shape, and configuration first; rerun successfully "
                "before considering any forecasting route."
            ),
            stakeholder_message=(
                f"{series_id} needs investigation before it can enter the forecasting queue."
            ),
        )

    return ForecastingNextStepPlan(
        action="resolve_readiness",
        priority_tier="low",
        recommended_model_families=[],
        why_this_action="Readiness issues blocked a reliable signal assessment.",
        validation_focus=(
            "Fix readiness warnings, especially sample-size or lag-feasibility issues, then rerun "
            "the deterministic workflow."
        ),
        stakeholder_message=(
            f"{series_id} is not ready for model selection yet; data/readiness issues come first."
        ),
    )


def _build_summary(
    items: list[BatchForecastabilityWorkbenchItem],
    *,
    top_n: int,
) -> BatchForecastabilityWorkbenchSummary:
    """Build technical and executive summaries for the batch workbench."""
    model_ready = [item for item in items if item.next_step.priority_tier == "high"]
    baseline_only = [item for item in items if item.next_step.action == "baseline_monitoring"]
    needs_review = [item for item in items if item.next_step.priority_tier == "review"]
    blocked_or_failed = [
        item
        for item in items
        if item.next_step.action in {"resolve_readiness", "investigate_failure"}
    ]

    top_priority_series_ids = [item.series_id for item in model_ready[: max(1, top_n)]]
    baseline_series_ids = [item.series_id for item in baseline_only]
    blocked_or_failed_series_ids = [item.series_id for item in blocked_or_failed]

    if top_priority_series_ids:
        technical_summary = (
            "Batch triage plus geometry-backed routing identified "
            f"{len(model_ready)} model-ready series. "
            f"Highest-priority series: {', '.join(top_priority_series_ids)}."
        )
        executive_summary = (
            f"{len(model_ready)} series are ready for focused forecasting experiments now. "
            f"Start with {', '.join(top_priority_series_ids)}; keep "
            f"{len(baseline_only)} on simple baselines, review "
            f"{len(needs_review)} ambiguous cases, and resolve "
            f"{len(blocked_or_failed)} blocked or failed cases separately."
        )
    else:
        technical_summary = (
            "No series reached the model-ready tier. The current batch should stay in "
            "baseline, review, or remediation mode."
        )
        executive_summary = (
            "No series is ready for heavier forecasting investment yet. Use baselines, "
            "resolve blocked runs, and rerun after remediation."
        )

    return BatchForecastabilityWorkbenchSummary(
        n_series=len(items),
        n_model_ready=len(model_ready),
        n_baseline_only=len(baseline_only),
        n_needs_review=len(needs_review),
        n_blocked_or_failed=len(blocked_or_failed),
        top_priority_series_ids=top_priority_series_ids,
        baseline_series_ids=baseline_series_ids,
        blocked_or_failed_series_ids=blocked_or_failed_series_ids,
        technical_summary=technical_summary,
        executive_summary=executive_summary,
    )


def run_batch_forecastability_workbench(
    request: BatchTriageRequest,
    *,
    triage_runner: Callable[[TriageRequest], TriageResult] = run_triage,
    geometry_config: AmiInformationGeometryConfig | None = None,
    fingerprint_config: FingerprintThresholdConfig | None = None,
    routing_config: RoutingPolicyConfig | None = None,
    top_n: int = 3,
) -> BatchForecastabilityWorkbenchResult:
    """Run batch triage, geometry-backed routing, and next-step planning."""
    execution = run_batch_triage_with_details(request, triage_runner=triage_runner)
    request_items = {item.series_id: item for item in request.items}

    workbench_items: list[BatchForecastabilityWorkbenchItem] = []
    for execution_item in execution.items_with_results:
        triage_item = execution_item.result
        triage_result = execution_item.triage_result

        if triage_result is None or triage_item.outcome != "ok":
            next_step = _blocked_next_step(
                triage_item.series_id,
                outcome=triage_item.outcome,
            )
            workbench_items.append(
                BatchForecastabilityWorkbenchItem(
                    rank=triage_item.rank,
                    series_id=triage_item.series_id,
                    triage_item=triage_item,
                    triage_result=triage_result,
                    fingerprint_bundle=None,
                    next_step=next_step,
                )
            )
            continue

        request_item = request_items[triage_item.series_id]
        max_lag = request_item.max_lag if request_item.max_lag is not None else request.max_lag
        n_surrogates = (
            request_item.n_surrogates
            if request_item.n_surrogates is not None
            else request.n_surrogates
        )
        random_state = (
            request_item.random_state
            if request_item.random_state is not None
            else request.random_state
        )
        bundle = _build_fingerprint_bundle(
            series_id=triage_item.series_id,
            triage_result=triage_result,
            max_lag=max_lag,
            n_surrogates=n_surrogates,
            random_state=random_state,
            geometry_config=geometry_config,
            fingerprint_config=fingerprint_config,
            routing_config=routing_config,
        )
        next_step = _next_step_from_bundle(series_id=triage_item.series_id, bundle=bundle)
        workbench_items.append(
            BatchForecastabilityWorkbenchItem(
                rank=triage_item.rank,
                series_id=triage_item.series_id,
                triage_item=triage_item,
                triage_result=triage_result,
                fingerprint_bundle=bundle,
                next_step=next_step,
            )
        )

    summary = _build_summary(workbench_items, top_n=top_n)
    return BatchForecastabilityWorkbenchResult(
        request=request,
        items=workbench_items,
        summary=summary,
    )
