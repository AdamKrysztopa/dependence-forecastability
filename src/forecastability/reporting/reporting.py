"""JSON/markdown reporting helpers."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

import pandas as pd
from pydantic import BaseModel, ConfigDict

from forecastability.reporting.interpretation import interpret_canonical_result
from forecastability.utils.aggregation import summarize_canonical_result
from forecastability.utils.io_models import CanonicalPayload
from forecastability.utils.types import CanonicalExampleResult

_logger = logging.getLogger(__name__)


class InterpretiveAnswers(BaseModel):
    """Structured Q&A answers derived from interpretation of one canonical example."""

    model_config = ConfigDict(frozen=True)

    is_there_predictive_structure: str
    is_it_broad_or_compact: str
    is_it_direct_or_mediated: str
    which_lags_remain_important: str
    what_modeling_regime_is_justified: str
    if_model_performance_mismatch_explanation: str


def _interpretive_answers(result: CanonicalExampleResult) -> InterpretiveAnswers:
    summary = summarize_canonical_result(result)
    interpretation = interpret_canonical_result(result)

    predictive_structure = (
        "Yes" if interpretation.forecastability_class in {"high", "medium"} else "Weak"
    )
    broad_or_compact = "Broad" if summary.n_sig_ami > 6 else "Compact"
    direct_or_mediated = (
        "Direct" if interpretation.directness_class == "high" else "Mostly mediated"
    )

    return InterpretiveAnswers(
        is_there_predictive_structure=predictive_structure,
        is_it_broad_or_compact=broad_or_compact,
        is_it_direct_or_mediated=direct_or_mediated,
        which_lags_remain_important=str(interpretation.primary_lags),
        what_modeling_regime_is_justified=interpretation.modeling_regime,
        if_model_performance_mismatch_explanation=(
            "No benchmark mismatch check for canonical examples."
        ),
    )


def save_canonical_result_json(
    result: CanonicalExampleResult,
    *,
    output_path: Path,
) -> None:
    """Save canonical result summary to JSON."""
    summary = summarize_canonical_result(result)
    interpretation = interpret_canonical_result(result)

    payload = {
        "series_name": result.series_name,
        "summary": summary.model_dump(),
        "interpretation": {
            "forecastability_class": interpretation.forecastability_class,
            "directness_class": interpretation.directness_class,
            "primary_lags": interpretation.primary_lags,
            "modeling_regime": interpretation.modeling_regime,
            "narrative": interpretation.narrative,
            "diagnostics": interpretation.diagnostics.model_dump(),
        },
        "analysis_agent_answers": _interpretive_answers(result).model_dump(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_canonical_markdown(
    result: CanonicalExampleResult,
) -> str:
    """Build markdown summary for one canonical example."""
    summary = summarize_canonical_result(result)
    interpretation = interpret_canonical_result(result)
    qa = _interpretive_answers(result)
    mismatch = qa.if_model_performance_mismatch_explanation

    return f"""# {result.series_name}

## Summary
- n_sig_ami: {summary.n_sig_ami}
- n_sig_pami: {summary.n_sig_pami}
- peak_lag_ami: {summary.peak_lag_ami}
- peak_lag_pami: {summary.peak_lag_pami}
- auc_ami: {summary.auc_ami:.4f}
- auc_pami: {summary.auc_pami:.4f}
- directness_ratio: {summary.directness_ratio:.4f}

## Interpretation
- forecastability_class: {interpretation.forecastability_class}
- directness_class: {interpretation.directness_class}
- primary_lags: {interpretation.primary_lags}
- modeling_regime: {interpretation.modeling_regime}

## Final Analysis Checks
- Is there predictive structure? {qa.is_there_predictive_structure}
- Is it broad or compact? {qa.is_it_broad_or_compact}
- Is it direct or mostly mediated? {qa.is_it_direct_or_mediated}
- Which lags remain important after conditioning? {qa.which_lags_remain_important}
- What modeling regime is justified? {qa.what_modeling_regime_is_justified}
- If model performance does not align with AMI/pAMI, what explains mismatch? {mismatch}

## Narrative
{interpretation.narrative}
"""


def _series_label(series_name: str) -> str:
    """Return a stable human-readable label for one series name."""
    return series_name.replace("_", " ").title()


def _canonical_panel_recommendation(payload: CanonicalPayload) -> str:
    """Build a deterministic modeling recommendation for one canonical payload."""
    summary = payload.summary
    interpretation = payload.interpretation

    if interpretation.primary_lags:
        lag_text = ", ".join(str(lag) for lag in interpretation.primary_lags)
        lag_sentence = f"Focus validation first on lags {lag_text}."
    else:
        lag_sentence = (
            "No dominant conditioned lag stands out yet, so keep lag selection conservative."
        )

    if interpretation.forecastability_class == "low":
        return (
            f"Keep simple baselines first. {interpretation.modeling_regime}. "
            f"Only escalate complexity if new exogenous structure appears. {lag_sentence}"
        )

    if interpretation.directness_class in {"high", "arch_suspected"}:
        return (
            f"Start with {interpretation.modeling_regime} and test nonlinear capacity explicitly. "
            f"The directness ratio of {summary.directness_ratio:.2f} indicates that "
            "structure survives "
            f"linear conditioning. {lag_sentence}"
        )

    return (
        f"Use {interpretation.modeling_regime} as the default challenger while "
        "keeping a strong linear baseline in the comparison set. "
        f"The directness ratio of {summary.directness_ratio:.2f} suggests "
        f"that some dependence is mediated through simpler dynamics. {lag_sentence}"
    )


def build_canonical_panel_markdown(*, payloads: list[CanonicalPayload]) -> str:
    """Build a deterministic markdown summary for a canonical panel run."""
    if not payloads:
        return "# Canonical Panel Summary\n\n_No canonical payloads available._\n"

    forecastability_counts = {"high": 0, "medium": 0, "low": 0}
    for payload in payloads:
        forecastability_class = payload.interpretation.forecastability_class
        forecastability_counts[forecastability_class] = (
            forecastability_counts.get(forecastability_class, 0) + 1
        )

    directness_values = [float(payload.summary.directness_ratio) for payload in payloads]
    executive_summary = (
        f"This canonical run covers {len(payloads)} series. "
        f"{forecastability_counts.get('high', 0)} classify as high forecastability, "
        f"{forecastability_counts.get('medium', 0)} as medium, and "
        f"{forecastability_counts.get('low', 0)} as low. "
        f"Directness ratios span {min(directness_values):.2f} to {max(directness_values):.2f}, "
        "separating series whose dependence survives linear conditioning from those "
        "that are better "
        "handled by simpler autoregressive or seasonal baselines."
    )

    lines = [
        "# Canonical Panel Summary",
        "",
        "## Executive Summary",
        executive_summary,
        "",
        "## Cross-Series Snapshot",
        "| Series | Forecastability | Directness | Directness Ratio | n_sig AMI | "
        "n_sig pAMI | Recommended Regime | Primary Lags |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for payload in payloads:
        primary_lags = ", ".join(str(lag) for lag in payload.interpretation.primary_lags) or "-"
        lines.append(
            "| "
            f"{_series_label(payload.series_name)} "
            f"| {payload.interpretation.forecastability_class} "
            f"| {payload.interpretation.directness_class} "
            f"| {float(payload.summary.directness_ratio):.3f} "
            f"| {int(payload.summary.n_sig_ami)} "
            f"| {int(payload.summary.n_sig_pami)} "
            f"| {payload.interpretation.modeling_regime} "
            f"| {primary_lags} |"
        )

    lines.extend(["", "## Actionable Recommendations"])
    for payload in payloads:
        lines.extend(
            [
                "",
                f"### {_series_label(payload.series_name)}",
                payload.interpretation.narrative or "No narrative available.",
                "",
                f"Recommendation: {_canonical_panel_recommendation(payload)}",
            ]
        )

    return "\n".join(lines) + "\n"


def save_canonical_markdown(result: CanonicalExampleResult, *, output_path: Path) -> None:
    """Save markdown snippet for one canonical example."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_canonical_markdown(result), encoding="utf-8")


def build_benchmark_markdown(
    *,
    horizon_table: pd.DataFrame,
    rank_associations: pd.DataFrame,
) -> str:
    """Build a compact benchmark markdown section."""
    mean_smape = (
        horizon_table.groupby("model_name", as_index=False)["smape"].mean().sort_values("smape")
    )
    best_model = str(mean_smape.iloc[0]["model_name"])

    lines = [
        "## Benchmark Panel",
        f"- Series evaluated: {horizon_table['series_id'].nunique()}",
        f"- Mean best-performing model: {best_model}",
        "",
        "### Rank Associations (AMI/pAMI vs sMAPE)",
    ]

    for _, row in rank_associations.iterrows():
        lines.append(
            "- "
            f"model={row['model_name']} h={int(row['horizon'])}: "
            f"AMI={row['spearman_ami_smape']:.3f}, "
            f"pAMI={row['spearman_pami_smape']:.3f}, "
            f"delta={row['delta_pami_minus_ami']:.3f}"
        )

    return "\n".join(lines)


def build_frequency_panel_markdown(
    *,
    frequency_summary: pd.DataFrame,
) -> str:
    """Build frequency-wise benchmark summary markdown."""
    lines = ["## Frequency-wise Benchmark Panel"]
    for _, row in frequency_summary.iterrows():
        lines.append(
            "- "
            f"frequency={row['frequency']}, model={row['model_name']}, "
            f"mean_smape={row['mean_smape']:.3f}, "
            f"directness_ratio={row['directness_ratio']:.3f}"
        )
    return "\n".join(lines)


def build_linkedin_post(
    *,
    canonical_payloads: list[dict[str, object]],
) -> str:
    """Generate a professional LinkedIn draft (250-400 words)."""
    lookup = {str(p["series_name"]): cast(dict[str, Any], p) for p in canonical_payloads}

    sine_lags = lookup["sine_wave"]["interpretation"]["primary_lags"]
    air_regime = lookup["air_passengers"]["interpretation"]["modeling_regime"]
    henon_direct = lookup["henon_map"]["interpretation"]["directness_class"]
    stock_fore = lookup["simulated_stock_returns"]["interpretation"]["forecastability_class"]

    first_paragraph = (
        "A recent AMI-focused forecasting paper reinforces a practical point: "
        "before choosing a model, we should first estimate whether useful "
        "predictive structure exists at each horizon. In this project, we "
        "replicated that horizon-specific AMI screening workflow and then "
        "extended it with pAMI as a project-specific addition."
    )
    second_paragraph = (
        "In plain language, AMI captures total dependence between now and "
        "future horizons, while pAMI focuses on the dependence that remains "
        "after accounting for shorter lags. That distinction matters. It "
        "separates true direct lag effects from structure that is only "
        "inherited through intermediate lags."
    )
    canonical_paragraph = (
        "Canonical examples made the difference concrete. "
        "The sine-wave case showed strong short-lag structure with direct "
        f"lags such as {sine_lags}. "
        "AirPassengers stayed highly structured, but the recommended regime "
        f"was {air_regime}, "
        "highlighting that not all broad dependence implies a complex model. "
        f"The H\u00e9non map remained structured with {henon_direct} "
        "directness, which supports compact "
        "yet nonlinear lag designs. "
        f"Simulated stock returns landed in {stock_fore} forecastability, "
        "exactly where simple baselines "
        "should remain competitive."
    )
    takeaway_paragraph = (
        "The practical takeaway is that AMI is useful for triage, and pAMI is "
        "useful for lag selection and directness interpretation. Using both "
        "gives a cleaner path from diagnostics to model specification and helps "
        "explain when strong structure does not translate into lower forecast "
        "error."
    )
    implementation_paragraph = (
        "Operationally, this workflow was built as a reproducible pipeline: "
        "canonical diagnostics produce figures and JSON summaries, rolling-origin "
        "evaluation keeps diagnostics on pre-origin training windows, and model "
        "errors are scored strictly on holdout windows. That makes the narrative "
        "auditable, not just anecdotal, and supports practical decisions about "
        "when to stay simple and when to invest in richer model classes."
    )

    return (
        "# **Forecastability screening should come before model selection.**\n\n"
        f"{first_paragraph}\n\n"
        f"{second_paragraph}\n\n"
        f"{canonical_paragraph}\n\n"
        f"{takeaway_paragraph}\n\n"
        f"{implementation_paragraph}\n\n"
        "AMI for triage, pAMI for model specification"
    )


def mandatory_caveats() -> list[str]:
    """Return mandatory caveat statements required by the analysis plan."""
    return [
        "pAMI is a project extension, not a paper-native metric.",
        (
            "Current pAMI uses residualization plus nonlinear MI, so it is an "
            "approximation to full nonlinear conditional MI."
        ),
        "pAMI becomes more sample-hungry as lag and conditioning dimension increase.",
        "AMI and pAMI are ordinal diagnostics, not perfectly calibrated physical quantities.",
        "Canonical examples are interpretive only.",
        "Weak AMI-error correlation can be informative rather than a failure.",
    ]


def _fget(d: dict[str, object], key: str, default: float = 0.0) -> float:
    """Safely coerce a value from an untyped JSON dict to float.

    Args:
        d:       Source dictionary (values typed as ``object``).
        key:     Key to look up.
        default: Fallback when the key is absent or the value cannot be cast.

    Returns:
        Float value, or *default* on failure.
    """
    v = d.get(key, default)
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def build_exog_group_markdown(
    group_name: str,
    cases: list[dict[str, object]],
) -> str:
    """Build a grouped markdown report for one target series' exogenous analysis.

    Args:
        group_name:  Short target identifier, e.g. ``"aapl"`` or ``"bike_cnt"``.
        cases:       List of enriched JSON payloads for this target group, sorted
                     so that univariate comes first, noise comes last.

    Returns:
        Markdown string with univariate section, per-exog subsections, and a
        summary table.
    """
    surrogates_on = any(bool(c.get("compute_surrogates", False)) for c in cases)
    surr_state = "ON" if surrogates_on else "OFF"
    _note = (
        f"> Note: Surrogates are {surr_state} in this run. Significance counts reflect "
        "surrogate bands only when `compute_surrogates=True`. "
        "Recommended lags are heuristic (top 5 by pCrossAMI)."
    )
    lines: list[str] = [
        f"# {group_name} — Exogenous Dependency Analysis",
        "",
        _note,
        "",
    ]

    # ---- Univariate baseline section -------------------------------------
    lines.append("## Target Series — Univariate Baseline")
    lines.append("")
    uni = next((c for c in cases if str(c.get("exog_name", "")) == "none"), None)
    if uni is None:
        lines.append("No dedicated univariate case in this analysis.")
    else:
        u_auc_raw = _fget(uni, "auc_raw")
        u_auc_par = _fget(uni, "auc_partial")
        u_pk_raw_lag = uni.get("peak_raw_lag", "N/A")
        u_pk_raw_val = _fget(uni, "peak_raw_value")
        u_pk_par_lag = uni.get("peak_partial_lag", "N/A")
        u_pk_par_val = _fget(uni, "peak_partial_value")
        lines += [
            f"- Observations: {uni.get('n_target', 'N/A')}",
            f"- Mean AutoMI (lags 1–20): {_fget(uni, 'mean_raw_20'):.4f}",
            f"- Mean pAutoMI (lags 1–20): {_fget(uni, 'mean_partial_20'):.4f}",
            f"- AUC AutoMI: {u_auc_raw:.4f} | AUC pAutoMI: {u_auc_par:.4f}",
            f"- Peak AutoMI: lag {u_pk_raw_lag} ({u_pk_raw_val:.4f})",
            f"- Peak pAutoMI: lag {u_pk_par_lag} ({u_pk_par_val:.4f})",
            f"- Directness ratio: {_fget(uni, 'directness_ratio'):.4f}",
            f"- Triage: {uni.get('recommendation', 'N/A')}",
        ]
    lines.append("")

    # ---- Exogenous variables section -------------------------------------
    lines.append("## Exogenous Variables")
    lines.append("")

    noise_case = next(
        (c for c in cases if str(c.get("exog_name", "")) == "noise"),
        None,
    )
    noise_mean: float = _fget(noise_case, "mean_raw_20") if noise_case else 0.0

    # Non-noise, non-univariate cases first
    non_noise = [c for c in cases if str(c.get("exog_name", "")) not in {"none", "noise"}]
    for case in non_noise:
        exog_name = str(case.get("exog_name", "unknown"))
        lines.append(f"### {exog_name}")
        lines.append("")
        mean_raw = _fget(case, "mean_raw_20")
        if noise_mean > 1e-9:
            snr_val = mean_raw / noise_mean
            snr_str = f"{snr_val:.2f}×"
        else:
            snr_str = "∞"
        c_auc_raw = _fget(case, "auc_raw")
        c_auc_par = _fget(case, "auc_partial")
        c_pk_raw_lag = case.get("peak_raw_lag", "N/A")
        c_pk_raw_val = _fget(case, "peak_raw_value")
        c_pk_par_lag = case.get("peak_partial_lag", "N/A")
        c_pk_par_val = _fget(case, "peak_partial_value")
        c_n_tgt = case.get("n_target", "N/A")
        c_n_exog = case.get("n_exog", "N/A")
        lines += [
            f"- Mode: {case.get('mode', 'cross')}",
            f"- Observations: target={c_n_tgt}, exog={c_n_exog}",
            f"- Mean CrossMI (lags 1–20): {mean_raw:.4f}",
            f"- Mean pCrossAMI (lags 1–20): {_fget(case, 'mean_partial_20'):.4f}",
            f"- AUC CrossMI: {c_auc_raw:.4f} | AUC pCrossAMI: {c_auc_par:.4f}",
            f"- Peak CrossMI: lag {c_pk_raw_lag} ({c_pk_raw_val:.4f})",
            f"- Peak pCrossAMI: lag {c_pk_par_lag} ({c_pk_par_val:.4f})",
            f"- Directness ratio: {_fget(case, 'directness_ratio'):.4f}",
            f"- SNR vs noise: {snr_str} (noise Mean CrossMI: {noise_mean:.4f})",
            f"- Recommended lags (top 5 by pCrossAMI): {case.get('recommended_lags', [])}",
            f"- Recommendation: {case.get('recommendation', 'N/A')}",
            f"- Description: {case.get('description', '')}",
            "",
        ]

    # Noise case last
    if noise_case is not None:
        lines.append("### noise — Noise Control (baseline)")
        lines.append("")
        n_auc_raw = _fget(noise_case, "auc_raw")
        n_auc_par = _fget(noise_case, "auc_partial")
        n_pk_raw_lag = noise_case.get("peak_raw_lag", "N/A")
        n_pk_raw_val = _fget(noise_case, "peak_raw_value")
        n_pk_par_lag = noise_case.get("peak_partial_lag", "N/A")
        n_pk_par_val = _fget(noise_case, "peak_partial_value")
        n_n_tgt = noise_case.get("n_target", "N/A")
        n_n_exog = noise_case.get("n_exog", "N/A")
        lines += [
            f"- Mode: {noise_case.get('mode', 'cross')}",
            f"- Observations: target={n_n_tgt}, exog={n_n_exog}",
            f"- Mean CrossMI (lags 1–20): {_fget(noise_case, 'mean_raw_20'):.4f}",
            f"- Mean pCrossAMI (lags 1–20): {_fget(noise_case, 'mean_partial_20'):.4f}",
            f"- AUC CrossMI: {n_auc_raw:.4f} | AUC pCrossAMI: {n_auc_par:.4f}",
            f"- Peak CrossMI: lag {n_pk_raw_lag} ({n_pk_raw_val:.4f})",
            f"- Peak pCrossAMI: lag {n_pk_par_lag} ({n_pk_par_val:.4f})",
            f"- Description: {noise_case.get('description', '')}",
            "",
        ]

    # ---- Lag Selection Summary table -------------------------------------
    lines += [
        "## Lag Selection Summary",
        "",
        "| Variable | AUC (CrossMI) | AUC (pCrossAMI) | Peak Lag | Recommended Lags | SNR | Decision |",  # noqa: E501
        "|---|---|---|---|---|---|---|",
    ]

    all_exog_cases = [c for c in cases if str(c.get("exog_name", "")) != "none"]
    for case in all_exog_cases:
        exog_nm = str(case.get("exog_name", "unknown"))
        auc_r = _fget(case, "auc_raw")
        auc_p = _fget(case, "auc_partial")
        peak_lag = case.get("peak_raw_lag", "N/A")
        rec_lags = case.get("recommended_lags", [])
        mean_r = _fget(case, "mean_raw_20")
        if exog_nm == "noise":
            snr_col = "BASELINE"
            decision = "BASELINE"
        elif noise_mean > 1e-9:
            snr_v = mean_r / noise_mean
            snr_col = f"{snr_v:.2f}×"
            recommendation = str(case.get("recommendation", ""))
            if recommendation.upper().startswith("HIGH"):
                decision = "INCLUDE"
            elif recommendation.upper().startswith("MEDIUM"):
                decision = "CONSIDER"
            elif not surrogates_on and snr_v >= 10.0:
                decision = "CONSIDER (SNR)"
            elif not surrogates_on and snr_v >= 3.0:
                decision = "TEST (SNR)"
            else:
                decision = "DROP"
        else:
            snr_col = "∞"
            recommendation = str(case.get("recommendation", ""))
            if recommendation.upper().startswith("HIGH"):
                decision = "INCLUDE"
            elif recommendation.upper().startswith("MEDIUM"):
                decision = "CONSIDER"
            elif not surrogates_on:
                decision = "TEST"
            else:
                decision = "DROP"
        lines.append(
            f"| {exog_nm} | {auc_r:.4f} | {auc_p:.4f} | {peak_lag} | {rec_lags} | {snr_col} | {decision} |"  # noqa: E501
        )

    lines.append("")
    return "\n".join(lines)


def save_exog_reports(
    *,
    json_dir: Path,
    report_dir: Path,
) -> None:
    """Generate per-target-group exog markdown reports from saved JSON payloads.

    Reads all ``*.json`` files in *json_dir*, groups them by ``target_name``,
    builds a markdown report per group, and writes to *report_dir*.

    Args:
        json_dir:   Directory containing enriched exog JSON payloads.
        report_dir: Directory where per-group ``.md`` files are written.
    """
    report_dir.mkdir(parents=True, exist_ok=True)
    payloads: list[dict[str, object]] = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted(json_dir.glob("*.json"))
    ]

    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for p in payloads:
        key = str(p.get("target_name", p["case_name"]))
        groups[key].append(p)

    for group_name, cases in groups.items():

        def _sort_key(c: dict[str, object]) -> tuple[int, str]:
            exog = str(c.get("exog_name", ""))
            if exog == "none":
                return (0, exog)
            if exog == "noise":
                return (2, exog)
            return (1, exog)

        cases_sorted = sorted(cases, key=_sort_key)
        md = build_exog_group_markdown(group_name, cases_sorted)
        out_path = report_dir / f"{group_name}.md"
        out_path.write_text(md, encoding="utf-8")
        _logger.info("Saved exog report: %s", out_path)
