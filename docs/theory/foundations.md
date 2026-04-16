<!-- type: explanation -->
# AMI, pAMI, and TE Foundations

## Scope

This document defines the mathematical basis used by `src/forecastability` and clarifies what is paper-native versus project extension.

## Paper-native metric

AMI at horizon \(h\):
\[
I_h = I(X_t; X_{t+h})
\]

Interpretation:
- Nonlinear analog of ACF (total dependence at lag \(h\)).
- Includes both direct and mediated lag paths.

Implementation:
- kNN MI estimator (`k=8` default).
- Horizon-specific curve, never collapsed before analysis.

## Project extension metric

pAMI at horizon \(h\):
\[
\tilde{I}_h = I(X_t; X_{t+h} \mid X_{t+1},\ldots,X_{t+h-1})
\]

Interpretation:
- Nonlinear analog of PACF (direct dependence after conditioning on intermediate lags).

Current estimator in this repo:
1. Build conditioning matrix \(Z=[X_{t+1},\ldots,X_{t+h-1}]\).
2. Residualize past and future on \(Z\) (linear backend by default; optional RF backend).
3. Compute MI on residual pairs.

## Directional extension metric

Transfer Entropy (TE) at lag \(h\):
\[
TE(X \to Y \mid h) = I(Y_t ; X_{t-h} \mid Y_{t-1},\ldots,Y_{t-h+1})
\]

Interpretation:
- Directional predictive dependence: in general \(TE(X \to Y) \neq TE(Y \to X)\).
- Conditioning on target history controls for autocorrelation-driven carryover in \(Y\).
- Positive TE indicates added predictive information from source history beyond target-only history.

Implemented entry points:
- `src/forecastability/diagnostics/transfer_entropy.py`:
  `compute_transfer_entropy()` and `compute_transfer_entropy_curve()` (core estimator path).
- `src/forecastability/services/transfer_entropy_service.py`:
  compatibility facade re-exporting the diagnostics functions.
- `src/forecastability/pipeline/analyzer.py`:
  `ForecastabilityAnalyzer` and `ForecastabilityAnalyzerExog` support `method="te"`
  for raw-curve analysis and TE surrogate significance bands.

Current constraints and caveats:
- Analyzer path is raw-only for TE: partial TE is intentionally unsupported.
  Requests for `compute_partial(..., method="te")` raise a validation error because no
  validated partial-TE estimand is implemented in the analyzer path.
- TE sample-size guardrails require `min_pairs >= 50`; with non-empty conditioning
  history, at least `2 * min_pairs` aligned rows are required.
- TE values are estimator- and null-model-aware diagnostics, not causal proof.
  Significance is evaluated against phase-randomized surrogate bands and should be
  interpreted with the same surrogate caveats used elsewhere in this repository.

Validated directional evidence (analyst run, 2026-04-16):
- Synthetic lag-2 driver pair, \(n=1200\), `seed=17`.
- \(TE(X \to Y)\) peaked at lag 2 with a strong directional gap vs \(TE(Y \to X)\).
- `ForecastabilityAnalyzerExog(..., method="te")` raw TE curve matched
  `compute_transfer_entropy_curve(...)` exactly (`max_abs_diff = 0.0`).
- Significant \(X \to Y\) lags above the surrogate upper band: 1, 2, and 3.

## AMI vs pAMI properties

| Property | AMI | pAMI |
|---|---|---|
| Form | \(I(X_t;X_{t+h})\) | \(I(X_t;X_{t+h}\mid X_{t+1},...,X_{t+h-1})\) |
| Analog | ACF | PACF |
| Mediated paths | Included | Removed (approximately with residualization) |
| Paper-native | Yes | No (project extension) |
| Non-negativity | Yes | Yes |

Expected relation:
- In theory, \(\tilde{I}_h \le I_h\).
- In finite samples with residual approximation, occasional \(\tilde{I}_h > I_h\) can occur.
- This repository flags `directness_ratio > 1.0` as `arch_suspected`.

## Significance bands

Surrogate significance uses phase-randomized surrogates and two-sided 95% quantiles:
- lower: 2.5th percentile
- upper: 97.5th percentile

Interpretation rule:
- Use upper-band crossings to detect non-null dependence.
- Lower band is near zero for MI and usually not operationally informative.

## Rolling-origin invariants

- Diagnostics (AMI/pAMI) are computed on each training window only.
- Forecast errors are computed on post-origin test window only.
- This separation is mandatory to prevent leakage.

## Time-series applicability

### Paper-aligned constraints

From arXiv:2601.10006:
- Use frequency-specific horizon caps: Yearly 6, Quarterly 8, Monthly 18, Weekly 13, Daily 14, Hourly 48.
- Treat short, sparse, and degenerate distributions as fragile for MI estimation.
- Expect weaker AMI-error discrimination in Daily frequency than in Hourly/Weekly/Quarterly/Yearly.

### Implementation length constraints

Given series length \(N\), max lag \(H\):

AMI feasibility:
\[
N \ge H + \texttt{min\_pairs\_ami} + 1
\]

pAMI feasibility (linear residual backend):
\[
N \ge \max\left(H + \texttt{min\_pairs\_pami} + 1,\ 2H\right)
\]

With defaults (`min_pairs_ami=30`, `min_pairs_pami=50`, `H=100`):
- AMI requires \(N \ge 131\)
- pAMI requires \(N \ge 201\)

## Directness summary

`directness_ratio`:
\[
r = \frac{\operatorname{AUC}(\tilde{I}_h)}{\operatorname{AUC}(I_h)}
\]

Interpretation:
- \(r \approx 1\): mostly direct structure.
- \(r \ll 1\): mostly mediated structure.
- \(r > 1\): numerical/assumption warning (often ARCH-type behavior), not a physical contradiction.

## Extension disclosure

- Paper validates AMI only.
- pAMI, exogenous cross-dependence, and scorer-registry abstractions are project additions.
