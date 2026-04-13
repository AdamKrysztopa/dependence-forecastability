<!-- type: reference -->
# Diagnostics Matrix

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.

This page is the evaluator-facing index for all F1–F8 diagnostics. For the surface
model (CLI, API, MCP, agents), see the companion [surface_guide.md](surface_guide.md).

---

## Quick reference

| Code | Name | Stability | Module |
|---|---|---|---|
| F1 | Forecastability Profile | stable | `triage/forecastability_profile.py` |
| F2 | Theoretical Limit Diagnostics | stable | `triage/theoretical_limit_diagnostics.py` |
| F3 | Predictive Information Learning Curves | stable | `triage/predictive_info_learning_curve.py` |
| F4 | Spectral Predictability Score | stable | `triage/spectral_predictability.py` |
| F5 | Largest Lyapunov Exponent | **experimental** | `triage/lyapunov.py` |
| F6 | Entropy-Complexity Band | stable | `triage/complexity_band.py` |
| F7 | Batch Triage and Multi-Series Ranking | stable | `triage/batch_models.py` |
| F8 | Exogenous Screening | stable | `extensions.py` |

> [!IMPORTANT]
> **F5 is experimental.** It is gated behind `experimental: true` at the config
> level and is **excluded from automated triage or ranking decisions** in F7.
> No stability guarantee applies. See the F5 entry below for full caveats.

---

## F1 — Forecastability Profile (AMI/pAMI curve)

**What it measures.** The horizon-wise mutual information between $X_t$ and its
own future $X_{t+h}$ (AMI) and the approximate direct-dependence residual (pAMI),
producing the informative horizon set $\mathcal{H}_\varepsilon$ and structural shape
flags for the triage decision.

**Stability:** stable

**When to use it.**
- As the primary output for any univariate forecastability assessment.
- When you need to know which forecast horizons carry detectable predictive signal
  above the noise floor.
- At the start of any triage pass; F1 is the anchor all other diagnostics
  contextualise.

**When to avoid it.**
- Directly at horizons beyond the frequency-specific cap (Yearly 6, Quarterly 8,
  Monthly 18, Weekly 13, Daily 14, Hourly 48): AMI values beyond these caps are
  unreliable.
- For series shorter than the recommended minimum (approximately 3× the maximum
  evaluation horizon).
- As the sole decision-maker when surrogate significance bands are unavailable
  (too-short series): treat the curve as indicative, not authoritative.

**Learn more.**
- [theory/forecastability_profile.md](theory/forecastability_profile.md) — profile
  construction, informative horizon set, epsilon resolution, DPI diagnostic
- [theory/foundations.md](theory/foundations.md) — AMI and pAMI definitions,
  significance logic, rolling-origin invariants

---

## F2 — Theoretical Limit Diagnostics

**What it measures.** The information-theoretic upper bound on forecastability
derived from the AMI curve, including compression ratio and predictability ceiling,
to quantify how close any model can get to the fundamental limit.

**Stability:** stable

**When to use it.**
- When you want to know *why* AMI is low — limit compression reveals whether the
  ceiling is genuinely low (hard limit) or whether the sampled curve has not
  saturated the limit.
- When comparing multiple series: the compression ratio (observed AMI / limit) is
  a cross-series comparable metric.
- Before investing in complex models: if the limit is low, model engineering gains
  diminish rapidly.

**When to avoid it.**
- As a standalone decision without F1: the limit is derived from the AMI curve, so
  F1 evidence is prerequisite context.
- When series length is very short: finite-sample bias inflates the estimated limit.

**Learn more.**
- [theory/foundations.md](theory/foundations.md) — AMI foundations and estimator
  properties

---

## F3 — Predictive Information Learning Curves

**What it measures.** The mutual information between a $k$-step past embedding and
the one-step-ahead future, evaluated for $k = 1 \ldots K$, to identify the minimal
sufficient lookback length where additional history yields negligible extra
predictive information.

**Stability:** stable

**When to use it.**
- When selecting the lookback window for a forecasting model: use the recommended
  plateau $k^*$ as a principled starting point.
- When you suspect that longer lags add noise rather than signal (the curve never
  plateauing is also informative).
- In combination with F1: F1 identifies *which* horizons are informative; F3
  identifies *how much* history informs the one-step horizon.

**When to avoid it.**
- As a standalone triage decision: F3 produces a curve and a lookback recommendation,
  not a scalar forecastability score.
- For embedding dimension $k > 5$–$8$ unless the series is very long ($n > 1000$):
  kNN estimators degrade in high-dimensional spaces; a hard cap $k_{\max} = 8$ is
  enforced.
- For non-stationary series: random-walk-like dynamics produce inflated estimates
  that grow with $k$ without plateauing.

**Learn more.**
- [triage_methods/predictive_information_learning_curves.md](triage_methods/predictive_information_learning_curves.md)
  — EvoRate definition, plateau detection, kNN curse of dimensionality warning

---

## F4 — Spectral Predictability Score (Ω)

**What it measures.** The concentration of spectral power across frequency bins,
normalised to $[0, 1]$: Ω = 1 for a perfectly periodic signal, Ω → 0 for white
noise, quantifying linear-structure predictability independently of AMI.

**Stability:** stable

**When to use it.**
- To characterise the *linear* spectral structure of a series as complementary
  context alongside the *nonlinear* AMI profile.
- When a divergence between high AMI and low Ω arises: this pattern signals that
  predictability comes from nonlinear dynamics, not spectral structure.
- For rapid cross-series ranking where a computationally cheap linear-domain
  signal is sufficient.

**When to avoid it.**
- As the sole forecastability measure: Ω misses nonlinear dependence entirely.
- For short series ($n < 128$): Welch PSD estimates are based on very few segments
  and Ω values are unreliable as anything other than a coarse indicator.
- For strongly non-stationary series without prior detrending.

**Learn more.**
- [theory/spectral_predictability.md](theory/spectral_predictability.md) — Ω formula,
  PSD normalisation, interpretation table, limitations

---

## F5 — Largest Lyapunov Exponent

> [!WARNING]
> **Experimental feature.** Largest Lyapunov exponent (LLE) is numerically fragile,
> excluded from automated triage decisions, and gated behind `experimental: true`
> in the config. No stability guarantee. Always combine with AMI/pAMI evidence and
> the F6 complexity band before drawing any conclusion.

**What it measures.** The average rate of exponential divergence of nearby
trajectories in a reconstructed phase space (Takens delay embedding + Rosenstein
algorithm), yielding $\hat{\lambda}$: positive values are *consistent with* chaotic
dynamics, but stochastic noise can also produce positive values.

**Stability:** **experimental — excluded from automated triage**

**When to use it.**
- Exploratory research only: as one piece of converging evidence that a series may
  exhibit chaotic dynamics, always alongside F1 and F6.
- When the series is long ($n \gg 1000$ for the default embedding dimension $m = 3$)
  and approximately stationary.

**When to avoid it.**
- In automated batch ranking (F7): LLE is excluded by design.
- For series with $n < 1000$: phase-space coverage is insufficient and the estimate
  is indicative only.
- As a causal or classification proof: a positive $\hat{\lambda}$ does not distinguish
  deterministic chaos from coloured stochastic noise.

**Learn more.**
- [triage_methods/largest_lyapunov_exponent.md](triage_methods/largest_lyapunov_exponent.md)
  — Takens embedding, Rosenstein algorithm, Theiler window, sample-size requirements

---

## F6 — Entropy-Complexity Band

**What it measures.** The normalised permutation entropy and spectral entropy of
the series, combined to classify its disorder level into a complexity band
(regular / moderate / noise-like), providing structural context for the AMI results.

**Stability:** stable

**When to use it.**
- To contextualise F1 AMI results: high AMI with low complexity typically indicates
  regular, easily modelled dynamics; high AMI with high complexity suggests
  potentially nonlinear or chaotic behaviour.
- As a cheap pre-model screening step to set expectations for model difficulty.
- Alongside F5 (when enabled) for convergence evidence on chaos vs stochasticity.

**When to avoid it.**
- As a sole decision-maker: F6 is a complementary contextual tool, not a
  forecastability measure. The forecastability ceiling is set by AMI, not entropy.
- For very short series: permutation entropy requires adequate pattern-frequency
  estimates; for $m = 5$, at least $n \approx 600$ is recommended.

**Learn more.**
- [theory/entropy_based_complexity.md](theory/entropy_based_complexity.md) — permutation
  entropy definition, embedding order selection, spectral entropy, complexity band
  classification

---

## F7 — Batch Triage and Multi-Series Ranking

**What it measures.** Runs F1–F4 and F6 deterministically across a panel of series
and produces a ranked diagnostic table, enabling rapid comparison of forecastability
structure across many signals in one pass.

**Stability:** stable

**When to use it.**
- When screening a large panel of candidate series to prioritise modelling effort.
- When producing a reproducible ranking artefact for a report or downstream pipeline.
- As the entry point for any multi-series analysis; individual series results remain
  accessible through the batch result object.

**When to avoid it.**
- When F5 output is desired in the ranking: LLE is intentionally excluded from
  automated batch triage by design.
- As a replacement for individual deep-dive analysis on flagged series: batch ranking
  surfaces which series to investigate, not why.

**Learn more.**
- `triage/batch_models.py` source for the batch result schema
- [notebooks/triage/05_batch_and_exogenous_workbench.ipynb](../notebooks/triage/05_batch_and_exogenous_workbench.ipynb)
  for a runnable walkthrough

---

## F8 — Exogenous Screening (CrossAMI/pCrossAMI + BH FDR)

**What it measures.** The cross-series mutual information between a target series
and one or more candidate exogenous drivers at each forecast horizon, filtered by
Benjamini-Hochberg FDR control, to screen which exogenous variables carry
statistically detectable predictive signal.

**Stability:** stable

**When to use it.**
- When candidate exogenous variables are available and you need to decide which, if
  any, are worth including in a multivariate model.
- When you need a principled multiple-testing correction to control false positives
  across many candidate drivers.
- In combination with F1: F8 extends the analysis to cross-series dependence;
  F1 remains the primary univariate anchor.

**When to avoid it.**
- As a causal screening tool: F8 detects predictive dependence, not causal direction.
- For very short series: CrossAMI inherits the same finite-sample bias and minimum-
  length requirements as univariate AMI.
- Without BH FDR correction when many drivers are tested simultaneously: uncorrected
  $p$-values will inflate false-positive rates.

**Learn more.**
- `extensions.py` source for `CrossAMIResult` and the BH FDR implementation
- [notebooks/exogenous_analysis.md](notebooks/exogenous_analysis.md) for the
  narrative walkthrough
- [notebooks/triage/05_batch_and_exogenous_workbench.ipynb](../notebooks/triage/05_batch_and_exogenous_workbench.ipynb)
  for a combined F7/F8 example
