"""Build report markdown artifacts from generated outputs."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import cast

import pandas as pd

# Default to non-interactive plotting backend for script execution.
os.environ.setdefault("MPLBACKEND", "Agg")

from forecastability.reporting import (
    build_benchmark_markdown,
    build_frequency_panel_markdown,
    build_linkedin_post,
    mandatory_caveats,
    save_exog_reports,
)
from forecastability.utils.io_models import CanonicalPayload
from forecastability.utils.plots import plot_rank_association_bars, plot_smape_vs_ami

_logger = logging.getLogger(__name__)


def _load_canonical_payloads(json_dir: Path) -> list[CanonicalPayload]:
    """Load and validate canonical JSON payloads."""
    if not json_dir.exists():
        raise FileNotFoundError(f"Missing canonical JSON directory: {json_dir}")

    payload_paths = sorted(json_dir.glob("*.json"))
    if not payload_paths:
        raise FileNotFoundError(f"No canonical payloads found in: {json_dir}")
    return [CanonicalPayload.from_json_file(path) for path in payload_paths]


def _load_required_table(path: Path, *, required_columns: set[str]) -> pd.DataFrame:
    """Load a required CSV and validate minimal schema."""
    if not path.exists():
        raise FileNotFoundError(f"Missing required table: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Required table is empty: {path}")

    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(f"Table {path} is missing required columns: {', '.join(missing)}")
    return df


# ---------------------------------------------------------------------------
# Narrative helpers (plan 39)
# ---------------------------------------------------------------------------


def _canonical_narrative(payload: CanonicalPayload) -> str:
    """Generate a narrative paragraph for one canonical series."""
    s = payload.summary
    i = payload.interpretation
    name = payload.series_name.replace("_", " ").title()
    dr = float(s.directness_ratio)
    n_sig_ami = int(s.n_sig_ami)
    n_sig_pami = int(s.n_sig_pami)
    peak_ami = s.peak_lag_ami
    peak_pami = s.peak_lag_pami
    fc = i.forecastability_class
    dc = i.directness_class
    regime = i.modeling_regime
    narrative = i.narrative or ""

    if dr > 1.5:
        collapse_desc = (
            "pAMI exceeds AMI at multiple horizons, a signature of ARCH-type "
            "volatility clustering where squared returns carry MI not present in raw returns"
        )
    elif dr < 0.3:
        collapse_desc = (
            "most AMI structure collapses after linear conditioning, confirming that "
            "predictive information is largely mediated through linear autoregressive dependence"
        )
    else:
        collapse_desc = (
            "substantial direct MI survives linear conditioning, pointing to genuine "
            "non-linear or short-lag predictive relationships beyond linear structure"
        )

    if peak_ami == peak_pami:
        peak_desc = f"the dominant lag (h={peak_ami}) is unchanged by conditioning"
    else:
        peak_desc = (
            f"the AMI peak at h={peak_ami} shifts to h={peak_pami} after conditioning, "
            "suggesting that the dominant structure is partially mediated at longer lags"
        )

    return (
        f"**{name}** exhibits **{fc}** forecastability "
        f"({n_sig_ami} significant AMI lags; {n_sig_pami} significant pAMI lags). "
        f"The directness ratio is {dr:.3f} ({dc} directness): {collapse_desc}. "
        f"In terms of lag structure, {peak_desc}. "
        f"{narrative} "
        f"Recommended modelling regime: **{regime}**."
    )


def _cross_series_table(payloads: list[CanonicalPayload]) -> str:
    """Build a cross-series comparison markdown table."""
    header = (
        "| Series | FC class | Directness | n_sig AMI | n_sig pAMI | DR | Peak AMI | Peak pAMI |"
    )
    sep = "|---|---|---|---|---|---|---|---|"
    rows = [header, sep]
    for p in payloads:
        s = p.summary
        i = p.interpretation
        name = p.series_name.replace("_", " ").title()
        rows.append(
            f"| {name} "
            f"| {i.forecastability_class} "
            f"| {i.directness_class} "
            f"| {int(s.n_sig_ami)} "
            f"| {int(s.n_sig_pami)} "
            f"| {float(s.directness_ratio):.3f} "
            f"| {s.peak_lag_ami} "
            f"| {s.peak_lag_pami} |"
        )
    return "\n".join(rows)


def _benchmark_narrative(rank_df: pd.DataFrame) -> str:
    """Generate benchmark panel interpretation prose from rank_associations table."""
    n_rows = len(rank_df)
    if n_rows == 0:
        return "_No benchmark data available._"

    models = rank_df["model_name"].unique().tolist()
    horizons = sorted(rank_df["horizon"].unique().tolist())

    # Summarise delta (pAMI − AMI Spearman) across models and horizons
    mean_delta = float(rank_df["delta_pami_minus_ami"].mean())
    pos_frac = float((rank_df["delta_pami_minus_ami"] > 0).mean())

    if mean_delta > 0.05:
        delta_desc = (
            f"pAMI is a stronger rank predictor of forecast error than AMI "
            f"(mean Δ = {mean_delta:+.3f}), suggesting that the linear-conditioning "
            f"step removes noise and sharpens the signal for {pos_frac:.0%} of "
            f"model-horizon combinations"
        )
    elif mean_delta < -0.05:
        delta_desc = (
            f"AMI is a marginally stronger rank predictor than pAMI "
            f"(mean Δ = {mean_delta:+.3f}), consistent with the conditional MI "
            f"losing power when the series are already well-explained by linear structure"
        )
    else:
        delta_desc = (
            f"AMI and pAMI show comparable rank-prediction performance "
            f"(mean Δ = {mean_delta:+.3f}), indicating that linear conditioning "
            f"neither substantially helps nor hurts forecastability diagnosis"
        )

    model_str = ", ".join(f"`{m}`" for m in models)
    horizon_str = f"h={horizons[0]}…{horizons[-1]}"

    return (
        f"The benchmark panel evaluated {model_str} across horizons {horizon_str} "
        f"({n_rows} model-horizon rows). "
        f"{delta_desc}. "
        f"These results should be interpreted with caution: the Spearman rank "
        f"correlation between forecastability diagnostics and realised sMAPE is "
        f"an indirect validation — the horizon-specific nature of AMI/pAMI is the "
        f"primary analytical contribution, not a direct accuracy predictor."
    )


def _executive_summary(payloads: list[CanonicalPayload]) -> str:
    """Generate a 2-3 paragraph executive summary across all canonical series."""
    if not payloads:
        return "_No canonical payloads available; generate canonical outputs first._"

    fc_counts: dict[str, int] = {}
    for p in payloads:
        fc = p.interpretation.forecastability_class
        fc_counts[fc] = fc_counts.get(fc, 0) + 1

    drs = [float(p.summary.directness_ratio) for p in payloads]
    dr_min, dr_max = min(drs), max(drs)
    n_series = len(payloads)

    high_n = fc_counts.get("high", 0)
    medium_n = fc_counts.get("medium", 0)
    low_n = fc_counts.get("low", 0)

    para1 = (
        f"This report summarises an AMI → pAMI forecastability analysis across "
        f"{n_series} canonical time-series examples. "
        f"Horizon-specific Approximate Mutual Information (AMI) measures raw lagged "
        f"dependence; partial AMI (pAMI) removes linear autoregressive structure first, "
        f"isolating non-linear or interaction-driven predictive content. "
        f"Of the {n_series} series, {high_n} show **high**, {medium_n} **medium**, "
        f"and {low_n} **low** forecastability under the AMI diagnostic."
    )

    para2 = (
        f"The directness ratio (pAMI AUC / AMI AUC) spans {dr_min:.3f} to {dr_max:.3f} "
        f"across the panel, revealing a wide spectrum of dependency structures. "
        f"Series with low directness ratios (< 0.3) carry most of their predictive "
        f"content through linear autoregressive channels — well-captured by AR or "
        f"seasonal models. Series with ratios near 1.0 retain strong direct MI, "
        f"suggesting non-linear modelling may add value. Ratios above 1.5 are "
        f"consistent with ARCH-type volatility clustering."
    )

    para3 = (
        "pAMI identifies the lag structure that is genuinely informative beyond "
        "linear trend and seasonality, enabling practitioners to distinguish "
        "series where deep learning or non-linear models are justified from those "
        "where a well-tuned ETS or ARIMA is sufficient. "
        "Note: AMI is paper-aligned; pAMI is a project extension and is "
        "not paper-native."
    )

    return "\n\n".join([para1, para2, para3])


def _what_pami_adds(payloads: list[CanonicalPayload]) -> str:
    """Synthesise what pAMI adds beyond AMI across the canonical panel."""
    low_dr = [
        p.series_name.replace("_", " ").title()
        for p in payloads
        if float(p.summary.directness_ratio) < 0.3
    ]
    high_dr = [
        p.series_name.replace("_", " ").title()
        for p in payloads
        if float(p.summary.directness_ratio) >= 0.3
    ]

    para1 = (
        "AMI alone answers 'is there predictive structure?'. "
        "pAMI answers the follow-up: 'is that structure direct, or mostly a "
        "by-product of linear autocorrelation?' This distinction is practically "
        "important because linear models saturate the linear-mediated MI at low cost, "
        "whereas direct MI requires non-linear capacity."
    )

    low_str = ", ".join(low_dr) if low_dr else "none in this panel"
    high_str = ", ".join(high_dr) if high_dr else "none in this panel"

    para2 = (
        f"Series with **low directness** ({low_str}) show that almost all AMI "
        f"collapses after conditioning — model selection can safely default to "
        f"linear or seasonal baselines. "
        f"Series with **higher directness** ({high_str}) retain meaningful direct MI, "
        f"justifying the additional complexity of non-linear or interaction models."
    )

    para3 = (
        "In the benchmark panel, pAMI rank-correlation with sMAPE is directionally "
        "consistent with AMI but noisier at short horizons, as expected: the "
        "conditioning step introduces additional estimation variance on short series. "
        "The combined AMI + pAMI profile remains the recommended diagnostic, "
        "using pAMI primarily to confirm or refute model-complexity choices."
    )

    return "\n\n".join([para1, para2, para3])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _load_report_inputs(
    *,
    json_dir: Path,
    tables_dir: Path,
) -> tuple[
    list[CanonicalPayload],
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame | None,
    pd.DataFrame | None,
]:
    """Load and validate all report inputs."""
    canonical_payloads = _load_canonical_payloads(json_dir)
    horizon_table = _load_required_table(
        tables_dir / "horizon_table.csv",
        required_columns={"series_id", "horizon", "model_name", "ami", "pami", "smape"},
    )
    rank_associations = _load_required_table(
        tables_dir / "rank_associations.csv",
        required_columns={
            "model_name",
            "horizon",
            "spearman_ami_smape",
            "spearman_pami_smape",
            "delta_pami_minus_ami",
        },
    )
    frequency_panel = _load_required_table(
        tables_dir / "frequency_panel_summary.csv",
        required_columns={
            "frequency",
            "model_name",
            "mean_ami",
            "mean_pami",
            "mean_smape",
            "directness_ratio",
        },
    )

    k_sensitivity_path = tables_dir / "k_sensitivity.csv"
    bootstrap_path = tables_dir / "bootstrap_uncertainty.csv"
    k_sensitivity = pd.read_csv(k_sensitivity_path) if k_sensitivity_path.exists() else None
    bootstrap_uncertainty = pd.read_csv(bootstrap_path) if bootstrap_path.exists() else None

    return (
        canonical_payloads,
        horizon_table,
        rank_associations,
        frequency_panel,
        k_sensitivity,
        bootstrap_uncertainty,
    )


def main() -> None:
    """Build final report and LinkedIn-ready markdown outputs."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    json_dir = Path("outputs/json/canonical")
    tables_dir = Path("outputs/tables")
    report_dir = Path("outputs/reports")
    figures_rel = "../figures"  # relative from outputs/reports/
    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        (
            canonical_payloads,
            horizon_table,
            rank_associations,
            frequency_panel,
            k_sensitivity,
            bootstrap_uncertainty,
        ) = _load_report_inputs(json_dir=json_dir, tables_dir=tables_dir)
    except (FileNotFoundError, ValueError) as exc:
        _logger.error("Cannot build report artifacts: %s", exc)
        _logger.error(
            "Run scripts/run_canonical_examples.py and scripts/run_benchmark_panel.py first."
        )
        raise SystemExit(2) from exc

    plot_rank_association_bars(
        rank_associations,
        save_path=Path("outputs/figures/rank_association_delta.png"),
    )
    plot_smape_vs_ami(
        horizon_table,
        metric="ami",
        horizons=[1],
        save_path=Path("outputs/figures/smape_vs_ami_h1.png"),
    )
    plot_smape_vs_ami(
        horizon_table,
        metric="pami",
        horizons=[1],
        save_path=Path("outputs/figures/smape_vs_pami_h1.png"),
    )
    plot_smape_vs_ami(
        horizon_table,
        metric="ami",
        save_path=Path("outputs/figures/smape_vs_ami_all_horizons.png"),
    )

    # ------------------------------------------------------------------
    # Build report sections
    # ------------------------------------------------------------------
    sections: list[str] = [
        "# AMI → pAMI Forecastability Analysis Report",
        "",
        "> **Disclosure:** AMI is paper-aligned; pAMI is a project extension "
        "and is **not** paper-native.",
        "",
        "## Executive Summary",
        "",
        _executive_summary(canonical_payloads),
        "",
        "---",
        "",
        "## Methodology",
        "",
        "- **AMI**: horizon-specific kNN mutual information, computed per lag h "
        "separately (k=8, `sklearn` estimator).",
        "- **pAMI**: linear residualisation (AR(1) removed) followed by kNN MI on "
        "residuals — isolates non-linear / direct predictive content.",
        "- **Surrogate significance**: phase-randomised surrogates, n=99, α=5% "
        "two-sided per horizon.",
        "- **Rolling-origin**: expanding window, diagnostics on train split only; "
        "forecast errors on post-origin holdout only.",
        "- **Rolling origins**: 10 per series.",
        "",
        "---",
        "",
        "## Canonical Examples",
        "",
    ]

    for payload in canonical_payloads:
        s_name = payload.series_name
        display = s_name.replace("_", " ").title()
        fig_overlay = f"{figures_rel}/canonical/{s_name}_overlay.png"
        fig_band = f"{figures_rel}/canonical/{s_name}_ami_band.png"
        s = payload.summary
        i = payload.interpretation

        sections += [
            f"### {display}",
            "",
            _canonical_narrative(payload),
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| n_sig AMI | {int(s.n_sig_ami)} |",
            f"| n_sig pAMI | {int(s.n_sig_pami)} |",
            f"| Directness ratio | {float(s.directness_ratio):.4f} |",
            f"| AUC AMI | {float(s.auc_ami):.4f} |",
            f"| AUC pAMI | {float(s.auc_pami):.4f} |",
            f"| Peak lag AMI | {s.peak_lag_ami} |",
            f"| Peak lag pAMI | {s.peak_lag_pami} |",
            f"| Forecastability class | {i.forecastability_class} |",
            f"| Directness class | {i.directness_class} |",
            f"| Modelling regime | {i.modeling_regime} |",
            "",
            f"![AMI/pAMI overlay — {display}]({fig_overlay})",
            f"![AMI with significance band — {display}]({fig_band})",
            "",
        ]

    sections += [
        "---",
        "",
        "## Cross-Series Comparison",
        "",
        _cross_series_table(canonical_payloads),
        "",
        "The canonical panel spans the full spectrum of time-series behaviour: "
        "from highly periodic (Sine Wave, Air Passengers) to chaotic (Hénon Map) "
        "to near-random (financial return series). The directness ratio is the key "
        "differentiator — it separates series where AMI and pAMI are redundant "
        "(linear-structured series) from those where pAMI adds unique diagnostic value.",
        "",
        "---",
        "",
        "## Benchmark Panel (M4)",
        "",
        build_benchmark_markdown(horizon_table=horizon_table, rank_associations=rank_associations),
        "",
        _benchmark_narrative(rank_associations),
        "",
        "### sMAPE vs AMI — per forecaster (h=1)",
        "",
        "![sMAPE vs AMI at h=1 per forecaster](../figures/smape_vs_ami_h1.png)",
        "",
        "### sMAPE vs pAMI — per forecaster (h=1)",
        "",
        "![sMAPE vs pAMI at h=1 per forecaster](../figures/smape_vs_pami_h1.png)",
        "",
        "### sMAPE vs AMI — per forecaster (all horizons pooled)",
        "",
        "![sMAPE vs AMI all horizons](../figures/smape_vs_ami_all_horizons.png)",
        "",
        "### Rank-association delta (pAMI − AMI)",
        "",
        "![Rank association delta](../figures/rank_association_delta.png)",
        "",
        build_frequency_panel_markdown(frequency_summary=frequency_panel),
        "",
        "---",
        "",
        "## What pAMI Adds Beyond AMI",
        "",
        _what_pami_adds(canonical_payloads),
        "",
    ]

    if k_sensitivity is not None:
        sections += [
            "---",
            "",
            "## k-Sensitivity (AMI/pAMI estimator)",
            "",
            k_sensitivity.to_csv(index=False).strip(),
            "",
        ]

    if bootstrap_uncertainty is not None:
        sections += [
            "---",
            "",
            "## Bootstrap Descriptor Uncertainty",
            "",
            bootstrap_uncertainty.to_csv(index=False).strip(),
            "",
        ]

    sections += [
        "---",
        "",
        "## Caveats",
        "",
        *[f"- {line}" for line in mandatory_caveats()],
        "",
        "---",
        "",
        "## References",
        "",
        "- Goerg, G. M. (2013). *Forecastable Component Analysis*. "
        "ICML 2013. [arXiv:1305.4342](https://arxiv.org/abs/1305.4342)",
        "- Runge, J. et al. (2019). *Detecting and quantifying causal associations "
        "in large nonlinear time series datasets*. Science Advances.",
        "",
    ]

    report_path = report_dir / "ami_to_pami_report.md"
    report_path.write_text("\n".join(sections), encoding="utf-8")

    linkedin_path = report_dir / "linkedin_post.md"
    linkedin_payloads: list[dict[str, object]] = cast(
        list[dict[str, object]],
        [payload.model_dump(exclude_none=True) for payload in canonical_payloads],
    )
    linkedin_path.write_text(
        build_linkedin_post(canonical_payloads=linkedin_payloads),
        encoding="utf-8",
    )

    summary_path = report_dir / "summary.md"
    summary_path.write_text(
        "\n".join(
            [
                "# AMI to pAMI Summary",
                "",
                "- Canonical examples: complete (PNG + JSON + markdown).",
                "- Benchmark panel: complete (horizon, rank association, terciles).",
                "- Final report and LinkedIn draft generated automatically.",
            ]
        ),
        encoding="utf-8",
    )

    _logger.info("Saved report: %s", report_path)
    _logger.info("Saved LinkedIn post: %s", linkedin_path)

    exog_json_dir = Path("outputs/json/exog")
    if exog_json_dir.exists() and any(exog_json_dir.glob("*.json")):
        save_exog_reports(json_dir=exog_json_dir, report_dir=report_dir / "exog")


if __name__ == "__main__":
    main()
