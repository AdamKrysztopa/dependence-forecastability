<!-- type: explanation -->
# Why Use This

This project separates several dependence diagnostics so teams can choose the smallest useful workflow for a decision, not the largest workflow available.

## Component Comparison Matrix

| Component | Question answered | When to use | Output type | Industrial value | Caveats |
|---|---|---|---|---|---|
| AMI | Is there horizon-specific dependence worth exploiting at all? | First-pass screening of a target signal before model search | Lag curve, AUC summary, significance bands | Fast go/no-go signal for forecastability work on a line, asset, or process | Detects dependence, not causality or guaranteed model gains |
| pAMI | How much dependence remains after removing linear mediation through intermediate lags? | After AMI is non-trivial and you need direct vs mediated lag structure | Partial lag curve, AUC summary | Helps reduce over-complex lag sets and prioritize direct signals | Linear approximation to conditional MI; can under-capture nonlinear mediation |
| directness_ratio | What share of total dependence appears direct? | Portfolio-level triage or quick comparison between windows, sensors, or assets | Scalar ratio: `AUC(pAMI) / AUC(AMI)` | Compact ranking signal for where direct structure is strong enough to operationalize | Diagnostic ratio only; unstable on weak/noisy short windows |
| Exogenous analysis | Which external drivers show lead-lag signal with the target? | Driver screening before multivariate forecasting or feature engineering | CrossAMI and pCrossAMI curves + ranked drivers | Narrows candidate driver set and reduces modeling iteration cost | Association-based screening; confounding and common-cause effects can remain |
| Triage | Is the signal ready for dependence analysis, and which method path should run? | Standardized entry point for production-like checks and repeatable diagnostics | Deterministic readiness flags, interpretation class, recommendations | Consistent gate before expensive model development across teams | Not a replacement for full backtesting or deployment validation |
| Optional narration | How should deterministic outputs be explained to non-specialists? | Stakeholder communication when numeric outputs already exist | Natural-language summary grounded in computed metrics | Faster cross-functional handoff (operations, maintenance, planning) | Communication layer only; it does not create or validate numeric results |

## Do Not Use This For

- Proving physical causality between variables.
- Replacing rolling-origin forecast evaluation and business KPI tracking.
- Setting maintenance policy thresholds without domain constraints and risk-cost modeling.
- Comparing very short windows where minimum sample assumptions are not met.
- Treating pAMI as an exact nonlinear conditional mutual information estimate.
