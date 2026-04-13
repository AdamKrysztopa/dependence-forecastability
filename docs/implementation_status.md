<!-- type: reference -->
# Implementation Status

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.

This page is a reviewer-facing evidence map. For each diagnostic feature (F1–F8)
it records implementation status, test coverage, regression fixtures, and links to
the theory doc, notebooks, and scripts. Read it to understand what is done, what is
experimental, and where the evidence lives — without reading the source code.

---

## Evidence map legend

| Column | Meaning |
|---|---|
| Implemented | Feature exists in `src/forecastability/` and is callable |
| Tested | Unit or integration tests in `tests/` cover the core logic |
| Regression fixtures | Frozen numeric regression fixtures stored in `tests/` or `docs/fixtures/` |
| Theory doc | A doc in `docs/theory/` or `docs/triage_methods/` matches the implementation |
| Notebook | At least one notebook in `notebooks/triage/` demonstrates the feature end-to-end |
| Script | At least one script in `scripts/` exercises the feature |

---

## F1 — Forecastability Profile (AMI/pAMI curve)

| Evidence | Status | Location |
|---|---|---|
| Implemented | ✅ | `src/forecastability/triage/forecastability_profile.py` |
| Tested | ✅ | `tests/test_forecastability_profile.py` |
| Regression fixtures | ✅ | `tests/` (diagnostic regression suite) |
| Theory doc | ✅ | [theory/forecastability_profile.md](theory/forecastability_profile.md), [theory/foundations.md](theory/foundations.md) |
| Notebook | ✅ | `notebooks/triage/01_forecastability_profile_walkthrough.ipynb` |
| Script | ✅ | `scripts/run_canonical_examples.py` |

**Known-partial / caveats.**
- Surrogate significance bands are unavailable for series shorter than the minimum
  required for stable quantile estimation.
- `directness_ratio > 1.0` (pAMI > AMI in finite samples) is flagged as
  `arch_suspected`; it is a warning boundary, not positive evidence of architecture.

---

## F2 — Theoretical Limit Diagnostics

| Evidence | Status | Location |
|---|---|---|
| Implemented | ✅ | `src/forecastability/triage/theoretical_limit_diagnostics.py` |
| Tested | ✅ | `tests/test_metrics.py`, `tests/test_phase1_examples.py` |
| Regression fixtures | ✅ | `tests/` (diagnostic regression suite) |
| Theory doc | ✅ | [theory/foundations.md](theory/foundations.md) |
| Notebook | ✅ | `notebooks/triage/02_information_limits_and_compression.ipynb` |
| Script | ✅ | `scripts/run_phase1_limit_diagnostics.py` |

**Known-partial / caveats.**
- Limit estimates inherit kNN MI finite-sample bias; short series inflate the
  computed ceiling.

---

## F3 — Predictive Information Learning Curves

| Evidence | Status | Location |
|---|---|---|
| Implemented | ✅ | `src/forecastability/triage/predictive_info_learning_curve.py` |
| Tested | ✅ | `tests/test_metrics.py` |
| Regression fixtures | ✅ | `tests/` (diagnostic regression suite) |
| Theory doc | ✅ | [triage_methods/predictive_information_learning_curves.md](triage_methods/predictive_information_learning_curves.md) |
| Notebook | ✅ | `notebooks/triage/03_predictive_information_learning_curves.ipynb` |
| Script | ✅ | `scripts/run_predictive_info_learning_curves.py` |

**Known-partial / caveats.**
- A hard cap $k_{\max} = 8$ is enforced to limit kNN curse of dimensionality.
- Reliability warnings are attached when $n < 1000$ and $k > 3$.

---

## F4 — Spectral Predictability Score

| Evidence | Status | Location |
|---|---|---|
| Implemented | ✅ | `src/forecastability/triage/spectral_predictability.py` |
| Tested | ✅ | `tests/test_metrics.py` |
| Regression fixtures | ✅ | `tests/` (diagnostic regression suite) |
| Theory doc | ✅ | [theory/spectral_predictability.md](theory/spectral_predictability.md) |
| Notebook | ✅ | `notebooks/triage/04_spectral_and_entropy_diagnostics.ipynb` |
| Script | ✅ | `scripts/run_spectral_predictability.py` |

**Known-partial / caveats.**
- Ω values are unreliable for $n < 128$; treat as coarse indicator only.
- Non-stationary series should be detrended before computing Ω.

---

## F5 — Largest Lyapunov Exponent

> [!WARNING]
> **Experimental.** F5 is gated behind `experimental: true` in the config. It is
> excluded from automated triage (F7) and has no stability guarantee. The evidence
> map below reflects the current state of a feature under active development.

| Evidence | Status | Location |
|---|---|---|
| Implemented | ✅ (experimental) | `src/forecastability/triage/lyapunov.py` |
| Tested | ✅ | `tests/test_lyapunov.py` |
| Regression fixtures | ⚠️ partial | Basic sanity checks only; no paper-aligned benchmark fixture |
| Theory doc | ✅ | [triage_methods/largest_lyapunov_exponent.md](triage_methods/largest_lyapunov_exponent.md) |
| Notebook | — | Not yet included in triage notebook set |
| Script | ✅ | `scripts/run_largest_lyapunov_exponent.py` |

**Known-partial / caveats.**
- Numerically fragile for $n < 1000$; estimates are indicative only.
- Cannot distinguish deterministic chaos from stochastic divergence.
- Excluded from F7 batch ranking by design.
- No paper alignment: F5 is a project extension with no direct claim in the
  referenced paper.

---

## F6 — Entropy-Complexity Band

| Evidence | Status | Location |
|---|---|---|
| Implemented | ✅ | `src/forecastability/triage/complexity_band.py` |
| Tested | ✅ | `tests/test_complexity_band.py` |
| Regression fixtures | ✅ | `tests/` (diagnostic regression suite) |
| Theory doc | ✅ | [theory/entropy_based_complexity.md](theory/entropy_based_complexity.md) |
| Notebook | ✅ | `notebooks/triage/04_spectral_and_entropy_diagnostics.ipynb` |
| Script | ✅ | `scripts/run_entropy_complexity.py` |

**Known-partial / caveats.**
- Pattern frequency estimates require adequate $n$; for embedding order $m = 5$
  approximately 600 observations are recommended.

---

## F7 — Batch Triage and Multi-Series Ranking

| Evidence | Status | Location |
|---|---|---|
| Implemented | ✅ | `src/forecastability/triage/batch_models.py` |
| Tested | ✅ | `tests/test_batch_triage_f7.py` |
| Regression fixtures | ✅ | `tests/` (benchmark panel regression suite) |
| Theory doc | — | (batch orchestration, no separate theory doc needed) |
| Notebook | ✅ | `notebooks/triage/05_batch_and_exogenous_workbench.ipynb` |
| Script | ✅ | `scripts/run_benchmark_panel.py`, `scripts/run_multi_signal_diagnostic_ranking.py` |

**Known-partial / caveats.**
- F5 (LLE) is intentionally excluded from the ranking table.
- Requires all individual series to clear the minimum-length threshold; short series
  in the panel are flagged, not silently skipped.

---

## F8 — Exogenous Screening (CrossAMI/pCrossAMI + BH FDR)

| Evidence | Status | Location |
|---|---|---|
| Implemented | ✅ | `src/forecastability/extensions.py` (+ scoring infrastructure) |
| Tested | ✅ | `tests/test_extensions.py`, `tests/test_benchmark_exog_panel.py` |
| Regression fixtures | ✅ | `tests/` (exogenous benchmark fixture) |
| Theory doc | ✅ | [notebooks/exogenous_analysis.md](notebooks/exogenous_analysis.md) |
| Notebook | ✅ | `notebooks/triage/05_batch_and_exogenous_workbench.ipynb` |
| Script | ✅ | `scripts/run_exog_analysis.py`, `scripts/run_benchmark_exog_panel.py` |

**Known-partial / caveats.**
- CrossAMI inherits all kNN MI finite-sample limitations.
- BH FDR correction is applied across drivers; family-wise error rate control is
  not provided.

---

## Theory → notebook → script → test evidence map

This table gives reviewers a one-screen overview of where evidence lives for
each feature.

| Feature | Theory doc | Notebook | Script | Test file |
|---|---|---|---|---|
| F1 | [forecastability_profile.md](theory/forecastability_profile.md) | `01_forecastability_profile_walkthrough.ipynb` | `run_canonical_examples.py` | `test_forecastability_profile.py` |
| F2 | [foundations.md](theory/foundations.md) | `02_information_limits_and_compression.ipynb` | `run_phase1_limit_diagnostics.py` | `test_metrics.py` |
| F3 | [predictive_information_learning_curves.md](triage_methods/predictive_information_learning_curves.md) | `03_predictive_information_learning_curves.ipynb` | `run_predictive_info_learning_curves.py` | `test_metrics.py` |
| F4 | [spectral_predictability.md](theory/spectral_predictability.md) | `04_spectral_and_entropy_diagnostics.ipynb` | `run_spectral_predictability.py` | `test_metrics.py` |
| F5 ⚠️ | [largest_lyapunov_exponent.md](triage_methods/largest_lyapunov_exponent.md) | — | `run_largest_lyapunov_exponent.py` | `test_lyapunov.py` |
| F6 | [entropy_based_complexity.md](theory/entropy_based_complexity.md) | `04_spectral_and_entropy_diagnostics.ipynb` | `run_entropy_complexity.py` | `test_complexity_band.py` |
| F7 | — | `05_batch_and_exogenous_workbench.ipynb` | `run_benchmark_panel.py` | `test_batch_triage_f7.py` |
| F8 | [notebooks/exogenous_analysis.md](notebooks/exogenous_analysis.md) | `05_batch_and_exogenous_workbench.ipynb` | `run_exog_analysis.py` | `test_extensions.py` |
