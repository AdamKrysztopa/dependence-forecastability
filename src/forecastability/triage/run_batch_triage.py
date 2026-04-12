"""Deterministic batch triage orchestration and ranking."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from pydantic import ValidationError

from forecastability.triage.batch_models import (
    BatchFailureRow,
    BatchSeriesRequest,
    BatchSummaryRow,
    BatchTriageExecution,
    BatchTriageExecutionItem,
    BatchTriageItemResult,
    BatchTriageRequest,
    BatchTriageResponse,
)
from forecastability.triage.models import TriageRequest, TriageResult
from forecastability.triage.run_triage import run_triage

_READINESS_RANK: dict[str, int] = {
    "clear": 0,
    "warning": 1,
    "blocked": 2,
    "failed": 3,
}

_FORECASTABILITY_RANK: dict[str, int] = {
    "high": 0,
    "medium": 1,
    "low": 2,
}

_EXOG_USEFULNESS_RANK: dict[str, int] = {
    "high": 0,
    "medium": 1,
    "low": 2,
    "not_applicable": 3,
}

_NEXT_ACTION_RANK: dict[str, int] = {
    "prioritize_exogenous_inclusion": 0,
    "prioritize_structured_models": 1,
    "include_exogenous_with_validation": 2,
    "validate_compact_models": 3,
    "drop_or_retest_exogenous": 4,
    "use_baseline_models": 5,
    "resolve_readiness_warnings": 6,
    "inspect_failure": 7,
}

_EXOG_HIGH_REGIMES: set[str] = {
    "include_exogenous_multivariate",
    "include_exogenous_direct",
}

_EXOG_MEDIUM_REGIMES: set[str] = {
    "include_exogenous_mediated",
    "include_exogenous_seasonal",
    "include_exogenous_selective",
}

_RECOVERABLE_BATCH_ERRORS: tuple[type[BaseException], ...] = (
    ValueError,
    TypeError,
    RuntimeError,
    ArithmeticError,
    ValidationError,
    np.linalg.LinAlgError,
)


def _to_triage_request(
    item: BatchSeriesRequest,
    request: BatchTriageRequest,
) -> TriageRequest:
    """Build a single-series triage request from one batch item."""
    return TriageRequest(
        series=np.asarray(item.series, dtype=np.float64),
        exog=(np.asarray(item.exog, dtype=np.float64) if item.exog is not None else None),
        goal=item.goal,
        max_lag=item.max_lag if item.max_lag is not None else request.max_lag,
        n_surrogates=(item.n_surrogates if item.n_surrogates is not None else request.n_surrogates),
        random_state=(item.random_state if item.random_state is not None else request.random_state),
    )


def _derive_exogenous_usefulness(result: TriageResult) -> str:
    """Map exogenous interpretation outcomes to usefulness buckets."""
    if result.method_plan is None or result.method_plan.route != "exogenous":
        return "not_applicable"

    interpretation = result.interpretation
    if interpretation is None:
        return "not_applicable"

    regime = interpretation.modeling_regime
    if regime in _EXOG_HIGH_REGIMES:
        return "high"
    if regime in _EXOG_MEDIUM_REGIMES:
        return "medium"
    return "low"


def _derive_next_action(
    result: TriageResult,
    *,
    exogenous_usefulness: str,
) -> str:
    """Produce a deterministic next-action label for ranking and routing."""
    if result.blocked:
        return "resolve_readiness_warnings"

    if exogenous_usefulness == "high":
        return "prioritize_exogenous_inclusion"
    if exogenous_usefulness == "medium":
        return "include_exogenous_with_validation"
    if exogenous_usefulness == "low":
        return "drop_or_retest_exogenous"

    recommendation = result.recommendation or ""
    if recommendation.startswith("HIGH"):
        return "prioritize_structured_models"
    if recommendation.startswith("MEDIUM"):
        return "validate_compact_models"
    if recommendation.startswith("LOW"):
        return "use_baseline_models"

    interpretation = result.interpretation
    if interpretation is None:
        return "resolve_readiness_warnings"
    if interpretation.forecastability_class == "high":
        return "prioritize_structured_models"
    if interpretation.forecastability_class == "medium":
        return "validate_compact_models"
    return "use_baseline_models"


def _build_item_result(
    item: BatchSeriesRequest,
    result: TriageResult,
) -> BatchTriageItemResult:
    """Build one ranked-item payload from a successful triage execution."""
    interpretation = result.interpretation
    exogenous_usefulness = _derive_exogenous_usefulness(result)

    forecastability_profile = None
    directness_ratio = None
    forecastability_class = None
    directness_class = None
    if interpretation is not None:
        forecastability_class = interpretation.forecastability_class
        directness_class = interpretation.directness_class
        forecastability_profile = (
            f"{interpretation.forecastability_class}:"
            f"{interpretation.directness_class}:"
            f"{interpretation.modeling_regime}"
        )
        directness_ratio = interpretation.diagnostics.directness_ratio

    warning_codes = [warning.code for warning in result.readiness.warnings]
    outcome = "blocked" if result.blocked else "ok"

    spectral_predictability = None
    permutation_entropy = None
    complexity_band_label = None
    if result.complexity_band is not None:
        spectral_predictability = round(1.0 - result.complexity_band.spectral_entropy, 6)
        permutation_entropy = result.complexity_band.permutation_entropy
        complexity_band_label = result.complexity_band.complexity_band

    return BatchTriageItemResult(
        series_id=item.series_id,
        outcome=outcome,
        blocked=result.blocked,
        readiness_status=result.readiness.status.value,
        warning_codes=warning_codes,
        forecastability_profile=forecastability_profile,
        forecastability_class=forecastability_class,
        directness_class=directness_class,
        directness_ratio=directness_ratio,
        exogenous_usefulness=exogenous_usefulness,
        recommended_next_action=_derive_next_action(
            result,
            exogenous_usefulness=exogenous_usefulness,
        ),
        recommendation=result.recommendation,
        spectral_predictability=spectral_predictability,
        permutation_entropy=permutation_entropy,
        complexity_band_label=complexity_band_label,
    )


def _build_failure_item(item: BatchSeriesRequest, error: BaseException) -> BatchTriageItemResult:
    """Build one ranked-item payload for a failed series execution."""
    return BatchTriageItemResult(
        series_id=item.series_id,
        outcome="failed",
        blocked=True,
        readiness_status="failed",
        warning_codes=[],
        exogenous_usefulness="not_applicable",
        recommended_next_action="inspect_failure",
        error_code=type(error).__name__,
        error_message=str(error),
    )


def _ranking_sort_key(item: BatchTriageItemResult) -> tuple[int, int, float, int, int, str]:
    """Create a deterministic sort key for batch ranking."""
    readiness_rank = _READINESS_RANK.get(item.readiness_status, 99)
    forecastability_rank = _FORECASTABILITY_RANK.get(item.forecastability_class or "", 99)
    directness_ratio = item.directness_ratio if item.directness_ratio is not None else -1.0
    exog_rank = _EXOG_USEFULNESS_RANK.get(item.exogenous_usefulness, 99)
    action_rank = _NEXT_ACTION_RANK.get(item.recommended_next_action, 99)
    return (
        readiness_rank,
        forecastability_rank,
        -directness_ratio,
        exog_rank,
        action_rank,
        item.series_id,
    )


def rank_batch_items(items: list[BatchTriageItemResult]) -> list[BatchTriageItemResult]:
    """Rank batch items by readiness, profile, directness, exogenous value, and action.

    Args:
        items: Unranked item results.

    Returns:
        New list sorted by deterministic policy and annotated with 1-based rank.
    """
    ordered = sorted(items, key=_ranking_sort_key)
    return [item.model_copy(update={"rank": index + 1}) for index, item in enumerate(ordered)]


def _to_summary_row(item: BatchTriageItemResult) -> BatchSummaryRow:
    """Convert an item result to a flat summary-table row."""
    return BatchSummaryRow(
        rank=item.rank,
        series_id=item.series_id,
        outcome=item.outcome,
        readiness_status=item.readiness_status,
        warning_codes="|".join(item.warning_codes),
        forecastability_profile=item.forecastability_profile,
        forecastability_class=item.forecastability_class,
        directness_class=item.directness_class,
        directness_ratio=item.directness_ratio,
        exogenous_usefulness=item.exogenous_usefulness,
        recommended_next_action=item.recommended_next_action,
        recommendation=item.recommendation,
        error_code=item.error_code,
        error_message=item.error_message,
        spectral_predictability=item.spectral_predictability,
        permutation_entropy=item.permutation_entropy,
        complexity_band_label=item.complexity_band_label,
    )


def _execute_batch_items(
    request: BatchTriageRequest,
    *,
    triage_runner: Callable[[TriageRequest], TriageResult],
) -> list[BatchTriageExecutionItem]:
    """Execute all batch items once and retain detailed triage results.

    Args:
        request: Batch request with per-series items.
        triage_runner: Injectable single-series triage callable.

    Returns:
        Unranked execution items with one-pass triage outputs.
    """
    items: list[BatchTriageExecutionItem] = []
    for item in request.items:
        try:
            triage_request = _to_triage_request(item, request)
            triage_result = triage_runner(triage_request)
            items.append(
                BatchTriageExecutionItem(
                    result=_build_item_result(item, triage_result),
                    triage_result=triage_result,
                )
            )
        except _RECOVERABLE_BATCH_ERRORS as error:
            items.append(
                BatchTriageExecutionItem(
                    result=_build_failure_item(item, error),
                    triage_result=None,
                )
            )
    return items


def _rank_execution_items(items: list[BatchTriageExecutionItem]) -> list[BatchTriageExecutionItem]:
    """Apply deterministic ranking to execution items and assign 1-based rank."""
    ordered = sorted(items, key=lambda item: _ranking_sort_key(item.result))
    return [
        item.model_copy(update={"result": item.result.model_copy(update={"rank": index + 1})})
        for index, item in enumerate(ordered)
    ]


def _build_response(items: list[BatchTriageExecutionItem]) -> BatchTriageResponse:
    """Build stable response tables from ranked execution items."""
    ranked_items = [item.result for item in items]
    summary_table = [_to_summary_row(item) for item in ranked_items]
    failure_table = [
        BatchFailureRow(
            series_id=item.series_id,
            error_code=item.error_code or "UnknownError",
            error_message=item.error_message or "No error message provided",
        )
        for item in ranked_items
        if item.outcome == "failed"
    ]

    return BatchTriageResponse(
        items=ranked_items,
        summary_table=summary_table,
        failure_table=failure_table,
    )


def run_batch_triage_with_details(
    request: BatchTriageRequest,
    *,
    triage_runner: Callable[[TriageRequest], TriageResult] = run_triage,
) -> BatchTriageExecution:
    """Run batch triage and return both stable response and detailed outputs.

    Statistical safety note:
        This use case delegates each item to ``run_triage()``, which computes AMI/pAMI
        diagnostics on the provided series only and preserves existing train-only
        conventions in downstream evaluation components.

    Args:
        request: Batch triage request with one or more series items.
        triage_runner: Injectable single-series triage callable for testing.

    Returns:
        Batch execution payload with the stable ranked response and per-item
        detailed triage outputs.
    """
    execution_items = _execute_batch_items(request, triage_runner=triage_runner)
    ranked_items = _rank_execution_items(execution_items)
    response = _build_response(ranked_items)

    return BatchTriageExecution(response=response, items_with_results=ranked_items)


def run_batch_triage(
    request: BatchTriageRequest,
    *,
    triage_runner: Callable[[TriageRequest], TriageResult] = run_triage,
) -> BatchTriageResponse:
    """Run deterministic triage for multiple series with per-item failure isolation.

    Statistical safety note:
        This use case delegates each item to ``run_triage()``, which computes AMI/pAMI
        diagnostics on the provided series only and preserves existing train-only
        conventions in downstream evaluation components.

    Args:
        request: Batch triage request with one or more series items.
        triage_runner: Injectable single-series triage callable for testing.

    Returns:
        Ranked batch response containing per-item outcomes plus summary and
        failure tables.
    """
    execution = run_batch_triage_with_details(request, triage_runner=triage_runner)
    return execution.response
