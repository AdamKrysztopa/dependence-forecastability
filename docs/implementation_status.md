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
| Script | ✅ | `scripts/run_canonical_triage.py` |

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
| Script | ✅ | `scripts/archive/run_phase1_limit_diagnostics.py` |

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
| Script | ✅ | `scripts/archive/run_predictive_info_learning_curves.py` |

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
| Script | ✅ | `scripts/archive/run_spectral_predictability.py` |

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
| Script | ✅ | `scripts/archive/run_largest_lyapunov_exponent.py` |

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
| Script | ✅ | `scripts/archive/run_entropy_complexity.py` |

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
| Script | ✅ | `scripts/run_benchmark_panel.py`, `scripts/archive/run_multi_signal_diagnostic_ranking.py` |

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
| Theory doc | — | No dedicated theory page; use the walkthrough notebook and script evidence |
| Notebook | ✅ | `notebooks/triage/05_batch_and_exogenous_workbench.ipynb` |
| Script | ✅ | `scripts/run_exog_analysis.py`, `scripts/archive/run_benchmark_exog_panel.py` |

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
| F1 | [forecastability_profile.md](theory/forecastability_profile.md) | `01_forecastability_profile_walkthrough.ipynb` | `scripts/run_canonical_triage.py` | `test_forecastability_profile.py` |
| F2 | [foundations.md](theory/foundations.md) | `02_information_limits_and_compression.ipynb` | `scripts/archive/run_phase1_limit_diagnostics.py` | `test_metrics.py` |
| F3 | [predictive_information_learning_curves.md](triage_methods/predictive_information_learning_curves.md) | `03_predictive_information_learning_curves.ipynb` | `scripts/archive/run_predictive_info_learning_curves.py` | `test_metrics.py` |
| F4 | [spectral_predictability.md](theory/spectral_predictability.md) | `04_spectral_and_entropy_diagnostics.ipynb` | `scripts/archive/run_spectral_predictability.py` | `test_metrics.py` |
| F5 ⚠️ | [largest_lyapunov_exponent.md](triage_methods/largest_lyapunov_exponent.md) | — | `scripts/archive/run_largest_lyapunov_exponent.py` | `test_lyapunov.py` |
| F6 | [entropy_based_complexity.md](theory/entropy_based_complexity.md) | `04_spectral_and_entropy_diagnostics.ipynb` | `scripts/archive/run_entropy_complexity.py` | `test_complexity_band.py` |
| F7 | — | `05_batch_and_exogenous_workbench.ipynb` | `run_benchmark_panel.py` | `test_batch_triage_f7.py` |
| F8 | — | `05_batch_and_exogenous_workbench.ipynb` | `run_exog_analysis.py` | `test_extensions.py` |

---

## v0.3.0 — Covariant Informative Extensions

These features extend the v0.2.x core with bivariate and causal dependence measures.
See [plan/v0_3_0_covariant_informative_ultimate_plan.md](plan/v0_3_0_covariant_informative_ultimate_plan.md)
for the full feature inventory and phasing plan.

### V3-F01 — Transfer Entropy scorer + service

| Evidence | Status | Location |
|---|---|---|
| Implemented | ✅ | `src/forecastability/diagnostics/transfer_entropy.py`, `src/forecastability/services/transfer_entropy_service.py` |
| Tested | ✅ | `tests/test_gcmi.py`, `tests/test_covariant_models.py` |
| Regression fixtures | ✅ | `tests/` (diagnostic regression suite) |
| Theory doc | ✅ | [theory/foundations.md](theory/foundations.md) — TE section |
| Notebook | — | Not yet in triage notebook set |
| Script | — | No dedicated standalone script; exercised via analyzer tests |

**Validated directional evidence (2026-04-16):** synthetic lag-2 driver pair, $n=1200$, `seed=17`;
$TE(X \to Y)$ peaked at lag 2 with a strong directional gap vs $TE(Y \to X)$.

---

### V3-F02 — GCMI scorer + service

| Evidence | Status | Location |
|---|---|---|
| Implemented | ✅ | `src/forecastability/diagnostics/gcmi.py`, `src/forecastability/services/gcmi_service.py` |
| Tested | ✅ | `tests/test_gcmi.py` (25 tests) |
| Regression fixtures | ✅ | `tests/test_gcmi.py` (numeric regression assertions) |
| Theory doc | ✅ | [theory/gcmi.md](theory/gcmi.md) |
| Notebook | — | Not yet in triage notebook set |
| Script | ✅ | `examples/covariant_informative/information_measures/gcmi_example.py` |

**Known-partial / caveats.**
- Bivariate GCMI only; no multivariate extension.
- GCMI is unconditional: it does not control for target autocorrelation.
  Use TE (V3-F01) or PCMCI+ (V3-F03) when autocorrelation control is required.
- `gcmi_scorer()` accepts `random_state` for protocol compatibility but ignores it
  (GCMI has no stochastic component).

---

### V3-F04 — PCMCI-AMI-Hybrid (shipped variant)

| Artefact | Status | Location |
|---|---|---|
| KnnCMI CondIndTest | ✅ | `src/forecastability/adapters/knn_cmi_ci_test.py` |
| PcmciAmiAdapter | ✅ | `src/forecastability/adapters/pcmci_ami_adapter.py` |
| Service facade | ✅ | `src/forecastability/services/pcmci_ami_service.py` |
| Result model | ✅ | `PcmciAmiResult` in `utils/types.py` |
| Tests | ✅ | `tests/test_pcmci_ami_hybrid.py` (12 tests incl. nonlinear detection) |
| Example (standalone) | ✅ | `examples/covariant_informative/causal_discovery/pcmci_ami_hybrid_benchmark.py` |
| Example (comparison) | ✅ | `examples/covariant_informative/causal_discovery/pcmci_plus_vs_pcmci_ami_benchmark.py` |
| Example (PCMCI+ base) | ✅ | `examples/covariant_informative/causal_discovery/pcmci_plus_benchmark.py` |

**What is implemented.**
- Phase 0 performs real unconditional MI/CrossMI screening over lagged `(source, lag, target)` triplets and passes survivors into Tigramite `link_assumptions` before the PCMCI+ run.
- The default `knn_cmi` path uses `linear_residual` to remove the conditioning set, scores dependence with kNN MI on residuals, and calibrates p-values with 199 shuffle permutations plus the Phipson and Smyth correction.
- `PcmciAmiResult` exposes the Phase 0 screening diagnostics alongside the mapped Phase 1 and Phase 2 PCMCI+ outputs.

**Current caveats.**
- The stronger proposal to rank downstream conditioning sets by Phase 0 MI is not implemented in the shipped adapter; after pruning, conditioning-set selection follows Tigramite PCMCI+ behavior.
- The shipped `knn_cmi` backend is residualization-based, so it should be read as a practical hybrid CI path rather than fully non-parametric conditioning.
- Phase 0 pruning narrows the candidate set, but the implementation does not claim a general statistical-power gain from pruning alone.

**Current evidence.**
- The clearest back-to-back demonstrator is `examples/covariant_informative/causal_discovery/pcmci_plus_vs_pcmci_ami_benchmark.py` with `seed=43`, `n=1200`, `max_lag=2`, and `alpha=0.05`.
- On that synthetic benchmark, PCMCI+ with `parcorr` misses the expected nonlinear parents while the shipped hybrid recovers at least one of them.
- Treat that comparison as benchmark-specific illustration, not broad validation of general nonlinear superiority.
