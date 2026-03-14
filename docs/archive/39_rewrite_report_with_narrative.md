# 39. Rewrite Report with Narrative and Figure References (P2)

> **Priority**: P2 — depends on P1 (benchmark results on real data must exist first).

## Problem

The current `outputs/reports/ami_to_pami_report.md` is a **data dump**: it lists raw numbers
(n_sig_ami, directness_ratio, etc.) without narrative interpretation. It does not embed or
reference any figures. It does not compare series against each other or explain what pAMI
adds beyond AMI in plain language.

The report should read as a coherent analysis narrative that a colleague could follow without
looking at the code.

## What to do

- [ ] Rewrite `build_report_artifacts.py` report-building section
- [ ] Add figure embedding (relative markdown image links)
- [ ] Add cross-series comparison narrative
- [ ] Add a "what pAMI adds" summary section
- [ ] Add benchmark panel interpretation (not just raw numbers)
- [ ] Ensure all mandatory caveats remain included

## Report structure (target)

The final `ami_to_pami_report.md` should have this structure:

```markdown
# AMI → pAMI Forecastability Analysis Report

> Disclosure: AMI is paper-aligned; pAMI is a project extension, not paper-native.

## Executive Summary
  2-3 paragraph overview of findings

## Methodology
  - AMI: per-horizon kNN MI (k=8)
  - pAMI: linear residualisation + kNN MI
  - Surrogate significance: phase-randomised, n=99, α=5% two-sided
  - Rolling-origin: expanding window, diagnostics on train only

## Canonical Examples

### Sine Wave
  Narrative paragraph + key numbers + figure reference

### Air Passengers
  ...

### Hénon Map
  ...

### Simulated Stock Returns
  ...

## Cross-Series Comparison
  Table comparing directness_ratio, forecastability_class, etc.
  Narrative interpreting the pattern

## Benchmark Panel (M4)
  - How many series, which frequencies
  - Rank association results and what they mean
  - Tercile analysis summary
  - Frequency-wise breakdown

## What pAMI Adds Beyond AMI
  2-3 paragraphs synthesising the evidence

## Caveats
  Mandatory caveats from reporting.mandatory_caveats()

## References
  - arXiv paper citation
```

## Where to make changes

The report generation logic lives in `scripts/build_report_artifacts.py`. The current
implementation builds `sections: list[str]` by appending raw data. You need to replace
this data-dump approach with narrative text.

### Current code to replace (in `scripts/build_report_artifacts.py`)

The section starting at approximately **line 44** builds the report. The key area to
change is the canonical examples loop (lines ~62-90) and the benchmark section.

### New canonical section builder

Replace the raw-number dump with a narrative function. Add this helper to
`scripts/build_report_artifacts.py`:

```python
def _canonical_narrative(payload: dict) -> str:
    """Build a narrative paragraph for one canonical example."""
    s = payload["summary"]
    i = payload["interpretation"]
    name = payload["series_name"]

    lines = [
        f"### {name}",
        "",
        f"![{name} AMI vs pAMI](../figures/canonical/{name}_overlay.png)",
        "",
        f"**Forecastability class**: {i['forecastability_class']}  ",
        f"**Directness class**: {i['directness_class']}  ",
        f"**Recommended modelling regime**: {i['modeling_regime']}",
        "",
        f"AMI identifies {s['n_sig_ami']} significant lags (peak at lag {s['peak_lag_ami']}), "
        f"while pAMI retains only {s['n_sig_pami']} "
        f"(peak at lag {s['peak_lag_pami']}). "
        f"The directness ratio of {s['directness_ratio']:.3f} indicates that "
        f"{'most dependence is mediated through intermediate lags' if s['directness_ratio'] < 0.3 else 'substantial direct dependence persists beyond the first lag'}.",
        "",
        f"{i['narrative']}",
        "",
        f"![{name} AMI−pAMI difference](../figures/canonical/{name}_ami_minus_pami.png)",
    ]
    return "\n".join(lines)
```

### Cross-series comparison table

Add after the canonical examples section:

```python
def _cross_series_table(payloads: list[dict]) -> str:
    """Build a markdown comparison table across canonical examples."""
    lines = [
        "## Cross-Series Comparison",
        "",
        "| Series | Forecastability | Directness | n_sig AMI | n_sig pAMI | Directness Ratio | Regime |",
        "|--------|----------------|------------|-----------|------------|------------------|--------|",
    ]
    for p in payloads:
        s, i = p["summary"], p["interpretation"]
        lines.append(
            f"| {p['series_name']} "
            f"| {i['forecastability_class']} "
            f"| {i['directness_class']} "
            f"| {s['n_sig_ami']} "
            f"| {s['n_sig_pami']} "
            f"| {s['directness_ratio']:.3f} "
            f"| {i['modeling_regime']} |"
        )
    lines.extend([
        "",
        "The table highlights the key pattern: AMI provides broad screening "
        "(high/medium/low forecastability), while pAMI refines the interpretation "
        "by quantifying how much structure is direct versus mediated. "
        "Low directness ratios (sine wave, air passengers) indicate that compact "
        "lag models can capture most of the predictive content, while high "
        "directness ratios (Hénon map) justify richer lag structures.",
    ])
    return "\n".join(lines)
```

### Benchmark section with narrative

Replace the raw rank-association dump in `build_report_artifacts.py`:

```python
def _benchmark_narrative(
    horizon_table: pd.DataFrame,
    rank_associations: pd.DataFrame,
    frequency_panel: pd.DataFrame,
) -> str:
    """Build a narrative benchmark section."""
    n_series = horizon_table["series_id"].nunique()
    freqs = sorted(horizon_table["frequency"].unique())

    mean_rho_ami = rank_associations["spearman_ami_smape"].mean()
    mean_rho_pami = rank_associations["spearman_pami_smape"].mean()
    mean_delta = rank_associations["delta_pami_minus_ami"].mean()

    lines = [
        "## Benchmark Panel (M4 Competition Data)",
        "",
        f"The rolling-origin benchmark evaluated **{n_series} series** across "
        f"frequencies: {', '.join(freqs)}.",
        "",
        f"![Rank Association Deltas](../figures/rank_association_delta.png)",
        "",
        "### Rank Associations (AMI/pAMI vs sMAPE)",
        "",
        f"Mean Spearman ρ(AMI, sMAPE) = **{mean_rho_ami:.3f}**  ",
        f"Mean Spearman ρ(pAMI, sMAPE) = **{mean_rho_pami:.3f}**  ",
        f"Mean Δ(pAMI − AMI) = **{mean_delta:.3f}**",
        "",
    ]

    if mean_delta < -0.05:
        lines.append(
            "pAMI shows a **stronger** negative correlation with forecast error "
            "than AMI on average, suggesting pAMI is a better predictor of "
            "achievable forecast accuracy."
        )
    elif mean_delta > 0.05:
        lines.append(
            "AMI shows a **stronger** negative correlation with forecast error "
            "than pAMI on average. This is expected for short horizons where "
            "conditioning has limited effect."
        )
    else:
        lines.append(
            "AMI and pAMI show **comparable** rank correlations with forecast "
            "error. The distinction becomes more important at specific horizons."
        )

    lines.extend([
        "",
        f"![Frequency Panel](../figures/frequency_panel.png)",
        "",
        "### Frequency-wise Summary",
        "",
    ])
    for _, row in frequency_panel.iterrows():
        lines.append(
            f"- **{row['frequency']}** ({row['model_name']}): "
            f"mean sMAPE = {row['mean_smape']:.2f}, "
            f"directness ratio = {row['directness_ratio']:.3f}"
        )

    return "\n".join(lines)
```

### Assembling the final report

Replace the current `sections.extend(...)` chain with:

```python
    sections: list[str] = [
        "# AMI → pAMI Forecastability Analysis Report",
        "",
        "> Disclosure: AMI is paper-aligned; pAMI is a project extension, not paper-native.",
        "",
        "## Executive Summary",
        "",
        # TODO: generate this from the data — 2-3 paragraphs
        "This report presents horizon-specific forecastability analysis using AMI "
        "(Auto-Mutual Information) and its extension pAMI (partial AMI) across "
        "four canonical interpretive examples and a benchmark panel of M4 "
        "competition series.",
        "",
        "## Methodology",
        "",
        "- AMI and pAMI computed per horizon using kNN MI (k=8)",
        "- Significance: phase-randomised surrogates (n=99), α=5% two-sided",
        "- Rolling-origin evaluation: expanding window, diagnostics on train only",
        "- Forecast error (sMAPE) scored on post-origin holdout only",
        "",
        "## Canonical Examples",
        "",
    ]

    for payload in canonical_payloads:
        sections.append(_canonical_narrative(payload))
        sections.append("")

    sections.append(_cross_series_table(canonical_payloads))
    sections.append("")

    sections.append(
        _benchmark_narrative(horizon_table, rank_associations, frequency_panel)
    )
    sections.append("")

    sections.extend([
        "## What pAMI Adds Beyond AMI",
        "",
        "1. **Lag selection**: pAMI identifies which lags carry *direct* predictive "
        "information, filtering out mediated dependence that inflates AMI.",
        "2. **Model complexity guidance**: low directness ratio → compact models; "
        "high directness ratio → richer lag structures.",
        "3. **Overfitting risk flag**: when many AMI-significant lags collapse to "
        "few pAMI-significant lags, including all AMI lags risks overfitting.",
        "",
        "## Caveats",
        "",
        *[f"- {line}" for line in mandatory_caveats()],
        "",
        "## References",
        "",
        "- Bandt, C. (2025). *Auto-Mutual Information for Lag Selection and "
        "Seasonality Testing.* arXiv:2601.10006.",
    ])
```

## Verification

After rebuilding:

```bash
MPLBACKEND=Agg uv run python scripts/build_report_artifacts.py
```

- [ ] Report contains `## Executive Summary`
- [ ] Report contains embedded figure references (`![...](../figures/...)`)
- [ ] Report contains `## Cross-Series Comparison` with a markdown table
- [ ] Report contains `## What pAMI Adds Beyond AMI`
- [ ] Report contains `## References` with arXiv citation
- [ ] All figure paths in the report correspond to existing files in `outputs/figures/`
- [ ] Word count of the report is ≥ 500 words (vs current ~200)
