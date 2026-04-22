---
applyTo: "scripts/**,outputs/**,configs/**"
---

# Analyst Agent

You are the analysis execution agent for the AMI → pAMI Forecastability Analysis project.
Your role is to run scripts, interpret numerical outputs, and answer the six interpretive
questions for each canonical example.

## Execution order

Run scripts strictly in this order — each builds on the previous:

```bash
MPLBACKEND=Agg uv run python scripts/run_canonical_triage.py
MPLBACKEND=Agg uv run python scripts/run_benchmark_panel.py
MPLBACKEND=Agg uv run python scripts/build_report_artifacts.py
```

## Pre-run checklist
- [ ] Confirm `outputs/figures/canonical/` directory is writable
- [ ] Confirm `outputs/json/canonical/` directory exists
- [ ] Confirm `outputs/tables/benchmark/` directory exists
- [ ] Confirm `uv sync` has been run and all dependencies are present

## Post-run verification

After `run_canonical_triage.py`:
- [ ] 4 canonical JSON files exist with non-empty `interpretation` and `summary`
- [ ] Figures exist for each of the 4 examples (canonical, overlay, diff)
- [ ] `interpretation.forecastability_class` is `'low'` for stock returns
- [ ] `interpretation.forecastability_class` is `'high'` for sine and air_passengers

After `run_benchmark_panel.py`:
- [ ] `horizon_table.csv` has columns: `series_id`, `frequency`, `model_name`, `horizon`, `ami`, `pami`, `smape`
- [ ] `rank_associations.csv` has Spearman columns `spearman_ami_smape` and `spearman_pami_smape`
- [ ] Tercile CSVs are non-empty

After `build_report_artifacts.py`:
- [ ] `ami_to_pami_report.md` exists and contains all four series summaries
- [ ] `linkedin_post.md` exists and is ≥ 200 words

## Six interpretive questions per canonical example

Answer these for each of the four series after outputs are generated:

1. **What does the AMI profile reveal about overall forecastability?**
   — Is `forecastability_class` high / medium / low? What is `auc_ami`?

2. **What does pAMI reveal beyond AMI?**
   — Is `directness_ratio` consistent with mediated or direct dependence?

3. **Which lags are actionable for model specification?**
   — Report `primary_lags` from `InterpretationResult`

4. **What model class is recommended?**
   — Cite the `pattern` (A–E) and the `narrative` field

5. **Is there evidence of exploitability mismatch (Pattern E)?**
   — Compare ETS vs naive sMAPE; flag if AMI is high but ETS does not outperform

6. **How do the surrogate bands contextualise the result?**
   — How many lags exceed the 97.5th percentile band for AMI and pAMI?

## Config files

- `configs/canonical_examples.yaml` — controls which series run, max_lag, k, n_surrogates
- `configs/benchmark_panel.yaml` — controls series, n_origins, horizons, models
- `configs/interpretation_rules.yaml` — threshold constants documented for reference

## Common issues

- Scripts should run with `MPLBACKEND=Agg` by default; if figures are missing, confirm backend override is not forcing an interactive backend.
- If `rank_associations.csv` shows all NaN, the series panel may have too few rows
  (add more series to `configs/benchmark_panel.yaml`)
- If `build_report_artifacts.py` prints `WARNING: canonical JSON not found`, run step 1 first
