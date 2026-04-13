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
| Forecastability profile (F1) | Which horizons carry usable predictive information? | After AMI curves exist; before choosing which horizons to model | Profile object: peak horizon, informative horizon set, shape flags, recommendations | Narrows model evaluation to productive horizons; detects non-monotone seasonal structure | Inherits AMI estimator reliability; requires surrogates for epsilon anchoring |
| IT limit diagnostics (F2) | What is the theoretical ceiling on prediction improvement? | After forecastability profile; when "how much can we gain?" matters | Ceiling per horizon, compression/DPI warnings | Sets realistic expectations before model investment; flags information-destroying transforms | Ceiling holds under log loss only; exploitation ratio deferred (pre-model repo) |
| Predictive info learning curves (F3) | How many past lags does the series actually need? | Lookback/window-length selection before model training | Learning curve, plateau flag, recommended lookback, reliability warnings | Avoids over-long or too-short lookback windows | kNN MI unreliable for k > 5–8 at small n; mandatory reliability warnings |
| Spectral predictability (F4) | How much linear predictable structure exists? | When AMI is high but you want to check if simple linear models suffice | Scalar Ω in [0,1] | Quick check: if Ω high and AMI high → linear models may be enough. If AMI ≫ Ω → nonlinear methods needed | Captures linear structure only; non-stationary series need detrending |
| Largest Lyapunov exponent (F5) | Does this series show sensitivity to initial conditions? | Expert-level chaos detection; experimental use only | λ estimate + experimental flag | Differentiates deterministic chaos from stochastic noise (when sample size permits) | Experimental — unreliable at finite sample sizes; gated behind config flag; never auto-included in triage score |
| Entropy-based complexity (F6) | Is this series periodic, chaotic, or stochastic? | Complexity-band screening before choosing model family | PE, SE, complexity band (low/medium/high) | Fast regime classification; complements AMI with amplitude-blind ordinal structure | PE is amplitude-blind; tie-breaking rule must be fixed |
| Batch diagnostic ranking (F7) | Which of my 50+ signals should I model first? | Portfolio-level signal prioritization | Ranked table with full diagnostic vector per signal | Objective multi-criteria ranking across an entire signal portfolio | Composite weighting across incommensurable scales must be transparent |
| Exogenous screening with FDR (F8) | Which external drivers add genuine predictive value after redundancy? | Multivariate feature selection before model engineering | Per-driver score by horizon, redundancy flags, BH-corrected significance | Prunes redundant drivers; controls false discovery rate across many tests | Greedy forward selection; redundancy penalty is configurable approximation |
| Optional narration | How should deterministic outputs be explained to non-specialists? | Stakeholder communication when numeric outputs already exist | Natural-language summary grounded in computed metrics | Faster cross-functional handoff (operations, maintenance, planning) | Communication layer only; it does not create or validate numeric results |

## Do Not Use This For

- Proving physical causality between variables.
- Replacing rolling-origin forecast evaluation and business KPI tracking.
- Setting maintenance policy thresholds without domain constraints and risk-cost modeling.
- Comparing very short windows where minimum sample assumptions are not met.
- Treating pAMI as an exact nonlinear conditional mutual information estimate.
- Treating experimental diagnostics (F5 Lyapunov) as automated decision criteria without expert review.
- Using learning curve plateaus (F3) as proof of information exhaustion — estimator saturation can mimic genuine plateaus.
