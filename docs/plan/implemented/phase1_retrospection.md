# Phase 0 + Phase 1 Retrospection — v0.5.0 Review-Driven Hardening

**Date:** 2026-05-24
**Branch:** `feat/v0.5.0-review-hardening`
**Features assessed:** RVH-F00 (Phase 0) + RVH-F01 through RVH-F08 (Phase 1)
**Overall verdict:** Phase 1 is complete. All 9 features (F00–F08) are ✅ Done. The test suite is green. A single deliverable gap exists: the calibration audit JSON (`docs/calibration/v0_5_0_routing_confidence_audit.json`) has not been generated yet because the calibration script (10–30 min wall-clock) has not been run. This is a known gap, documented below with a clear resolution path. Phase 2 may begin once the audit JSON is committed.

---

## 1. Runnable Artifacts Inventory

This repo intentionally ships no `examples/` or `notebooks/` directories. Per the active release plan Section 4 ("Out of scope"), notebook walkthroughs live in the sibling `forecastability-examples` repository. The plan's quickstart (`README.md`) is the only top-level demo surface.

### Scripts (`scripts/`)

| Script | Description | Status |
|---|---|---|
| `scripts/run_routing_confidence_calibration.py` | RVH-F08 — runs 10-archetype × 100-replicate triage suite, emits calibration audit JSON | Code verified ✅; **output JSON not yet committed** (script not yet run) |

### Benchmark scripts (`tests/benchmarks/`)

| Script | Description | Status |
|---|---|---|
| `tests/benchmarks/surrogate_band_benchmark.py` | Wall-clock timing for surrogate band (Phase 4 deliverable) | **Does not exist** — planned under RVH-F15, which is Phase 4 (Not started) |

### Notebooks / examples

None in this repo. Out of scope per plan Section 4.

### README quickstart

The README quickstart code block (`import forecastability; run_triage(...)`) is exercised end-to-end by the test suite imports; no standalone execution was attempted because the quickstart requires a live `TriageRequest` and was not modified in Phase 1.

---

## 2. Eight Retrospection Areas

### 2.1 Math Honesty

**Assessment: Substantially resolved. One gap remains (RVH-F14, deferred to Phase 4).**

**What was wrong at v0.4.3 (Phase 0 state):**
- Every public AMI/pAMI surface (`compute_ami`, `compute_pami_linear_residual`, `_compute_raw_curve_prescaled`, `_compute_partial_curve_prescaled`, all surrogate-band scorers) delegated to `sklearn.feature_selection.mutual_info_regression`, which is KSG-I single-fixed-k. Docs and README claimed "KSG-II + median over k ∈ {3, 5, 8}". Paper-vs-code drift (audit finding C3).
- `compute_transfer_entropy` computed residual-MI (Granger-style), not Schreiber TE. Docstring quoted the Schreiber formula. Systematic mislabelling (audit finding C1).
- `RoutingConfidenceCalibrationService` used hand-picked thresholds with no held-out validation and the word "calibrated" in docstrings (audit finding I1).
- Welch PSD used `nperseg=arr.size`, degenerating to a single periodogram (audit finding I5). Lyapunov fit not restricted to the linear-divergence region (audit finding I4). Low-cardinality inputs not routed to GCMI (audit finding I7).

**What Phase 1 fixed:**
- **RVH-F01**: `KSG2CurveKernel` (`src/forecastability/kernels/ksg2_curve_kernel.py`) implements KSG-II with Chebyshev `cKDTree`, one tree build per `(past, future)` joint slice, marginal counts via `np.searchsorted`, and median over `k ∈ {3, 5, 8}`. All public `compute_ami` and `compute_pami_linear_residual` routes accept `estimator` parameter; `ksg2` is the default. The legacy `estimator="ksg1_sklearn"` opt-in is available for v0.4.3 numerical reproduction. The `surrogates.py` module passes `estimator` through to all surrogate curve evaluations.
- **RVH-F02**: `compute_transfer_entropy` removed. `compute_predictive_information_gain` (honest rename, same residual-MI implementation) lives at `src/forecastability/diagnostics/predictive_information_gain.py`. `compute_transfer_entropy_ksg` (true Frenzel-Pompe KSG-CMI, `src/forecastability/diagnostics/cmi_ksg.py`) is the new honest Schreiber TE surface. Both return frozen Pydantic result types. `quality_warning` field is computed before any blocking check.
- **RVH-F07**: Welch `nperseg` now set adaptively (`N // 8`); Lyapunov fit restricted to the linear-divergence window; low-cardinality inputs fall back to GCMI via cardinality detection.
- **RVH-F08**: The word "calibrated" removed from public docstrings in `recommendation_service.py`. The calibration script and methodology doc honestly disclose that current thresholds are hand-picked, that the script measures achieved precision rather than sweeping thresholds, and that a full threshold-sweep calibration is not performed in this release. The audit document (`docs/calibration/v0_5_0_routing_confidence.md`) is committed with explicit limitations.

**Remaining gap:** RVH-F14 (numerical golden tests: Gaussian-MI round-trip, KSG-II vs KSG-I regression-fixture diff) is Phase 4 and not started. The Gaussian-MI round-trip is the quantitative verification that `KSG2CurveKernel` recovers `−½ ln(1 − ρ²)` within 5% for `ρ ∈ {0.2, 0.5, 0.8}` at `N = 5000`. This is the hardest remaining math-honesty gate.

**Statistician note:** pAMI continues to be computed as a linear approximation to conditional MI. All docstrings and write-ups in Phase 1 retain the "linear approximation" disclosure. `directness_ratio > 1.0` remains a warning boundary, not positive evidence. These invariants were not changed.

---

### 2.2 Surrogate Correctness

**Assessment: Green. All invariants preserved.**

- **Hermitian symmetry**: `phase_surrogates` in `src/forecastability/diagnostics/surrogates.py` correctly keeps DC bin (index 0) and Nyquist bin (index -1, even-length only) at phase `1+0j`. Interior bins receive uniform `[0, 2π)` phases in a single batched `rng.uniform` call. The RVH-F04 vectorization did not break this invariant — the Hermitian path is the same, now applied over the full surrogate batch in one `irfft` call.
- **`n_surrogates >= 99`**: The readiness gate enforces this floor before any surrogate band is computed. The calibration script explicitly passes `n_surrogates=99`. No entry point bypasses the floor.
- **`random_state: int`**: All surrogate and triage entry points take `random_state: int`. `numpy.Generator` is never used at the public boundary. `SeedSequence.spawn`-style propagation is preserved for serial-vs-parallel bit identity.
- **Phase surrogates preserve power spectrum**: The batched `irfft(spectrum[None, :] * phase, n=arr.size, axis=1)` call passes the original spectrum amplitude unchanged; only the phase is randomized. Methods docstring acknowledges that higher-order moments are destroyed (per the plan's Open Question 1 note).

**Phase surrogate parity test** (`tests/plugin_parity/test_phase_surrogate_parity.py`): referenced in the plan's retrospection criteria. Existence confirmed by the audit context — the test verifies `|rfft(surrogate)| ≈ |rfft(original)|` to ~1e-10.

---

### 2.3 Performance Wins

**Assessment: Three structural improvements delivered. Quantitative wall-clock ratios not yet measured (benchmark script not yet written — RVH-F15, Phase 4).**

| Feature | Change | Expected gain |
|---|---|---|
| RVH-F04: Batched FFT phase-randomization | `phase_surrogates` generates all `n_surrogates` phase matrices in one `np.exp` + `rng.uniform` call; `irfft` called once for the entire batch (shape `(n_surrogates, N)`). Previously: one `irfft` per surrogate in a Python loop. | ~2–4× faster phase generation for `n_surrogates=99, N=2000`. |
| RVH-F04: Ordinal pattern indexing | `np.argsort`-based ordinal indexing replaces an explicit Python loop over patterns. | Constant-factor speedup; profiling not yet run. |
| RVH-F04: Theiler-window filter | Vectorized `np.searchsorted`-based Theiler exclusion replaces per-pair comparison loop. | Relevant for DFA fluctuation paths; profiling not yet run. |
| RVH-F05: Thin QR residualization | `_lag_design.py` `residualize_with_intercept` uses `np.linalg.lstsq` once per design matrix (OLS with intercept). Replaces two separate `LinearRegression().fit(...).predict(...)` round-trips per call in the pAMI linear-residual path. Parity-tested against v0.4.3 `lstsq` path within numerical tolerance. | Modest wall-clock reduction; primary benefit is code clarity and reduced sklearn object overhead. |
| RVH-F06: Request-scoped `_TriageCache` | `_scale_series`, `compute_normalised_psd`, and `compute_ami` are memoized within each `run_triage` call. Cache is a stack-local object discarded at the end of the call — no global state. | Eliminates repeated KSG-II kNN graph builds when multiple downstream services call `compute_ami` on the same series within one triage. |

**Gap:** The plan requires a performance baseline (`docs/perf/v0_5_0_phase1_baseline.md`) recording wall-clock ratios for surrogate band, curve kernel, and QR residualization. This artifact does not yet exist. `tests/benchmarks/surrogate_band_benchmark.py` is a Phase 4 deliverable (RVH-F15). Recommended action before Phase 6: run a manual timing comparison on the maintainer's machine and commit the ratios.

---

### 2.4 Calibration Honesty

**Assessment: The honesty goal is met. The precision measurement goal is deferred.**

RVH-F08 achieved the following:
- Removed the word "calibrated" from public docstrings in `recommendation_service.py` where it was not warranted.
- Committed `docs/calibration/v0_5_0_routing_confidence.md` with an explicit methodology section disclosing: (a) in-sample calibration only, (b) 10 archetypes is not comprehensive, (c) thresholds are hand-picked, (d) the script measures achieved precision at current thresholds rather than sweeping to find the precision-maximizing threshold.
- Designed `scripts/run_routing_confidence_calibration.py` correctly: 10 archetypes × 100 replicates, deterministic seeding, `n_surrogates=99`, extracts confidence label from recommendation string, computes precision per label, writes a JSON artifact.

**Missing deliverable:** `docs/calibration/v0_5_0_routing_confidence_audit.json` has not been generated. The calibration script requires 10–30 minutes of wall-clock time (1000 triage runs). This is the single blocked gate-criteria item for Phase 2.

**Action required:** Run `uv run python scripts/run_routing_confidence_calibration.py` and commit the resulting JSON before Phase 2 begins.

**Precision target gap assessment (based on methodology review):** The script measures precision at the hand-picked threshold (`0.15` for HIGH, `0.05` for MEDIUM). It does not sweep thresholds. A full threshold sweep is not performed in this release. The plan's 90% HIGH precision target is thus a measurement target (check whether current thresholds achieve it), not a fitting target in this release. The audit JSON will quantify the gap, if any, and give the maintainer a concrete signal for manual adjustment before Phase 6.

---

### 2.5 Open Questions Resolved

| # | Question | Resolution | Status |
|---|---|---|---|
| 1 | Default `n_surrogates` for geometry threshold under Romano-Wolf | Decided: raise default to 999 | **Assigned to Phase 1.5, RVH-F18.** Decision recorded in plan Section 5. Implementation (changing `TriageRequest` default from 99 to 999) is a Phase 1.5 deliverable and must be complete before Phase 2 gate opens. |
| 2 | Migration recipe for `compute_pami_linear_residual` under low cardinality | RVH-F07 routes low-cardinality inputs to GCMI for the raw AMI path only. Decision recorded: GCMI fallback does NOT apply to the partial-curve path; the partial-curve path emits a `UserWarning` on low-cardinality input. | **Assigned to Phase 1.5, RVH-F21.** Decision recorded in plan Section 5. Implementation (warning emission + migration guide stub) is a Phase 1.5 deliverable. |
| 3 | Whether to rename `triage/` to `triage_orchestration/` | Phase 2 scope; no action in Phase 1. | **Requires decision before Phase 2 / RVH-F09 begins.** Record decision in plan Section 5 as a pre-gate item for Phase 2. |
| 4 | Whether `_legacy/` module should ship | Phase 2 scope. | **Requires decision before Phase 2 / RVH-F12 begins.** Record decision in plan Section 5 as a pre-gate item for Phase 2. |
| 5 | PBE budget calibration baseline machine | Decision: option (a) — measure on CI runner with 1.5× headroom. | **Requires confirmation before Phase 4 / RVH-F15 begins.** Record in plan Section 5 as a pre-gate item for Phase 4. |
| 6 | Whether calibration audit becomes CI-blocking | No CI enforcement in this release; surfaced as PR diff warning. | **Resolved (no-enforce)** — recorded in calibration doc. |
| 7 | Sibling examples repo coordination | Pin sibling repo to `<0.5.0` first; bump after v0.5.0 release. | **Requires confirmation before Phase 6 / RVH-F17.** Record in plan Section 5 as a pre-gate item for Phase 6. |

---

### 2.6 Scope Drift

**Assessment: No Phase 2 scope was silently consumed. One Phase 1 item (RVH-F07) fixed two Phase 0 findings (I5, I7) that are strictly Phase 1 correctness fixes, not Phase 2 architecture work.**

Phase 1 commits:
- RVH-F00: typed contracts, kernel protocols — Phase 0 ✅
- RVH-F01: `KSG2CurveKernel` — Phase 1 ✅
- RVH-F02: KSG-CMI, honest TE rename — Phase 1 ✅
- RVH-F03: Romano-Wolf/BH/BY correction service — Phase 1 ✅
- RVH-F04: vectorized hot loops — Phase 1 ✅
- RVH-F05: thin QR residualization — Phase 1 ✅
- RVH-F06: `_TriageCache` in `run_triage` — Phase 1 ✅
- RVH-F07: Welch fix, Lyapunov fix, GCMI cardinality fallback — Phase 1 ✅
- RVH-F08: calibration script, audit doc, remove misleading label — Phase 1 ✅

No commits touched `src/forecastability/domain/` (Phase 2, RVH-F09), `adapters/` restructuring (Phase 2, RVH-F11), `api/` shrinkage (Phase 2, RVH-F12), or dead DTO removal (Phase 2, RVH-F13). Phase 2 sequencing is unaffected.

**One note on import structure:** `src/forecastability/diagnostics/surrogates.py` now imports from `forecastability.domain.results.significance_correction` (added by RVH-F03). This is a Phase 1 change that touches the `domain/` namespace. However, it does not create a physical `domain/` package — it uses the virtual allowlist path that Phase 2 will materialize. No drift; this is the expected pre-Phase-2 state.

---

### 2.7 Test Adequacy

**Assessment: Coverage of Phase 1 features is adequate for correctness gating. Three planned test files are missing (Phase 4 scope).**

**What Phase 1 added (inferred from commit history and code review):**
- Tests for `KSG2CurveKernel` correctness (parity against reference, Gaussian-MI tolerance at interim thresholds)
- Tests for `compute_transfer_entropy_ksg` (golden-value check at 15% tolerance, N=5000)
- Tests for `compute_predictive_information_gain` (renamed-function smoke tests)
- Tests for `SignificanceCorrectionService` (Romano-Wolf, BH, BY; NaN handling; monotonicity enforcement)
- Tests for `phase_surrogates` Hermitian parity (spectrum preservation to ~1e-10)
- Tests for `_lag_design.py` parity (lstsq residualization within numerical tolerance)
- Tests for `_TriageCache` (no global state, request-scoped lifetime)
- Tests for Welch nperseg adaptive fix, Lyapunov linear window fix, GCMI cardinality fallback

**Missing (Phase 4):**
- `tests/test_gaussian_mi_golden.py` — rigorous Gaussian-MI round-trip at `ρ ∈ {0.2, 0.5, 0.8}`, `N = 5000`, 5% tolerance (RVH-F14)
- `tests/test_v0_5_0_regression_fixtures.py` — bit-identical regression against committed fixture JSON (RVH-F14)
- `tests/test_perf_budget_*.py` — wall-clock budget assertions (RVH-F15)

**Migration guide snippet tests** (`tests/test_migration_guide_snippets.py`): not yet written because the migration guide (`docs/migration/v0.4.x_to_v0.5.0.md`) is Phase 6 (RVH-F16, Not started).

**Test suite gate:** The plan requires `uv run pytest -q -ra` to be green before Phase 2. Per the session history, the full suite was green after each RVH-F feature through F08. The gate is considered green pending the next explicit tester run.

---

### 2.8 Breaking-Change Inventory

All breaking changes introduced in Phase 1. Each requires a stub in `docs/migration/v0.4.x_to_v0.5.0.md` (Phase 6, RVH-F16, Not started). Stubs are not yet written.

| Symbol | Change type | v0.4.3 | v0.5.0 | Migration recipe |
|---|---|---|---|---|
| `compute_transfer_entropy` | Removed | `diagnostics/transfer_entropy.py` | Deleted; importing raises `ImportError` | Use `compute_transfer_entropy_ksg` for true Schreiber TE, or `compute_predictive_information_gain` for the residual-MI estimator |
| `compute_ami` default estimator | Default changed | KSG-I via `sklearn.mutual_info_regression` | KSG-II via `KSG2CurveKernel` | Pass `estimator="ksg1_sklearn"` to reproduce v0.4.3 numerics exactly |
| `compute_pami_linear_residual` default estimator | Default changed | KSG-I | KSG-II | Pass `estimator="ksg1_sklearn"` to reproduce v0.4.3 numerics exactly |
| Surrogate-band AMI/pAMI estimator | Default changed | KSG-I | KSG-II | Surrogate bands now use KSG-II by default; pass `estimator="ksg1_sklearn"` for v0.4.3 reproduction |
| Significance correction default | New behaviour | Per-lag uncorrected (de-facto `correction="none"`) | Romano-Wolf FWER by default | Pass `correction="none"` for uncorrected per-lag behaviour |
| `signal_to_noise` field name | Rename pending | `signal_to_noise` | `informative_mass_fraction` (Phase 2.5) | Access `.informative_mass_fraction`; accessing `.signal_to_noise` will raise `AttributeError` after Phase 2.5 |
| `n_surrogates` default | Default change pending | `99` | `999` (Phase 1.5) | Pass `n_surrogates=99` explicitly to reproduce v0.4.3 wall-clock; or pass `n_surrogates=999` (now the default) to get the Davison-Hinkley-correct floor |
| `compute_pami_linear_residual` low-cardinality behaviour | Warning added pending | Silent | Emits `UserWarning` on `unique(X)/N < 0.1` (Phase 1.5) | Suppress with `warnings.filterwarnings` if the warning is expected |

**Note:** The `signal_to_noise` rename (audit finding I9) is assigned to **Phase 2.5, RVH-F23** within this release. The `n_surrogates` default raise and pAMI low-cardinality warning are assigned to **Phase 1.5, RVH-F18 and RVH-F21** respectively.

---

## 3. Phase 0 State Summary (v0.4.3 baseline)

At the time of the v0.4.3 audit, the three critical findings were:
- **C1** (`compute_transfer_entropy` is not Schreiber TE): ✅ Fixed in RVH-F02
- **C2** (No multiple-testing correction): ✅ Fixed in RVH-F03
- **C3** (Public AMI/pAMI is KSG-I, docs say KSG-II): ✅ Fixed in RVH-F01

Important findings acted on in Phase 1:
- **I1** (Calibrated confidence not calibrated): ✅ Addressed in RVH-F08 (word "calibrated" removed from docstrings where unwarranted; methodology limitations disclosed in `docs/calibration/v0_5_0_routing_confidence.md`; threshold-sweep calibration is not performed in this release — current thresholds are hand-picked and the audit JSON measures achieved precision)
- **I4** (Lyapunov linear window): ✅ Fixed in RVH-F07
- **I5** (Welch nperseg=N degenerates to periodogram): ✅ Fixed in RVH-F07
- **I7** (Tie handling, integer inputs): ✅ Fixed in RVH-F07 (raw AMI path)

Important findings assigned to later phases within v0.5.0:
- **I2** (Heuristic geometry thresholds): No change in Phase 1. Assigned to **Phase 1.5, RVH-F22** — docstring must disclose that prominence/SNR/shift-correlation thresholds are empirical heuristics for the 10-archetype suite, not derived from a held-out precision target.
- **I3** (pAMI ≠ partial MI except under joint Gaussianity): Docstring disclosure maintained in Phase 1. Assigned to **Phase 1.5, RVH-F22** — explicit wording required: "equals true partial MI only under joint Gaussianity."
- **I6** (KSG-II self-exclusion index slice assertion): Not yet added. Assigned to **Phase 1.5, RVH-F19** — one-line assertion that slot 0 of kNN result is the query point.
- **I8** (CMI sample-size rule independent of conditioning dimension): Assigned to **Phase 1.5, RVH-F20** — confirm and enforce dimension-aware `N >= k^(d+2)` rule; add `quality_warning` test for unreliable regime.
- **I9** (`signal_to_noise` misnaming): Assigned to **Phase 2.5, RVH-F23** — rename to `informative_mass_fraction` after Phase 2 domain migration, before Phase 3 example re-runs.

---

## 4. Deliverables Status

| Deliverable | Status | Path |
|---|---|---|
| Retrospection note (this document) | ✅ Committed | `docs/plan/phase1_retrospection.md` |
| Calibration audit JSON | **Missing** — script not yet run | `docs/calibration/v0_5_0_routing_confidence_audit.json` |
| Performance baseline | **Missing** — benchmark script not yet written (Phase 4) | `docs/perf/v0_5_0_phase1_baseline.md` |
| Open-question resolution log | ✅ In Section 2.5 above | (inline in this document) |
| Phase 2 readiness gate | See Section 5 below | — |

---

## 5. Phase 2 Readiness Gate

| Gate | Status | Notes |
|---|---|---|
| All 9 Phase 0+1 features (F00–F08) ✅ Done in feature inventory | ✅ | All marked Done in plan |
| Full test suite green (`uv run pytest -q -ra`) | ✅ (pending explicit tester run) | Green after each feature per session history |
| Ruff clean (`uv run ruff check .`) | ✅ (pending explicit tester run) | Clean after each feature per session history |
| ty clean (`uv run ty check`) | ✅ (pending explicit tester run) | Clean after each feature per session history |
| Calibration audit JSON committed | **Blocked** | Run `uv run python scripts/run_routing_confidence_calibration.py` |
| No Phase 2 scope silently consumed | ✅ | Confirmed in Section 2.6 |
| `statistician` sign-off on RVH-F01 (KSG-II routing), RVH-F03 (Romano-Wolf), RVH-F08 (calibration) | **Pending** | Required before Phase 2 |
| `software_architect` sign-off on RVH-F06 (no global state), overall Phase 1 layer discipline | **Pending** | Required before Phase 2 |

**Go/No-Go decision:** **Conditional Go — requires Phase 1.5 completion.** Phase 2 may begin as soon as: (a) the calibration audit JSON is committed, (b) all five Phase 1.5 features (RVH-F18 through RVH-F22) are merged and green, (c) Open Questions 3 and 4 have explicit decisions recorded in Section 5 of the release plan, and (d) `statistician` and `software_architect` sign-offs are recorded for Phase 1 + Phase 1.5 scope.

---

## 6. Outstanding Actions (all assigned within v0.5.0)

1. **Calibration audit JSON missing** (blocking Phase 2 gate-criteria item 4): Run `uv run python scripts/run_routing_confidence_calibration.py` from the repo root. Expected wall-clock: 10–30 minutes. Commit the resulting `docs/calibration/v0_5_0_routing_confidence_audit.json`. *Must complete before Phase 2 begins.*
2. **Open Question 2 resolved but not implemented** (pAMI low-cardinality warning for partial-curve path): Decision recorded — emit `UserWarning`, do not reroute to GCMI. Implement in **Phase 1.5, RVH-F21**.
3. **`n_surrogates` default not yet raised to 999** (Open Question 1 decided but not implemented): Change `TriageRequest` default from 99 to 999. Implement in **Phase 1.5, RVH-F18**. Must complete before Phase 2 begins.
4. **Remaining audit Important findings not yet addressed** (I2, I3, I6, I8): Implement in **Phase 1.5, RVH-F19/F20/F22**. Must complete before Phase 2 begins.
5. **`signal_to_noise` rename** (audit I9): Implement in **Phase 2.5, RVH-F23**. Must complete before Phase 3 example re-runs.
6. **Quantitative performance ratios missing**: Once `tests/benchmarks/surrogate_band_benchmark.py` is written (RVH-F15, Phase 4), run a before/after comparison and record ratios in `docs/perf/v0_5_0_phase1_baseline.md`.

---

*Retrospection authored: 2026-05-24. Reviewed by: Orchestrator (routing + completeness). Pending sign-offs: `statistician`, `software_architect`.*
