<!-- type: explanation -->
# Results Summary

> [!IMPORTANT]
> AMI is paper-aligned (horizon-specific, kNN-based, with phase-surrogate significance bands).
>
> [!IMPORTANT]
> pAMI is a project extension, not a paper-native metric. It uses linear residualisation, so nonlinear mediation is not removed.

This page is a compact, decision-first evidence layer. Notebooks are linked as deep evidence, not as the primary source.

## 1) Univariate AMI/pAMI findings

- Dataset: 8 canonical univariate series (`sine_wave`, `air_passengers`, `henon_map`, `simulated_stock_returns`, `bitcoin_returns`, `gold_returns`, `crude_oil_returns`, `aapl_returns`).
- Evaluation protocol: horizon-specific AMI/pAMI curves generated in the canonical pipeline and summarised in [../outputs/json/canonical_examples_summary.json](../outputs/json/canonical_examples_summary.json), with methodology details in [../outputs/reports/ami_to_pami_report.md](../outputs/reports/ami_to_pami_report.md).
- What decision was improved: model-family triage became more explicit. In the current run, 2/8 series are `forecastability_class=high`, 1/8 is `medium`, and 5/8 are `low`, which supports separating rich-model candidates from baseline-first candidates before model search. Very low `directness_ratio` in `sine_wave` (0.0157) and `air_passengers` (0.0993) supports compact structured models over long-lag complexity.
- What limitation remains: significance counts are currently zero across this canonical summary (`n_sig_ami=0`, `n_sig_pami=0` for all 8), so actionable lag decisions should rely on class-level screening plus domain checks rather than significance-lag selection alone.

## 2) Exogenous screening findings

- Dataset: 7 target-driver benchmark cases (`bike_cnt_temp`, `bike_cnt_hum`, `bike_cnt_noise`, `aapl_spy`, `aapl_noise`, `btc_eth`, `btc_noise`).
- Evaluation protocol: rolling-origin exogenous screening using raw CrossMI and conditioned pCrossAMI with horizon-level outputs in [../outputs/tables/exog_benchmark/horizon_table.csv](../outputs/tables/exog_benchmark/horizon_table.csv) and case aggregates in [../outputs/tables/exog_benchmark/case_summary.csv](../outputs/tables/exog_benchmark/case_summary.csv).
- What decision was improved: driver prioritisation is more robust. `bike_cnt_temp` has the strongest useful signal (`mean_raw_cross_mi=0.0906`, `mean_conditioned_cross_mi=0.0523`, no warning horizons), while multiple noise-linked cases can be deprioritised early.
- What limitation remains: directness can be numerically unstable when raw dependence is close to zero. In this slice, 6/7 cases have warning horizons and at least one `directness_ratio > 1.0`, which should be treated as an estimation warning, not scientific evidence of stronger conditioned dependence.

## 3) Triage workflow findings

- Dataset: deterministic triage regression inputs in [../tests/test_triage_regression.py](../tests/test_triage_regression.py) (AR(1), white noise, trend+seasonal, and exogenous AR(1)+noise), with broader walkthrough coverage in [../notebooks/03_agentic_triage.ipynb](../notebooks/03_agentic_triage.ipynb).
- Evaluation protocol: one-entry-point orchestration (`run_triage`) with staged readiness, routing, compute, and interpretation checks validated in [../tests/test_triage_run.py](../tests/test_triage_run.py), [../tests/test_triage_router.py](../tests/test_triage_router.py), and [../tests/test_triage_readiness.py](../tests/test_triage_readiness.py).
- What decision was improved: earlier go/no-go and route decisions before expensive modelling. The workflow blocks infeasible requests, routes exogenous requests separately, and preserves stable screening behavior (`AR(1) -> high`, `white_noise -> low`) in regression tests.
- What limitation remains: when data are significance-infeasible (for example n=150 in regression tests), surrogates are skipped and decisions are route/class screening only. This workflow supports prioritisation and method selection, not guaranteed downstream forecast accuracy gains.

## Decision-Relevant Outcomes

| Area | Dataset | Evaluation protocol | Decision improved | Limitation remains |
|---|---|---|---|---|
| Univariate AMI/pAMI | 8 canonical series | Horizon-specific AMI/pAMI pipeline summary | Separate high/medium/low forecastability candidates before model search; identify mediated vs direct structure via `directness_ratio` | Current canonical summary has zero significant lags, so lag-level claims stay conservative |
| Exogenous screening | 7 target-driver pairs | Rolling-origin CrossMI and conditioned pCrossAMI across fixed horizons | Prioritise drivers with persistent conditioned signal (e.g., `bike_cnt_temp`) and deprioritise noise controls | `directness_ratio > 1.0` appears in warning cases; treat as diagnostic instability |
| Triage workflow | Canonical + exogenous triage regression inputs | Deterministic staged orchestration (`readiness -> routing -> compute -> interpretation`) | Early stop/routing reduces wasted modelling effort and enforces consistent screening paths | Route/class outputs are triage diagnostics, not direct proof of forecast error improvement |

## Deep Evidence (Secondary)

- [../notebooks/01_canonical_forecastability.ipynb](../notebooks/01_canonical_forecastability.ipynb)
- [../notebooks/02_exogenous_analysis.ipynb](../notebooks/02_exogenous_analysis.ipynb)
- [../notebooks/03_agentic_triage.ipynb](../notebooks/03_agentic_triage.ipynb)
