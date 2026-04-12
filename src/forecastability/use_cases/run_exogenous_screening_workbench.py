"""Use-case: target-plus-many-drivers exogenous screening workbench."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Literal

import numpy as np

from forecastability.config import (
    ExogenousLagWindowConfig,
    ExogenousScreeningRecommendationConfig,
    ExogenousScreeningWorkbenchConfig,
)
from forecastability.types import (
    ExogenousBenchmarkResult,
    ExogenousDriverSummary,
    ExogenousHorizonUsefulnessRow,
    ExogenousLagWindowSummaryRow,
    ExogenousScreeningWorkbenchResult,
)
from forecastability.use_cases.run_exogenous_rolling_origin_evaluation import (
    run_exogenous_rolling_origin_evaluation,
)
from forecastability.validation import validate_time_series

DRIVER_SUMMARY_TABLE_COLUMNS: tuple[str, ...] = (
    "overall_rank",
    "driver_name",
    "recommendation",
    "pruned",
    "prune_reason",
    "mean_usefulness_score",
    "peak_usefulness_score",
    "top_horizon",
    "top_horizon_usefulness_score",
    "n_horizons_above_floor",
    "warning_horizon_count",
)

HORIZON_USEFULNESS_TABLE_COLUMNS: tuple[str, ...] = (
    "horizon",
    "horizon_rank",
    "driver_name",
    "raw_cross_mi",
    "conditioned_cross_mi",
    "directness_ratio",
    "usefulness_score",
)

LAG_WINDOW_SUMMARY_TABLE_COLUMNS: tuple[str, ...] = (
    "driver_name",
    "window_name",
    "start_horizon",
    "end_horizon",
    "n_horizons_covered",
    "mean_usefulness_score",
    "peak_usefulness_score",
)

_Recommendation = Literal["keep", "review", "reject"]


def _compute_usefulness_score(*, conditioned_cross_mi: float, directness_ratio: float) -> float:
    """Compute one horizon-specific usefulness score.

    The score favors candidate drivers with high conditioned cross-MI and
    down-weights horizons where directness is weak.

    Args:
        conditioned_cross_mi: Conditioned pCrossAMI value at one horizon.
        directness_ratio: Conditioned/raw ratio at the same horizon.

    Returns:
        Non-negative usefulness score.
    """
    clipped_directness = float(np.clip(directness_ratio, 0.0, 1.0))
    return float(max(conditioned_cross_mi, 0.0) * clipped_directness)


def _validate_driver_panel(
    *,
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    """Validate and normalize a target-plus-many-drivers panel.

    Args:
        target: Validated target series.
        drivers: Driver name to series mapping.

    Returns:
        Deterministically ordered and validated driver mapping.

    Raises:
        ValueError: If panel shape assumptions are violated.
    """
    if len(drivers) == 0:
        raise ValueError("drivers must contain at least one candidate exogenous series")

    validated: dict[str, np.ndarray] = {}
    for driver_name in sorted(drivers):
        if not driver_name.strip():
            raise ValueError("driver names must be non-empty")
        series = validate_time_series(drivers[driver_name], min_length=target.size)
        if series.size != target.size:
            raise ValueError(
                "each driver series must exactly match target length: "
                f"{driver_name}={series.size}, target={target.size}"
            )
        validated[driver_name] = series
    return validated


def _rank_horizon_usefulness_rows(
    *,
    evaluations: dict[str, ExogenousBenchmarkResult],
    horizons: list[int],
) -> list[ExogenousHorizonUsefulnessRow]:
    """Build per-horizon driver rankings by usefulness score."""
    rows_by_horizon: dict[int, list[tuple[str, float, float, float, float]]] = {
        horizon: [] for horizon in horizons
    }

    for driver_name, result in evaluations.items():
        for horizon in horizons:
            if horizon not in result.horizons:
                continue
            raw_cross_mi = float(result.raw_cross_mi_by_horizon[horizon])
            conditioned_cross_mi = float(result.conditioned_cross_mi_by_horizon[horizon])
            directness_ratio = float(result.directness_ratio_by_horizon[horizon])
            usefulness_score = _compute_usefulness_score(
                conditioned_cross_mi=conditioned_cross_mi,
                directness_ratio=directness_ratio,
            )
            rows_by_horizon[horizon].append(
                (
                    driver_name,
                    raw_cross_mi,
                    conditioned_cross_mi,
                    directness_ratio,
                    usefulness_score,
                )
            )

    ranked_rows: list[ExogenousHorizonUsefulnessRow] = []
    for horizon in horizons:
        ordered = sorted(rows_by_horizon[horizon], key=lambda row: (-row[4], row[0]))
        for rank, row in enumerate(ordered, start=1):
            ranked_rows.append(
                ExogenousHorizonUsefulnessRow(
                    driver_name=row[0],
                    horizon=horizon,
                    raw_cross_mi=row[1],
                    conditioned_cross_mi=row[2],
                    directness_ratio=row[3],
                    usefulness_score=row[4],
                    horizon_rank=rank,
                )
            )

    return ranked_rows


def _apply_pruning(
    *,
    mean_usefulness_score: float,
    peak_usefulness_score: float,
    n_horizons_above_floor: int,
    config: ExogenousScreeningWorkbenchConfig,
) -> tuple[bool, str | None]:
    """Apply optional weak-driver pruning heuristics."""
    pruning = config.pruning
    if not pruning.enabled:
        return False, None

    reasons: list[str] = []
    if mean_usefulness_score < pruning.min_mean_usefulness:
        reasons.append("mean_usefulness_below_threshold")
    if peak_usefulness_score < pruning.min_peak_usefulness:
        reasons.append("peak_usefulness_below_threshold")
    if n_horizons_above_floor < pruning.min_horizons_above_floor:
        reasons.append("insufficient_horizons_above_floor")

    if not reasons:
        return False, None
    return True, ",".join(reasons)


def map_workbench_recommendation(
    *,
    mean_usefulness_score: float,
    peak_usefulness_score: float,
    pruned: bool,
    recommendation_config: ExogenousScreeningRecommendationConfig,
) -> _Recommendation:
    """Map driver usefulness diagnostics to keep/review/reject labels."""
    if pruned:
        return "reject"
    if (
        mean_usefulness_score >= recommendation_config.keep_min_mean_usefulness
        and peak_usefulness_score >= recommendation_config.keep_min_peak_usefulness
    ):
        return "keep"
    if (
        mean_usefulness_score >= recommendation_config.review_min_mean_usefulness
        or peak_usefulness_score >= recommendation_config.review_min_peak_usefulness
    ):
        return "review"
    return "reject"


def _build_driver_summaries(
    *,
    evaluations: dict[str, ExogenousBenchmarkResult],
    horizon_rows: list[ExogenousHorizonUsefulnessRow],
    config: ExogenousScreeningWorkbenchConfig,
) -> list[ExogenousDriverSummary]:
    """Build ranked one-row-per-driver screening summaries."""
    rows_by_driver: dict[str, list[ExogenousHorizonUsefulnessRow]] = defaultdict(list)
    for row in horizon_rows:
        rows_by_driver[row.driver_name].append(row)

    summaries: list[ExogenousDriverSummary] = []
    for driver_name in sorted(evaluations):
        driver_rows = rows_by_driver.get(driver_name, [])
        scores = [row.usefulness_score for row in driver_rows]

        mean_usefulness_score = float(np.mean(scores)) if scores else 0.0
        peak_usefulness_score = float(np.max(scores)) if scores else 0.0

        top_row = max(
            driver_rows,
            key=lambda row: (row.usefulness_score, -row.horizon),
            default=None,
        )
        top_horizon = top_row.horizon if top_row is not None else None
        top_horizon_usefulness_score = top_row.usefulness_score if top_row is not None else None

        n_horizons_above_floor = sum(
            score >= config.pruning.horizon_usefulness_floor for score in scores
        )

        pruned, prune_reason = _apply_pruning(
            mean_usefulness_score=mean_usefulness_score,
            peak_usefulness_score=peak_usefulness_score,
            n_horizons_above_floor=n_horizons_above_floor,
            config=config,
        )
        recommendation = map_workbench_recommendation(
            mean_usefulness_score=mean_usefulness_score,
            peak_usefulness_score=peak_usefulness_score,
            pruned=pruned,
            recommendation_config=config.recommendation,
        )

        summaries.append(
            ExogenousDriverSummary(
                overall_rank=0,
                driver_name=driver_name,
                recommendation=recommendation,
                pruned=pruned,
                prune_reason=prune_reason,
                mean_usefulness_score=mean_usefulness_score,
                peak_usefulness_score=peak_usefulness_score,
                top_horizon=top_horizon,
                top_horizon_usefulness_score=top_horizon_usefulness_score,
                n_horizons_above_floor=n_horizons_above_floor,
                warning_horizon_count=len(evaluations[driver_name].warning_horizons),
            )
        )

    recommendation_rank: dict[_Recommendation, int] = {
        "keep": 0,
        "review": 1,
        "reject": 2,
    }
    ordered = sorted(
        summaries,
        key=lambda row: (
            recommendation_rank[row.recommendation],
            -row.mean_usefulness_score,
            -row.peak_usefulness_score,
            row.driver_name,
        ),
    )
    return [
        row.model_copy(update={"overall_rank": rank}) for rank, row in enumerate(ordered, start=1)
    ]


def _build_lag_window_summaries(
    *,
    horizon_rows: list[ExogenousHorizonUsefulnessRow],
    lag_windows: list[ExogenousLagWindowConfig],
) -> list[ExogenousLagWindowSummaryRow]:
    """Build lag-window relevance summaries for each driver."""
    rows_by_driver: dict[str, list[ExogenousHorizonUsefulnessRow]] = defaultdict(list)
    for row in horizon_rows:
        rows_by_driver[row.driver_name].append(row)

    summaries: list[ExogenousLagWindowSummaryRow] = []
    for driver_name in sorted(rows_by_driver):
        for window in lag_windows:
            window_scores = [
                row.usefulness_score
                for row in rows_by_driver[driver_name]
                if window.start_horizon <= row.horizon <= window.end_horizon
            ]
            mean_score = float(np.mean(window_scores)) if window_scores else 0.0
            peak_score = float(np.max(window_scores)) if window_scores else 0.0
            summaries.append(
                ExogenousLagWindowSummaryRow(
                    driver_name=driver_name,
                    window_name=window.name,
                    start_horizon=window.start_horizon,
                    end_horizon=window.end_horizon,
                    n_horizons_covered=len(window_scores),
                    mean_usefulness_score=mean_score,
                    peak_usefulness_score=peak_score,
                )
            )

    return summaries


def run_exogenous_screening_workbench(
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
    *,
    target_name: str,
    config: ExogenousScreeningWorkbenchConfig,
    pair_evaluator: Callable[
        ..., ExogenousBenchmarkResult
    ] = run_exogenous_rolling_origin_evaluation,
) -> ExogenousScreeningWorkbenchResult:
    """Run exogenous screening for one target against many candidate drivers.

    Statistical safety note:
        This use case reuses ``run_exogenous_rolling_origin_evaluation`` for each
        target-driver pair, so cross-dependence diagnostics are computed on
        train windows only at each rolling origin.

    Args:
        target: Target series.
        drivers: Candidate driver series keyed by driver name.
        target_name: Stable target identifier used in output tables.
        config: Workbench configuration.
        pair_evaluator: Injectable pairwise evaluator for deterministic tests.

    Returns:
        Typed screening result with horizon rankings, lag-window summaries,
        and keep/review/reject recommendations.
    """
    min_length = max(config.horizons) + config.min_pairs_partial + 1
    validated_target = validate_time_series(target, min_length=min_length)
    validated_drivers = _validate_driver_panel(target=validated_target, drivers=drivers)

    evaluations: dict[str, ExogenousBenchmarkResult] = {}
    for index, driver_name in enumerate(sorted(validated_drivers)):
        evaluations[driver_name] = pair_evaluator(
            validated_target,
            validated_drivers[driver_name],
            case_id=f"{target_name}_{driver_name}",
            target_name=target_name,
            exog_name=driver_name,
            horizons=config.horizons,
            n_origins=config.n_origins,
            random_state=config.random_state + index,
            n_surrogates=config.n_surrogates,
            min_pairs_raw=config.min_pairs_raw,
            min_pairs_partial=config.min_pairs_partial,
            analysis_scope=config.analysis_scope,
            project_extension=config.project_extension,
        )

    horizon_rows = _rank_horizon_usefulness_rows(
        evaluations=evaluations,
        horizons=config.horizons,
    )
    lag_window_summaries = _build_lag_window_summaries(
        horizon_rows=horizon_rows,
        lag_windows=config.lag_windows,
    )
    driver_summaries = _build_driver_summaries(
        evaluations=evaluations,
        horizon_rows=horizon_rows,
        config=config,
    )

    return ExogenousScreeningWorkbenchResult(
        target_name=target_name,
        horizons=config.horizons,
        driver_summaries=driver_summaries,
        horizon_usefulness_rows=horizon_rows,
        lag_window_summaries=lag_window_summaries,
        metadata={
            "purpose": config.purpose,
            "analysis_scope": config.analysis_scope,
            "project_extension": int(config.project_extension),
            "n_origins": config.n_origins,
            "n_surrogates": config.n_surrogates,
            "n_drivers": len(validated_drivers),
            "n_pruned": sum(1 for row in driver_summaries if row.pruned),
        },
    )


def driver_summary_table_rows(
    result: ExogenousScreeningWorkbenchResult,
) -> list[dict[str, object]]:
    """Return one-row-per-driver payloads for CSV/JSON export."""
    return [summary.model_dump(mode="json") for summary in result.driver_summaries]


def horizon_usefulness_table_rows(
    result: ExogenousScreeningWorkbenchResult,
) -> list[dict[str, object]]:
    """Return horizon ranking payloads for CSV/JSON export."""
    return [row.model_dump(mode="json") for row in result.horizon_usefulness_rows]


def lag_window_summary_table_rows(
    result: ExogenousScreeningWorkbenchResult,
) -> list[dict[str, object]]:
    """Return lag-window summary payloads for CSV/JSON export."""
    return [row.model_dump(mode="json") for row in result.lag_window_summaries]


def build_workbench_markdown(result: ExogenousScreeningWorkbenchResult) -> str:
    """Render a compact markdown summary for exogenous screening decisions."""
    lines: list[str] = [
        f"# Exogenous Screening Workbench — {result.target_name}",
        "",
        (
            "This workbench ranks candidate drivers by horizon-specific usefulness "
            "and maps each driver to keep/review/reject."
        ),
        "",
        "## Driver Recommendations",
        "",
        (
            "| Rank | Driver | Recommendation | Mean usefulness | "
            "Peak usefulness | Top horizon | Pruned |"
        ),
        "|---:|---|---|---:|---:|---:|---|",
    ]

    for summary in result.driver_summaries:
        line_template = (
            "| {rank} | {driver} | {recommendation} | {mean:.4f} | "
            "{peak:.4f} | {top_horizon} | {pruned} |"
        )
        lines.append(
            line_template.format(
                rank=summary.overall_rank,
                driver=summary.driver_name,
                recommendation=summary.recommendation,
                mean=summary.mean_usefulness_score,
                peak=summary.peak_usefulness_score,
                top_horizon=(summary.top_horizon if summary.top_horizon is not None else "-"),
                pruned=(summary.prune_reason if summary.prune_reason is not None else "no"),
            )
        )

    return "\n".join(lines)
