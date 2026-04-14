<!-- type: reference -->
# Exogenous benchmark workflow

This workflow extends the repository with a fixed exogenous benchmark slice built from existing local real-data pairs and deterministic noise controls.

Disclosure:
- Exogenous cross-dependence analysis is a project extension.
- Conditioned pCrossAMI reporting is a project extension.
- The paper-aligned M4 benchmark workflow remains unchanged.

## Slice definition

The fixed slice is:
- `bike_cnt_temp`
- `bike_cnt_hum`
- `bike_cnt_noise`
- `aapl_spy`
- `aapl_noise`
- `btc_eth`
- `btc_noise`

Noise controls use the local `data/raw/exog/noise_control.csv` series, tail-aligned to the target length.

## Leakage boundary

- Rolling-origin splits are built on the target series length.
- For each origin and horizon, raw CrossMI and conditioned pCrossAMI are computed on the train window only.
- No holdout observations are used in exogenous diagnostics.
- Holdout scoring is not part of this workflow; it is strictly a diagnostic benchmark extension.

## Outputs

Run:

```bash
MPLBACKEND=Agg uv run python scripts/archive/run_benchmark_exog_panel.py
```

Artifacts:
- `outputs/tables/exog_benchmark/horizon_table.csv`
- `outputs/tables/exog_benchmark/case_summary.csv`
- `outputs/figures/exog_benchmark/raw_vs_conditioned.png`
- `outputs/reports/benchmark_exog_panel.md`

## Interpretation

- `raw_cross_mi` is descriptive total cross-dependence.
- `conditioned_cross_mi` is conditioned cross-dependence after removing intermediate target-lag mediation.
- The workflow is intended as both descriptive analysis and bounded model-selection guidance.
- Any `directness_ratio > 1.0` is treated as a warning condition only, not a scientific conclusion.
