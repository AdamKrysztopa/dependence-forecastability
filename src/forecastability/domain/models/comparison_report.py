"""Pure domain models for multi-series comparison reporting.

This module contains only frozen Pydantic models, column-name constants, and
pure-Python / numpy helpers that carry zero infrastructure dependencies.

Rendering (matplotlib) lives in ``forecastability.reporting.comparison_report_plots``.
The coordinator that assembles reports lives in
``forecastability.triage.comparison_report`` (deprecated shim) and will
eventually move to a use-case module.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from forecastability.domain.models.batch_models import BatchSummaryRow

SERIES_COMPARISON_TABLE_COLUMNS: tuple[str, ...] = (
    "rank",
    "series_id",
    "outcome",
    "readiness_status",
    "forecastability_class",
    "directness_class",
    "ami_auc",
    "pami_auc",
    "directness_ratio",
    "ami_significance_coverage",
    "pami_significance_coverage",
    "ami_dropoff_index",
    "pami_dropoff_index",
    "recommended_next_action",
    "deserves_deeper_modeling",
    "priority_score",
)

HORIZON_DROPOFF_TABLE_COLUMNS: tuple[str, ...] = (
    "series_id",
    "horizon",
    "ami_normalized",
    "pami_normalized",
    "ami_dropoff_from_h1",
    "pami_dropoff_from_h1",
)

RECOMMENDATION_TABLE_COLUMNS: tuple[str, ...] = (
    "priority_rank",
    "series_id",
    "deserves_deeper_modeling",
    "priority_score",
    "rationale",
    "recommended_next_action",
)


class SeriesComparisonRow(BaseModel):
    """Standardized per-series metrics for comparison reporting."""

    model_config = ConfigDict(frozen=True)

    rank: int | None
    series_id: str
    outcome: str
    readiness_status: str
    forecastability_class: str | None = None
    directness_class: str | None = None
    ami_auc: float | None = None
    pami_auc: float | None = None
    directness_ratio: float | None = None
    ami_significance_coverage: float | None = None
    pami_significance_coverage: float | None = None
    ami_dropoff_index: float | None = None
    pami_dropoff_index: float | None = None
    recommended_next_action: str
    deserves_deeper_modeling: bool
    priority_score: float


class HorizonDropoffRow(BaseModel):
    """Horizon-level normalized decay profile for one series."""

    model_config = ConfigDict(frozen=True)

    series_id: str
    horizon: int
    ami_normalized: float
    pami_normalized: float
    ami_dropoff_from_h1: float
    pami_dropoff_from_h1: float


class SeriesRecommendationRow(BaseModel):
    """Recommendation row used in the comparison summary output."""

    model_config = ConfigDict(frozen=True)

    priority_rank: int | None = None
    series_id: str
    deserves_deeper_modeling: bool
    priority_score: float
    rationale: str
    recommended_next_action: str


class ComparisonSummary(BaseModel):
    """Top-level recommendation summary for engineering review."""

    model_config = ConfigDict(frozen=True)

    n_series_screened: int
    n_series_failed: int
    n_series_recommended: int
    recommended_series_ids: list[str] = Field(default_factory=list)
    summary_markdown: str


class MultiSeriesComparisonReport(BaseModel):
    """In-memory representation of multi-series comparison report artifacts."""

    model_config = ConfigDict(frozen=True)

    batch_summary_table: list[BatchSummaryRow]
    series_table: list[SeriesComparisonRow]
    horizon_dropoff_table: list[HorizonDropoffRow]
    recommendation_table: list[SeriesRecommendationRow]
    summary: ComparisonSummary

    def series_table_frame(self) -> pd.DataFrame:
        """Return the standardized per-series comparison table."""
        rows = [row.model_dump(mode="json") for row in self.series_table]
        return pd.DataFrame(rows, columns=list(SERIES_COMPARISON_TABLE_COLUMNS))

    def horizon_dropoff_frame(self) -> pd.DataFrame:
        """Return the standardized horizon drop-off table."""
        rows = [row.model_dump(mode="json") for row in self.horizon_dropoff_table]
        return pd.DataFrame(rows, columns=list(HORIZON_DROPOFF_TABLE_COLUMNS))

    def recommendation_frame(self) -> pd.DataFrame:
        """Return the standardized recommendation table."""
        rows = [row.model_dump(mode="json") for row in self.recommendation_table]
        return pd.DataFrame(rows, columns=list(RECOMMENDATION_TABLE_COLUMNS))


class ComparisonArtifactPaths(BaseModel):
    """Filesystem paths for generated comparison artifacts."""

    model_config = ConfigDict(frozen=True)

    series_table_csv: Path
    horizon_dropoff_csv: Path
    recommendations_csv: Path
    auc_plot_png: Path
    directness_plot_png: Path
    significance_plot_png: Path
    horizon_dropoff_plot_png: Path
    report_markdown: Path


# ---------------------------------------------------------------------------
# Pure-Python / numpy helper functions (no infrastructure dependencies)
# ---------------------------------------------------------------------------


def _compute_auc(values: np.ndarray) -> float:
    """Compute trapezoidal AUC for one horizon curve.

    Args:
        values: 1-D array of horizon-indexed values.

    Returns:
        Scalar AUC estimate, or 0.0 for an empty array.
    """
    if values.size == 0:
        return 0.0
    return float(np.trapezoid(values))


def _compute_significance_coverage(
    significant_lags: np.ndarray,
    *,
    n_horizons: int,
    compute_surrogates: bool,
) -> float | None:
    """Compute fraction of horizons that exceed surrogate significance bands.

    Args:
        significant_lags: Array of lag indices that exceeded the surrogate band.
        n_horizons: Total number of horizons evaluated.
        compute_surrogates: Whether surrogate bands were requested.

    Returns:
        Coverage fraction in [0, 1], or ``None`` when surrogates were not computed.
    """
    if not compute_surrogates:
        return None
    if n_horizons <= 0:
        return None
    return float(significant_lags.size / n_horizons)


def _compute_dropoff_index(values: np.ndarray) -> float:
    """Compute early-to-late drop-off index in [roughly] increasing decay scale.

    Args:
        values: 1-D horizon curve.

    Returns:
        Scalar drop-off index (0 = flat, approaching 1 = full collapse).
    """
    if values.size == 0:
        return 0.0
    window = max(1, int(np.ceil(values.size * 0.25)))
    head = float(np.mean(values[:window]))
    tail = float(np.mean(values[-window:]))
    return float((head - tail) / max(abs(head), 1e-12))


def _priority_score(row: SeriesComparisonRow) -> float:
    """Score one series for deeper-modeling priority ranking.

    Args:
        row: Comparison row containing forecastability metrics.

    Returns:
        Non-negative priority score; 0.0 for non-analyzable series.
    """
    if row.outcome != "ok":
        return 0.0

    forecastability_component = {
        "high": 1.00,
        "medium": 0.60,
        "low": 0.20,
    }.get(row.forecastability_class or "", 0.0)
    directness_component = min(max(row.directness_ratio or 0.0, 0.0), 1.0)
    pami_auc_component = float(np.log1p(max(row.pami_auc or 0.0, 0.0)))
    coverage_component = (
        float(row.ami_significance_coverage or 0.0) + float(row.pami_significance_coverage or 0.0)
    ) * 0.50
    dropoff_penalty = max(row.pami_dropoff_index or 0.0, 0.0) * 0.40

    return round(
        forecastability_component
        + directness_component
        + pami_auc_component
        + coverage_component
        - dropoff_penalty,
        6,
    )


def _deserves_deeper_modeling(row: SeriesComparisonRow) -> bool:
    """Decide whether a series is a candidate for deeper modeling.

    Args:
        row: Comparison row for one series.

    Returns:
        ``True`` when the series passes all deeper-modeling thresholds.
    """
    if row.outcome != "ok":
        return False
    if row.forecastability_class not in {"high", "medium"}:
        return False
    if row.directness_ratio is None or row.directness_ratio < 0.20:
        return False
    if row.pami_auc is None or row.pami_auc <= 0.0:
        return False

    # Very steep pAMI collapse suggests short-lived direct effects only.
    if row.forecastability_class == "medium" and (row.pami_dropoff_index or 0.0) > 0.95:
        return False

    return True


def _recommendation_rationale(row: SeriesComparisonRow) -> str:
    """Produce a short recommendation rationale for one series.

    Args:
        row: Comparison row for one series.

    Returns:
        Single-sentence rationale string.
    """
    if row.outcome != "ok":
        return "Series is not analyzable in batch output; resolve failure/readiness first."

    if row.forecastability_class == "high" and (row.directness_ratio or 0.0) >= 0.50:
        return "High forecastability with strong direct dependence retained after conditioning."
    if row.forecastability_class == "high":
        return (
            "High forecastability with mediated structure; prioritize compact "
            "but structured models."
        )
    if row.forecastability_class == "medium" and (row.directness_ratio or 0.0) >= 0.50:
        return "Medium forecastability with meaningful direct dependence at key horizons."
    if row.forecastability_class == "medium":
        return (
            "Medium forecastability but weaker directness; start with "
            "regularized/seasonal baselines."
        )

    return "Low forecastability profile; deeper models are unlikely to outperform robust baselines."


def _normalized_curve(values: np.ndarray) -> np.ndarray:
    """Normalize one curve by its first-horizon value.

    Args:
        values: 1-D horizon curve.

    Returns:
        Curve divided by the absolute first-horizon value (or 1e-12 if near zero).
    """
    if values.size == 0:
        return np.array([], dtype=float)
    baseline = float(values[0])
    return values / max(abs(baseline), 1e-12)


def _build_dropoff_rows(
    series_id: str,
    raw: np.ndarray,
    partial: np.ndarray,
) -> list[HorizonDropoffRow]:
    """Build horizon-level normalized drop-off rows for one series.

    Args:
        series_id: Identifier for the series.
        raw: AMI curve array.
        partial: pAMI curve array.

    Returns:
        List of one ``HorizonDropoffRow`` per horizon index.
    """
    n_horizons = int(min(raw.size, partial.size))
    if n_horizons == 0:
        return []

    raw_norm = _normalized_curve(raw[:n_horizons])
    partial_norm = _normalized_curve(partial[:n_horizons])

    rows: list[HorizonDropoffRow] = []
    for idx in range(n_horizons):
        rows.append(
            HorizonDropoffRow(
                series_id=series_id,
                horizon=idx + 1,
                ami_normalized=float(raw_norm[idx]),
                pami_normalized=float(partial_norm[idx]),
                ami_dropoff_from_h1=float(1.0 - raw_norm[idx]),
                pami_dropoff_from_h1=float(1.0 - partial_norm[idx]),
            )
        )
    return rows


def _build_series_row(item: object) -> SeriesComparisonRow:
    """Build one standardized comparison row from one batch execution item.

    Args:
        item: A ``BatchTriageExecutionItem`` (typed as ``object`` to avoid a
            circular import from the coordinator layer into domain).

    Returns:
        Fully-populated ``SeriesComparisonRow``.
    """
    # Import here to keep the module importable without pulling in all domain
    # batch internals at module level (avoids circular-dependency at domain level).
    from forecastability.domain.models.batch_models import (  # noqa: PLC0415
        BatchTriageExecutionItem,
    )

    execution_item: BatchTriageExecutionItem = item  # type: ignore[assignment]
    result = execution_item.result
    triage_result = execution_item.triage_result

    if triage_result is None or triage_result.analyze_result is None:
        base_row = SeriesComparisonRow(
            rank=result.rank,
            series_id=result.series_id,
            outcome=result.outcome,
            readiness_status=result.readiness_status,
            forecastability_class=result.forecastability_class,
            directness_class=result.directness_class,
            recommended_next_action=result.recommended_next_action,
            deserves_deeper_modeling=False,
            priority_score=0.0,
        )
        return base_row

    analyze_result = triage_result.analyze_result
    raw = analyze_result.raw
    partial = analyze_result.partial

    ami_auc = _compute_auc(raw)
    pami_auc = _compute_auc(partial)
    directness_ratio = float(pami_auc / max(ami_auc, 1e-12))

    compute_surrogates = bool(
        triage_result.method_plan is not None and triage_result.method_plan.compute_surrogates
    )
    ami_significance_coverage = _compute_significance_coverage(
        analyze_result.sig_raw_lags,
        n_horizons=int(raw.size),
        compute_surrogates=compute_surrogates,
    )
    pami_significance_coverage = _compute_significance_coverage(
        analyze_result.sig_partial_lags,
        n_horizons=int(partial.size),
        compute_surrogates=compute_surrogates,
    )

    interpretation = triage_result.interpretation
    row = SeriesComparisonRow(
        rank=result.rank,
        series_id=result.series_id,
        outcome=result.outcome,
        readiness_status=result.readiness_status,
        forecastability_class=(
            interpretation.forecastability_class
            if interpretation is not None
            else result.forecastability_class
        ),
        directness_class=(
            interpretation.directness_class
            if interpretation is not None
            else result.directness_class
        ),
        ami_auc=ami_auc,
        pami_auc=pami_auc,
        directness_ratio=directness_ratio,
        ami_significance_coverage=ami_significance_coverage,
        pami_significance_coverage=pami_significance_coverage,
        ami_dropoff_index=_compute_dropoff_index(raw),
        pami_dropoff_index=_compute_dropoff_index(partial),
        recommended_next_action=result.recommended_next_action,
        deserves_deeper_modeling=False,
        priority_score=0.0,
    )
    score = _priority_score(row)
    deserves = _deserves_deeper_modeling(row)
    return row.model_copy(update={"priority_score": score, "deserves_deeper_modeling": deserves})


def _build_recommendation_table(
    rows: list[SeriesComparisonRow],
    *,
    top_n: int,
) -> list[SeriesRecommendationRow]:
    """Build recommendation rows and assign priority rank for selected series.

    Args:
        rows: All per-series comparison rows.
        top_n: Maximum number of series to surface in the recommendation.

    Returns:
        Ordered list of ``SeriesRecommendationRow`` instances.
    """
    eligible = [row for row in rows if row.deserves_deeper_modeling]
    ordered = sorted(
        eligible,
        key=lambda row: (
            -row.priority_score,
            -(row.directness_ratio or 0.0),
            row.series_id,
        ),
    )

    selected_ids = {row.series_id for row in ordered[:top_n]}
    rank_map = {row.series_id: idx + 1 for idx, row in enumerate(ordered[:top_n])}

    recommendation_rows: list[SeriesRecommendationRow] = []
    for row in rows:
        selected = row.series_id in selected_ids
        recommendation_rows.append(
            SeriesRecommendationRow(
                priority_rank=rank_map.get(row.series_id),
                series_id=row.series_id,
                deserves_deeper_modeling=selected,
                priority_score=row.priority_score,
                rationale=_recommendation_rationale(row),
                recommended_next_action=row.recommended_next_action,
            )
        )

    return sorted(
        recommendation_rows,
        key=lambda row: (
            0 if row.priority_rank is not None else 1,
            row.priority_rank or 999,
            row.series_id,
        ),
    )


def _build_summary(
    rows: list[SeriesComparisonRow],
    recommendation_rows: list[SeriesRecommendationRow],
) -> ComparisonSummary:
    """Build recommendation summary text for engineering review meetings.

    Args:
        rows: All per-series comparison rows.
        recommendation_rows: Recommendation rows with priority ranks assigned.

    Returns:
        ``ComparisonSummary`` with counts and markdown text.
    """
    n_series_screened = len(rows)
    n_failed = sum(row.outcome == "failed" for row in rows)
    recommended = [row for row in recommendation_rows if row.deserves_deeper_modeling]
    recommended_series_ids = [row.series_id for row in recommended]

    if not recommended_series_ids:
        summary_markdown = (
            "No series currently qualifies for deeper modeling. "
            "Prioritize data quality/readiness remediation and baseline model validation."
        )
    else:
        joined = ", ".join(recommended_series_ids)
        summary_markdown = (
            f"Recommend deeper modeling for {len(recommended_series_ids)} series: {joined}. "
            "Selection prioritizes high/medium forecastability, non-trivial directness ratio "
            "(>= 0.20), and stable horizon behavior after conditioning."
        )

    return ComparisonSummary(
        n_series_screened=n_series_screened,
        n_series_failed=n_failed,
        n_series_recommended=len(recommended_series_ids),
        recommended_series_ids=recommended_series_ids,
        summary_markdown=summary_markdown,
    )
