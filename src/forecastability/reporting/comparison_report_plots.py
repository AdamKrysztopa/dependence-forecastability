"""Matplotlib rendering helpers for multi-series comparison reports.

All functions in this module depend on ``matplotlib``; they must not be
imported from domain or use-case layers.  Import path:

    from forecastability.reporting.comparison_report_plots import (
        write_multi_series_comparison_artifacts,
    )
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from forecastability.domain.models.comparison_report import (
    ComparisonArtifactPaths,
    MultiSeriesComparisonReport,
)
from forecastability.triage.batch_models import BatchTriageRequest
from forecastability.triage.models import TriageRequest, TriageResult

# ---------------------------------------------------------------------------
# Internal plot helpers
# ---------------------------------------------------------------------------


def _save_no_data_plot(save_path: Path, *, title: str, subtitle: str) -> None:
    """Save a minimal placeholder figure when no plotable rows are available.

    Args:
        save_path: Output path for the PNG figure.
        title: Bold headline text.
        subtitle: Smaller explanatory text below the headline.
    """
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(8, 3.5))
    axis.text(0.5, 0.62, title, ha="center", va="center", fontsize=12, fontweight="bold")
    axis.text(0.5, 0.42, subtitle, ha="center", va="center", fontsize=10)
    axis.axis("off")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def _plot_auc(series_df: pd.DataFrame, *, save_path: Path) -> None:
    """Plot AMI and pAMI AUC bars for all analyzable series.

    Args:
        series_df: Series comparison DataFrame with ``ami_auc`` / ``pami_auc`` columns.
        save_path: Output path for the PNG figure.
    """
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
    """Plot directness ratio by series.

    Args:
        series_df: Series comparison DataFrame with a ``directness_ratio`` column.
        save_path: Output path for the PNG figure.
    """
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
    """Plot AMI/pAMI significance coverage by series.

    Args:
        series_df: Series comparison DataFrame with significance coverage columns.
        save_path: Output path for the PNG figure.
    """
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
    """Plot horizon-specific AMI/pAMI drop-off curves for all series.

    Args:
        dropoff_df: Horizon drop-off DataFrame with ``series_id``, ``horizon``,
            ``ami_dropoff_from_h1``, and ``pami_dropoff_from_h1`` columns.
        save_path: Output path for the PNG figure.
    """
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


# ---------------------------------------------------------------------------
# Markdown renderer (no matplotlib, but lives here for cohesion with the
# write_* function that references ComparisonArtifactPaths)
# ---------------------------------------------------------------------------


def _build_recommendation_markdown_table(recommendation_df: pd.DataFrame) -> str:
    """Render recommendation rows as markdown table text.

    Args:
        recommendation_df: Recommendation DataFrame from
            ``MultiSeriesComparisonReport.recommendation_frame()``.

    Returns:
        Markdown-formatted table string.
    """
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
    """Render the markdown comparison summary artifact.

    Args:
        report: In-memory comparison report.
        paths: Artifact output paths.

    Returns:
        Rendered markdown string.
    """
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


# ---------------------------------------------------------------------------
# Public coordinator — assembles report + writes artifacts
# ---------------------------------------------------------------------------


def build_multi_series_comparison_report(
    request: BatchTriageRequest,
    *,
    triage_runner: Callable[[TriageRequest], TriageResult],
    top_n: int = 5,
) -> MultiSeriesComparisonReport:
    """Generate multi-series comparison outputs from one batch triage request.

    Args:
        request: Batch request payload compatible with the triage-batch flow.
        triage_runner: Injectable single-series triage function.
        top_n: Maximum number of series to recommend for deeper modeling.

    Returns:
        In-memory report with standardized tables and recommendation summary.
    """
    from forecastability.domain.models.comparison_report import (  # noqa: PLC0415  # noqa: PLC0415
        HorizonDropoffRow,
        _build_dropoff_rows,
        _build_recommendation_table,
        _build_series_row,
        _build_summary,
    )
    from forecastability.use_cases.run_batch_triage import (  # noqa: PLC0415
        run_batch_triage_with_details,
    )

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
