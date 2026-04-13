<!-- type: explanation -->
# Exogenous Analysis Notebook: Durable Summary

## Purpose

Provide a stable narrative summary of the exogenous screening workflow so users can decide which external drivers are worth modeling before opening the full notebook.

Scope covered:
- CrossAMI and pCrossAMI for target-driver pairs,
- warning-aware ranking behavior,
- screening decisions for keep, review, or deprioritize.

## Key Figure

![Raw versus conditioned cross-dependence](../../outputs/figures/exog_benchmark/raw_vs_conditioned.png)

Figure source: [../../outputs/figures/exog_benchmark/raw_vs_conditioned.png](../../outputs/figures/exog_benchmark/raw_vs_conditioned.png)

Why this figure matters: it contrasts raw cross-signal against conditioned cross-signal by case, making actionable exogenous candidates visible at a glance.

## Key Result

From [../../outputs/tables/exog_benchmark/case_summary.csv](../../outputs/tables/exog_benchmark/case_summary.csv):

- bike_cnt_temp is the strongest practical driver candidate: mean raw CrossMI = 0.0906, mean conditioned CrossMI = 0.0523, warning horizons = 0.
- bike_cnt_noise is weak and unstable: mean raw CrossMI = 0.00157, mean conditioned CrossMI = 0.00237, warning horizons = 4.
- Six of seven benchmark pairs carry at least one directness warning horizon, so directness > 1.0 is handled as a diagnostic warning rather than a strength claim.

## Takeaways

- Rank exogenous drivers by conditioned signal strength and warning counts together.
- Treat directness anomalies as estimation-risk flags, not performance evidence.
- Prefer driver candidates that stay informative across horizons with low warning burden.
- Preserve rolling-origin train-only diagnostics for leakage-safe screening.

## Notebook For Full Detail

- Full walkthrough: [../../notebooks/walkthroughs/02_exogenous_analysis.ipynb](../../notebooks/walkthroughs/02_exogenous_analysis.ipynb)
