"""Multi-series comparison reporting built on batch triage outputs."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from forecastability.triage.batch_models import (
    BatchSummaryRow,
    BatchTriageExecutionItem,
    BatchTriageRequest,
)
from forecastability.triage.models import TriageRequest, TriageResult
from forecastability.use_cases.run_batch_triage import run_batch_triage_with_details

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


def _compute_auc(values: np.ndarray) -> float:
    """Compute trapezoidal AUC for one horizon curve."""
    return float(np.trapezoid(values))


def _compute_significance_coverage(
    significant_lags: np.ndarray,
    *,
    n_horizons: int,
    compute_surrogates: bool,
) -> float | None:
    """Compute fraction of horizons that exceed surrogate significance bands."""
    if not compute_surrogates:
        return None
    if n_horizons <= 0:
        return None
    return float(significant_lags.size / n_horizons)


def _compute_dropoff_index(values: np.ndarray) -> float:
    """Compute early-to-late drop-off index in [roughly] increasing decay scale."""
    if values.size == 0:
        return 0.0
    window = max(1, int(np.ceil(values.size * 0.25)))
    head = float(np.mean(values[:window]))
    tail = float(np.mean(values[-window:]))
    return float((head - tail) / max(abs(head), 1e-12))


def _priority_score(row: SeriesComparisonRow) -> float:
    """Score one series for deeper-modeling priority ranking."""
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
    """Decide whether a series is a candidate for deeper modeling."""
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
    """Produce a short recommendation rationale for one series."""
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
    """Normalize one curve by its first-horizon value."""
    if values.size == 0:
        return np.array([], dtype=float)
    baseline = float(values[0])
    return values / max(abs(baseline), 1e-12)


def _build_dropoff_rows(
    series_id: str,
    raw: np.ndarray,
    partial: np.ndarray,
) -> list[HorizonDropoffRow]:
    """Build horizon-level normalized drop-off rows for one series."""
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


def _build_series_row(item: BatchTriageExecutionItem) -> SeriesComparisonRow:
    """Build one standardized comparison row from one batch execution item."""
    result = item.result
    triage_result = item.triage_result

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
    """Build recommendation rows and assign priority rank for selected series."""
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
    """Build recommendation summary text for engineering review meetings."""
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


def build_multi_series_comparison_report(
    request: BatchTriageRequest,
    *,
    triage_runner: Callable[[TriageRequest], TriageResult],
    top_n: int = 5,
) -> MultiSeriesComparisonReport:
    """Generate multi-series comparison outputs from one batch triage request.

    Args:
        request: Batch request payload compatible with #14 triage-batch flow.
        triage_runner: Injectable single-series triage function.
        top_n: Maximum number of series to recommend for deeper modeling.

    Returns:
        In-memory report with standardized tables and recommendation summary.
    """
    execution = run_batch_triage_with_details(request, triage_runner=triage_runner)

    series_rows = [_build_series_row(item) for item in execution.items_with_results]

    dropoff_rows: list[HorizonDropoffRow] = []
    for item in execution.items_with_results:
        triage_result = item.triage_result
        if triage_result is None or triage_result.analyze_result is None:
            continue
        analyze_result = triage_result.analyze_result
        dropoff_rows.extend(
            _build_dropoff_rows(
                item.result.series_id,
                analyze_result.raw,
                analyze_result.partial,
            )
        )

    recommendation_rows = _build_recommendation_table(series_rows, top_n=max(1, top_n))
    summary = _build_summary(series_rows, recommendation_rows)

    return MultiSeriesComparisonReport(
        batch_summary_table=execution.response.summary_table,
        series_table=series_rows,
        horizon_dropoff_table=dropoff_rows,
        recommendation_table=recommendation_rows,
        summary=summary,
    )


def _save_no_data_plot(save_path: Path, *, title: str, subtitle: str) -> None:
    """Save a minimal placeholder figure when no plotable rows are available."""
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(8, 3.5))
    axis.text(0.5, 0.62, title, ha="center", va="center", fontsize=12, fontweight="bold")
    axis.text(0.5, 0.42, subtitle, ha="center", va="center", fontsize=10)
    axis.axis("off")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def _plot_auc(series_df: pd.DataFrame, *, save_path: Path) -> None:
    """Plot AMI and pAMI AUC bars for all analyzable series."""
    data = series_df.dropna(subset=["ami_auc", "pami_auc"]).copy()
    if data.empty:
        _save_no_data_plot(
            save_path,
            title="AUC Comparison",
            subtitle="No analyzable series with AUC values.",
        )
        return

    x = np.arange(len(data), dtype=float)
    width = 0.38

    fig_width = max(8.0, len(data) * 1.15)
    fig, axis = plt.subplots(figsize=(fig_width, 4.8))
    axis.bar(x - width / 2.0, data["ami_auc"], width=width, label="AMI AUC")
    axis.bar(x + width / 2.0, data["pami_auc"], width=width, label="pAMI AUC")
    axis.set_xticks(x)
    axis.set_xticklabels(data["series_id"], rotation=30, ha="right")
    axis.set_ylabel("AUC")
    axis.set_title("AMI vs pAMI AUC across series")
    axis.legend(loc="upper right")

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def _plot_directness_ratio(series_df: pd.DataFrame, *, save_path: Path) -> None:
    """Plot directness ratio by series."""
    data = series_df.dropna(subset=["directness_ratio"]).copy()
    if data.empty:
        _save_no_data_plot(
            save_path,
            title="Directness Ratio",
            subtitle="No analyzable series with directness ratio values.",
        )
        return

    fig_width = max(8.0, len(data) * 0.95)
    fig, axis = plt.subplots(figsize=(fig_width, 4.2))
    axis.bar(data["series_id"], data["directness_ratio"], color="#4C78A8")
    axis.axhline(0.20, color="#F58518", linestyle="--", linewidth=1.2, label="review threshold")
    axis.axhline(0.50, color="#54A24B", linestyle=":", linewidth=1.2, label="strong directness")
    axis.set_ylabel("directness ratio (pAMI AUC / AMI AUC)")
    axis.set_title("Directness ratio by series")
    axis.tick_params(axis="x", rotation=30)
    axis.legend(loc="upper right")

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def _plot_significance_coverage(series_df: pd.DataFrame, *, save_path: Path) -> None:
    """Plot AMI/pAMI significance coverage by series."""
    data = series_df.copy()
    data["ami_significance_coverage"] = data["ami_significance_coverage"].fillna(0.0)
    data["pami_significance_coverage"] = data["pami_significance_coverage"].fillna(0.0)

    if data.empty:
        _save_no_data_plot(
            save_path,
            title="Significance Coverage",
            subtitle="No series available in comparison table.",
        )
        return

    x = np.arange(len(data), dtype=float)
    width = 0.38

    fig_width = max(8.0, len(data) * 1.15)
    fig, axis = plt.subplots(figsize=(fig_width, 4.8))
    axis.bar(
        x - width / 2.0,
        data["ami_significance_coverage"],
        width=width,
        label="AMI significance coverage",
    )
    axis.bar(
        x + width / 2.0,
        data["pami_significance_coverage"],
        width=width,
        label="pAMI significance coverage",
    )
    axis.set_xticks(x)
    axis.set_xticklabels(data["series_id"], rotation=30, ha="right")
    axis.set_ylim(0.0, 1.0)
    axis.set_ylabel("fraction of significant horizons")
    axis.set_title("Significance coverage by series")
    axis.legend(loc="upper right")

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def _plot_horizon_dropoff(dropoff_df: pd.DataFrame, *, save_path: Path) -> None:
    """Plot horizon-specific AMI/pAMI drop-off curves for all series."""
    if dropoff_df.empty:
        _save_no_data_plot(
            save_path,
            title="Horizon-Specific Drop-off",
            subtitle="No analyzable horizon-level drop-off rows.",
        )
        return

    ordered = dropoff_df.sort_values(["series_id", "horizon"])

    fig, axes = plt.subplots(2, 1, figsize=(9.5, 7.0), sharex=True)
    for series_id, group in ordered.groupby("series_id"):
        axes[0].plot(group["horizon"], group["ami_dropoff_from_h1"], marker="o", label=series_id)
        axes[1].plot(group["horizon"], group["pami_dropoff_from_h1"], marker="o", label=series_id)

    axes[0].set_ylabel("AMI drop-off from h=1")
    axes[0].set_title("Horizon-specific AMI drop-off")
    axes[1].set_ylabel("pAMI drop-off from h=1")
    axes[1].set_title("Horizon-specific pAMI drop-off")
    axes[1].set_xlabel("horizon")

    handles, labels = axes[1].get_legend_handles_labels()
    if labels:
        fig.legend(handles, labels, loc="upper center", ncol=min(4, len(labels)), frameon=False)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def _build_recommendation_markdown_table(recommendation_df: pd.DataFrame) -> str:
    """Render recommendation rows as markdown table text."""
    lines = [
        "| Priority | Series | Deeper modeling | Score | Rationale |",
        "|---|---|---|---|---|",
    ]

    for row in recommendation_df.to_dict(orient="records"):
        priority_rank = row.get("priority_rank")
        priority = priority_rank if priority_rank is not None else "-"
        lines.append(
            "| "
            f"{priority} | {row.get('series_id')} | {row.get('deserves_deeper_modeling')} "
            f"| {float(row.get('priority_score', 0.0)):.4f} | {row.get('rationale')} |"
        )

    return "\n".join(lines)


def _render_report_markdown(
    report: MultiSeriesComparisonReport,
    *,
    paths: ComparisonArtifactPaths,
) -> str:
    """Render the markdown comparison summary artifact."""
    recommendation_df = report.recommendation_frame()
    recommendation_table_md = _build_recommendation_markdown_table(recommendation_df)

    recommended = report.summary.recommended_series_ids
    recommended_text = ", ".join(recommended) if recommended else "none"

    return "\n".join(
        [
            "# Multi-Series Comparison Report",
            "",
            "## Scope",
            "- Built from deterministic batch triage outputs.",
            (
                "- Standardized metrics include AMI AUC, pAMI AUC, directness "
                "ratio, significance coverage, and horizon-specific drop-off."
            ),
            "",
            "## Recommendation Summary",
            f"- Screened series: {report.summary.n_series_screened}",
            f"- Failed series: {report.summary.n_series_failed}",
            f"- Recommended for deeper modeling: {report.summary.n_series_recommended}",
            f"- Recommended IDs: {recommended_text}",
            "",
            report.summary.summary_markdown,
            "",
            "## Recommendation Table",
            recommendation_table_md,
            "",
            "## Artifact Paths",
            f"- Series comparison table: {paths.series_table_csv}",
            f"- Horizon drop-off table: {paths.horizon_dropoff_csv}",
            f"- Recommendation table: {paths.recommendations_csv}",
            f"- AUC plot: {paths.auc_plot_png}",
            f"- Directness plot: {paths.directness_plot_png}",
            f"- Significance coverage plot: {paths.significance_plot_png}",
            f"- Horizon drop-off plot: {paths.horizon_dropoff_plot_png}",
            "",
        ]
    )


def write_multi_series_comparison_artifacts(
    report: MultiSeriesComparisonReport,
    *,
    tables_dir: Path,
    figures_dir: Path,
    report_path: Path,
) -> ComparisonArtifactPaths:
    """Write standardized comparison tables, plots, and markdown summary.

    Args:
        report: In-memory comparison report.
        tables_dir: Destination directory for CSV tables.
        figures_dir: Destination directory for PNG figures.
        report_path: Destination markdown summary path.

    Returns:
        Paths to all generated artifacts.
    """
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    series_df = report.series_table_frame()
    dropoff_df = report.horizon_dropoff_frame()
    recommendation_df = report.recommendation_frame()

    series_table_csv = tables_dir / "multi_series_comparison_table.csv"
    horizon_dropoff_csv = tables_dir / "multi_series_horizon_dropoff.csv"
    recommendations_csv = tables_dir / "multi_series_recommendations.csv"

    series_df.to_csv(series_table_csv, index=False)
    dropoff_df.to_csv(horizon_dropoff_csv, index=False)
    recommendation_df.to_csv(recommendations_csv, index=False)

    auc_plot_png = figures_dir / "multi_series_auc.png"
    directness_plot_png = figures_dir / "multi_series_directness_ratio.png"
    significance_plot_png = figures_dir / "multi_series_significance_coverage.png"
    horizon_dropoff_plot_png = figures_dir / "multi_series_horizon_dropoff.png"

    _plot_auc(series_df, save_path=auc_plot_png)
    _plot_directness_ratio(series_df, save_path=directness_plot_png)
    _plot_significance_coverage(series_df, save_path=significance_plot_png)
    _plot_horizon_dropoff(dropoff_df, save_path=horizon_dropoff_plot_png)

    paths = ComparisonArtifactPaths(
        series_table_csv=series_table_csv,
        horizon_dropoff_csv=horizon_dropoff_csv,
        recommendations_csv=recommendations_csv,
        auc_plot_png=auc_plot_png,
        directness_plot_png=directness_plot_png,
        significance_plot_png=significance_plot_png,
        horizon_dropoff_plot_png=horizon_dropoff_plot_png,
        report_markdown=report_path,
    )

    report_path.write_text(_render_report_markdown(report, paths=paths), encoding="utf-8")
    return paths
