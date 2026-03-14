<!-- type: explanation -->
# AMI and pAMI Foundations

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
