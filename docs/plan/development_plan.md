<!-- type: reference -->
# Development Plan — Triage Extension

**Replaces:** MoSCoW plan (removed)
**Source epic:** [`not_planed/triage_extension_epic_math_grounded.md`](not_planed/triage_extension_epic_math_grounded.md)
**Last reviewed:** 2026-04-13 (F1 implemented 2026-04-12; F2, SeriesDiagnosticScorer, PSD utility implemented 2026-04-12; F6 implemented 2026-04-12; F4 implemented 2026-04-12; F3 implemented 2026-04-12; F5 implemented 2026-04-12; F7, F8 implemented 2026-04-12; F9 elaborated 2026-04-13; F9 implemented 2026-04-13; examples/notebooks/agents plan added 2026-04-13; E3/E4/E6 examples marked done 2026-04-13)

---

## Why a new plan structure

The MoSCoW categories served the initial baseline delivery well—`must_have` and
`should_have` are now complete. The remaining work is a coordinated extension of the
deterministic triage layer: ten features with shared infrastructure, real code
dependencies between them, and varying statistical risk. A phased dependency-aware
plan is a better fit than loose priority buckets.

### Planning principles

1. **Dependency-first ordering** — features that produce shared infrastructure ship
   before features that consume it.
2. **Risk-gated delivery** — high-risk estimators ship behind explicit experimental
   flags and never auto-influence triage decisions.
3. **Overlap honesty** — features already substantially implemented are scoped as
   incremental enhancements, not new epics.
4. **Stage gates** — each phase ends with a verification gate before the next begins.

---

## Repo baseline (what already exists)

Before reading the per-feature sections, note what the repo already provides:

| Capability | Status |
|---|---|
| 4-stage deterministic triage pipeline (readiness → routing → compute → interpretation) | ✅ |
| Pluggable scorer registry (MI, Pearson, Spearman, Kendall, distance corr.) | ✅ |
| Batch triage with per-series error isolation and composite ranking | ✅ |
| Exogenous screening workbench with keep / review / reject flow | ✅ |
| Result bundles with SHA-256 provenance | ✅ |
| Checkpointing + event emission | ✅ |
| 9 hexagonal port protocols | ✅ |
| 64+ triage-specific tests | ✅ |
| Interpretation: forecastability class, directness class, modelling regime | ✅ |

---

## Feature inventory and overlap assessment

| # | Feature | Phase | Overlap | Genuine new work | Status |
|---|---------|-------|---------|------------------|--------|
| F1 | Forecastability Profile & Informative Horizon Set | 1 | ~20 % — class label exists; formal profile object does not | New domain model + application service | ✅ Done |
| F2 | Information-Theoretic Limit Diagnostics | 1 | ~5 % | New service + DPI / compression warnings | ✅ Done |
| F10 | Permutation-AMI Naming Cleanup | 1 | 100 % — convention already followed | Documentation-only | ✅ Done (convention already followed; theory doc confirms naming) |
| Infra | `SeriesDiagnosticScorer` protocol | 1 | — | New protocol alongside `DependenceScorer` | ✅ Done |
| Infra | Shared PSD / FFT utility | 1 | — | Deterministic PSD helper for F4, F6 | ✅ Done |
| F6 | Entropy-Based Complexity Triage | 2 | 0 % (shares PSD with F4) | New scorer(s) + complexity-band service | ✅ Done |
| F4 | Spectral Predictability | 2 | 0 % | New scorer + shared PSD utility | ✅ Done |
| F3 | Predictive Information Learning Curves | 2 | 0 % | New service, new estimator (multi-dim MI) | ✅ Done |
| F5 | Largest Lyapunov Exponent | 3 | 0 % | New experimental scorer | ✅ Done |
| F7 | Batch Multi-Signal Ranking | 3 | ~85 % — `run_batch_triage()` exists | Incremental: add new-scorer columns | ✅ Done |
| F8 | Enhanced Exogenous Screening | 3 | ~80 % — screening workbench exists | Incremental: add inter-driver redundancy penalty | ✅ Done |
| F9 | Benchmark & Reproducibility Expansion | 3 | Infrastructure exists | Regression fixtures for F1–F6 diagnostics + F7 batch + F8 exog extensions | ✅ Done |

---

## Examples, notebooks & agent adapter inventory

> Source: [`not_planed/examples_notebooks_agents_plan.md`](not_planed/examples_notebooks_agents_plan.md).
> Design rules: examples are deterministic, fast, call `src/` only; notebooks never duplicate formulas inline;
> agent adapters consume stable deterministic payloads — one shared layer, no per-feature duplication.

| # | Kind | Feature(s) | Phase | Overlap | Genuine new work | Status |
|---|------|------------|-------|---------|------------------|--------|
| E1a | Example | F1 Profile (synthetic) | 1 | — | Seasonal non-monotone + AR decay; print horizons, informative set, recommendations | ✅ Done |
| E1b | Example | F1 Profile (realistic) | 1 | — | Real-data profile walkthrough | ✅ Done |
| E2 | Example | F2 IT Limits | 1 | ~60 % — `run_phase1_limit_diagnostics.py` | Add compressed-vs-original; "possible" vs "achieved" distinction | ✅ Done |
| E3 | Example | F3 Learning Curves | 2 | ~80 % — `run_predictive_info_learning_curves.py` | Add reliability-warning demo for small $n$; consolidate | ✅ Done |
| E4 | Example | F4 Spectral | 2 | ~90 % — `run_spectral_predictability.py` | Minimal — consolidate into examples convention | ✅ Done |
| E5 | Example | F5 Lyapunov | 3 | ~80 % — `run_largest_lyapunov_exponent.py` | Add parameter-sensitivity demo; mandatory experimental warning | Not started |
| E6 | Example | F6 Entropy | 2 | ~90 % — `run_entropy_complexity.py` | Minimal — consolidate into examples convention | ✅ Done |
| E7 | Example | F7 Batch | 3 | ~85 % — `run_multi_signal_diagnostic_ranking.py` | Add JSON/CSV export demo; consolidate | Not started |
| E8 | Example | F8 Exog Screening | 3 | ~80 % — `run_exogenous_driver_redundancy_screening.py` | Add strong/weak/redundant driver narrative; consolidate | Not started |
| N1 | Notebook | F1 | 1 | — | `05_forecastability_profile_walkthrough` — profile vs scalar; non-monotone vs monotone | Not started |
| N2 | Notebook | F2 | 1 | — | `06_information_limits_and_compression` — ceiling vs realisation; compression warnings | Not started |
| N3 | Notebook | F3 | 2 | — | `07_predictive_information_learning_curves` — curve construction; plateau; bias-floor caveat | Not started |
| N4 | Notebook | F4, F5, F6 | 2–3 | — | `08_spectral_and_entropy_diagnostics` — Ω, PE/SE plane, complexity bands, optional LLE | Not started |
| N5 | Notebook | F7, F8 | 3 | — | `09_batch_and_exogenous_workbench` — batch ranking + exog screening + redundancy + BH | Not started |
| A1 | Agent adapter | F1–F8 | 3 | — | `triage_agent_payload_models.py` — Pydantic payload models for all diagnostics | Not started |
| A2 | Agent adapter | F1–F8 | 3 | A1 | `triage_summary_serializer.py` — result models → agent-safe payloads; schema version | Not started |
| A3 | Agent adapter | F1–F8 | 3 | A1, A2 | `triage_agent_interpretation_adapter.py` — concise summaries; warnings; experimental flags | Not started |
| N6 | Notebook | A1–A3 | 3 | — | `10_agent_ready_triage_interpretation` — triage → payload → summary → deterministic vs narrative | Not started |

**Agent payload fields per feature:**
F1: `profile_peak_horizon`, `profile_informative_horizons`, `profile_shape_label`, `profile_summary` ·
F2: `theoretical_ceiling_by_horizon`, `ceiling_summary`, `compression_warning`, `dpi_warning` ·
F3: `recommended_lookback`, `plateau_detected`, `reliability_warnings`, `lookback_summary` ·
F4: `spectral_predictability_score`, `spectral_summary`, `spectral_reliability_notes` ·
F5: `lyapunov_estimate`, `lyapunov_warning`, `experimental_flag_required` ·
F6: `permutation_entropy`, `spectral_entropy`, `complexity_band`, `complexity_summary` ·
F7: `batch_rank`, `diagnostic_vector`, `ranking_summary` ·
F8: `driver_scores_by_horizon`, `redundancy_flags`, `driver_recommendations`, `screening_summary`

---

## Phased delivery

### Phase 1 — Foundation & Profile Assembly

> Low risk · High value · No new estimators

```mermaid
flowchart LR
    A["Existing AMI/pAMI\nhorizon outputs"] --> B["F1 Profile Service"]
    B --> C["F2 Limit Diagnostics"]
    D["New SeriesDiagnosticScorer\nprotocol"] --> E["Phase 2 scorers"]
    F["Shared PSD / FFT\nutility"] --> E
    G["F10 Naming docs"] --> H["Done"]
```

| Item | Type | Effort |
|---|---|---|
| **F1 — Forecastability Profile** | New domain model `ForecastabilityProfile` + application service | S–M |
| **F2 — IT Limit Diagnostics** | New domain model `TheoreticalLimitDiagnostics` + service; exploitation ratio as `supported: bool = False` placeholder only | S |
| **F10 — Naming cleanup** | Documentation-only | Trivial |
| **Infra: `SeriesDiagnosticScorer` protocol** | New protocol alongside existing `DependenceScorer`; separates univariate diagnostics from bivariate dependence | S |
| **Infra: shared PSD / FFT utility** | Deterministic PSD helper in domain layer, used by F4 and F6 in Phase 2 | S |

#### F1 — Forecastability Profile & Informative Horizon Set

**Paper:** Catt (2026), `arXiv:2603.27074`

**Core math.** For forecast target $Y_{t+h}$ and information set $\mathcal{I}_t$:

$$F(h;\,\mathcal{I}_t) = I(Y_{t+h};\,\mathcal{I}_t) = H(Y_{t+h}) - H(Y_{t+h} \mid \mathcal{I}_t)$$

The **forecastability profile** is the map $h \mapsto F(h;\,\mathcal{I}_t)$ over
$h \in \{1,\dots,H\}$.

The **informative horizon set** is:

$$\mathcal{H}_\varepsilon = \bigl\{h : F(h;\,\mathcal{I}_t) \ge \varepsilon\bigr\}$$

> [!IMPORTANT]
> Define $\varepsilon$ relative to the surrogate upper band, not as an absolute
> constant. An absolute threshold risks admitting noise lags or rejecting useful
> ones.

**What to build:**
- Domain model `ForecastabilityProfile` with fields: `horizons`, `values`, `epsilon`,
  `informative_horizons`, `peak_horizon`, `is_non_monotone`, `summary`.
- Application service `ForecastabilityProfileService` that consumes existing
  horizon-wise MI outputs + config → `ForecastabilityProfile`.
- Recommendation vector: `model_now`, `review_horizons`, `avoid_horizons`.
- Data-processing inequality diagnostic: $F(h;\,T(\mathcal{I}_t)) \le F(h;\,\mathcal{I}_t)$.

**Architectural slot:** New application service + domain model. Not a scorer—output
is a structured profile, not a scalar.

**Where it goes:**
- `src/forecastability/domain/models/forecastability_profile.py`
- `src/forecastability/services/forecastability_profile_service.py`

**Statistical notes:**
- Inherits reliability of existing kNN MI estimator—no new estimation.
- Non-monotone profiles are expected (e.g. seasonal processes); do not treat
  non-monotonicity as an error.

**Example requirements:**
- Synthetic seasonal process (non-monotone profile).
- Simple AR process (smoothly decaying profile).
- Script prints horizons, values, informative set, recommendations.

**Theory-doc deliverable:**
`docs/theory/forecastability_profile.md` — formula, informative horizon set,
DPI warning, estimator reuse note.

**Acceptance criteria:**
- [x] No breaking changes to current AMI/pAMI outputs
- [x] Profile fully derived from deterministic core outputs
- [x] Integrated into `TriageResult` output
- [x] Example runs end-to-end
- [x] Theory doc cites Catt and explains the equations

---

#### F2 — Information-Theoretic Limit Diagnostics

**Paper:** Catt (2026), `arXiv:2603.27074`

**Core math.** Under log loss the maximum predictive improvement from
$\mathcal{I}_t$ is mutual information:

$$\mathbb{E}[-\log q_h(Y_{t+h} \mid \mathcal{I}_t)]
  = H(Y_{t+h} \mid \mathcal{I}_t)
  + \mathbb{E}\bigl[D_{\mathrm{KL}}(p_h^* \parallel q_h)\bigr]$$

The **exploitation ratio** is:

$$\chi_q(h;\,\mathcal{I}_t) = \frac{X_q(h;\,\mathcal{I}_t)}{F(h;\,\mathcal{I}_t)}$$

> [!WARNING]
> The MI ceiling holds strictly under log loss. Mapping to sMAPE or MSE
> requires distributional assumptions. Do not introduce a fake post-model
> metric.

**Scope decision:** This repo is pre-model and deterministic. Implement theoretical
ceiling diagnostics now. Exploitation ratio stays as schema placeholder
(`supported: False`) until a proper model-evaluation layer exists.

**What to build:**
- Domain model `TheoreticalLimitDiagnostics` with fields:
  `forecastability_ceiling_by_horizon`, `ceiling_summary`,
  `compression_warning`, `dpi_warning`, `exploitation_ratio_supported`.
- Service `TheoreticalLimitDiagnosticsService`.
- Warning logic for likely information-destroying transforms
  (aggregation, downsampling, lossy compression).

**Acceptance criteria:**
- [x] `run_triage()` can output theoretical ceiling wording
- [x] Exploitation ratio is not implemented (placeholder only)
- [x] Documentation clearly separates possibility from realisation

---

#### Infra: `SeriesDiagnosticScorer` protocol

The current `DependenceScorer` protocol takes `(past, future, *, random_state) → float`.
Spectral predictability (F4), Lyapunov (F5), and permutation entropy (F6) operate on
a single series, not a (past, future) pair.

**Decision:** Introduce a `SeriesDiagnosticScorer` protocol (ISP compliance) rather
than forcing univariate diagnostics through a bivariate interface. Register both
types in `ScorerRegistry` with a `kind` discriminator.

---

#### Phase 1 gate

```bash
uv run pytest -q -ra
uv run ruff check .
uv run ty check
```

- F1 + F2 integrated into `run_triage()` output
- Profile accessible from `TriageResult`
- Theory docs written for both features
- `SeriesDiagnosticScorer` protocol defined and tested
- PSD utility implemented with unit tests

---

### Phase 2 — New Deterministic Scorers

> Medium risk · Expands diagnostic surface · New computation

```mermaid
flowchart TD
    PSD["Shared PSD utility\n(from Phase 1)"] --> F4["F4 Spectral\nPredictability"]
    PSD --> F6s["F6 Spectral Entropy"]
    F6p["F6 Permutation\nEntropy"] --> F6band["F6 Complexity\nBand Service"]
    F6s --> F6band
    F4 --> REG["ScorerRegistry"]
    F6p --> REG
    MI["Existing kNN MI"] --> F3["F3 Learning\nCurves"]
```

| Item | Type | Effort |
|---|---|---|
| **F6 — Entropy-Based Complexity** | New scorer(s) + complexity-band interpretation service | M |
| **F4 — Spectral Predictability** | New scorer using Phase 1 PSD utility | S |
| **F3 — Predictive Info Learning Curves** | New application service (reuses MI estimator) | M |

> [!NOTE]
> F6 is ordered before F4 here because permutation entropy is cheaper,
> more robust, and has higher complementarity with AMI than spectral
> predictability alone. The spectral entropy component of F6 shares PSD
> code with F4.

#### F6 — Entropy-Based Complexity Triage

**Paper:** Ponce-Flores et al. (2020), Bandt & Pompe (2002)

**Core math.** For ordinal patterns of embedding order $m$ with probabilities $p(\pi)$:

$$H_{\mathrm{perm}} = -\sum_{\pi} p(\pi)\,\log p(\pi)$$

Normalised: $H_{\mathrm{perm}}^{\mathrm{norm}} = H_{\mathrm{perm}} / \log(m!)$

The PE + spectral entropy plane separates periodic, chaotic, and stochastic regimes.

**Statistical assessment:**
- **Reliability: High** — distribution-free, robust to outliers, monotone-invariant.
- **Sample-size:** $n \geq 1000$ for $m=5$; $n \geq 100$ for $m=3$ (coarser).
  For $n = 200$, cap at $m \leq 4$.
- **Risk:** Tie-breaking rule must be fixed and documented. PE is amplitude-blind.

**What to build:**
- `PermutationEntropyScorer` implementing `SeriesDiagnosticScorer`.
- Optional `SpectralEntropyScorer` (reuses F4 PSD utility).
- `ComplexityBandService` mapping (PE, spectral entropy) → `low` / `medium` / `high`.

**Acceptance criteria:**
- [x] Low overhead
- [x] Clear separation between estimator and interpretation
- [x] Works as complementary triage—never sole decision-maker
- [x] Tie-breaking rule documented

---

#### F4 — Spectral Predictability

**Paper:** Wang et al. (2025), `arXiv:2507.13556`

**Core math.** Given normalised PSD weights $p_i$, spectral entropy is:

$$H_a = -\sum_i p_i \log_a p_i$$

Normalised predictability:

$$\Omega(\mathbf{y}) = 1 - \frac{H_a(\mathbf{y})}{\log_a(N_{\mathrm{bins}})}$$

> [!WARNING]
> Normalise by number of frequency bins, not $\log_a(n)$. The latter
> makes the metric sample-size-dependent.

**Statistical assessment:**
- **Reliability: High** — use Welch or multitaper; $n \geq 128$.
- **Complementarity: Moderate** — captures linear predictability. Divergence
  between $\Omega$ and AMI signals nonlinearity.
- **Risk:** Raw periodogram is inconsistent. Non-stationary series need
  detrending / windowing.

**What to build:**
- `SpectralPredictabilityScorer` implementing `SeriesDiagnosticScorer`.
- Document: windowing rule, normalisation rule, zero-power handling.

**Acceptance criteria:**
- [x] Deterministic across runs
- [x] White noise scores low, periodic signal scores high
- [x] Runtime small relative to AMI path

---

#### F3 — Predictive Information Learning Curves

**Paper:** Morawski et al. (2025), `arXiv:2510.10744`

**Core math.** Predictive information between past and future blocks:

$$I_{\mathrm{pred}}(k, k') = I(X_{t:t-k+1};\; X_{t+k':t+1})$$

One-step special case (EvoRate):

$$\mathrm{EvoRate}(k) = I(X_{t:t-k+1};\; X_{t+1})$$

> [!CAUTION]
> The kNN MI estimator with $k_{\mathrm{nn}} = 8$ degrades severely for
> embedding dimension $d > 5$–$8$ (curse of dimensionality). At $n = 200$
> this estimator is **unreliable for $k > 3$**. Cap lookback at $k \leq 8$
> and emit explicit reliability warnings when $n$ is below the convergence
> regime. The curve may flatten from estimator saturation, not from genuine
> information plateau.

**Statistical assessment:**
- **Scientific value: High** — answers "how many lags do I need?", a genuinely
  different question from "is horizon $h$ forecastable?"
- **Reliability: Low / experimental** — MI in dimension $k$ is heavily biased
  downward for $k > 5$ with kNN.
- **Sample-size:** $n > 1000$ for $k = 10$; $n > 5000$ preferred.

**What to build:**
- Domain model `PredictiveInfoLearningCurve` with fields: `window_sizes`,
  `information_values`, `convergence_index`, `recommended_lookback`,
  `plateau_detected`, `reliability_warnings`.
- Service `PredictiveInfoLearningCurveService`.
- Plateau / convergence detection with mandatory bias-floor caveat.

**Acceptance criteria:**
- [x] Reproducible on tiny fixtures
- [x] Works as optional specialised analysis path
- [x] Emits reliability warnings when $n < 1000$ or $k > 8$
- [x] Does not distort scorer registry abstraction

---

#### Phase 2 gate

- All new scorers registered in `ScorerRegistry`
- Example scripts run end-to-end for F4, F6
- F3 service tested with synthetic finite-memory and long-memory processes
- Benchmark fixtures frozen with tolerances
- Complexity-band service tested
- Theory docs complete for F3, F4, F6

---

### Phase 3 — Experimental Scorer + Workflow Extensions

> Higher risk · Incremental improvements · Completes the surface

```mermaid
flowchart LR
    F5["F5 Lyapunov\n(experimental)"] --> REG["ScorerRegistry\n(gated)"]
    F7["F7 Batch\nextension"] --> RANK["Updated ranking\nwith new scorers"]
    F8["F8 Exog\nextension"] --> SCREEN["Redundancy\npenalty"]
    F9["F9 Benchmarks"] --> FIX["Fixtures for\nF1–F6"]
```

| Item | Type | Effort |
|---|---|---|
| **F5 — Largest Lyapunov Exponent** | New experimental scorer (gated behind config flag) | M–L |
| **F7 — Batch ranking extension** | Extend `run_batch_triage` with new scorer columns | S |
| **F8 — Exog screening extension** | Add inter-driver redundancy penalty to workbench | S |
| **F9 — Benchmark & reproducibility expansion** | Diagnostic regression fixtures + batch/exog regression + rebuild/verify scripts | M–L |

#### F5 — Largest Lyapunov Exponent

**Paper:** Wang et al. (2025), `arXiv:2507.13556`

**Core math.** Embed series via delay coordinates:

$$\mathbf{x}_t = (y_t,\; y_{t+\tau},\; \dots,\; y_{t+(m-1)\tau})$$

Track divergence:

$$\lambda \approx \frac{1}{\Delta t} \log \frac{\lVert\delta(\Delta t)\rVert}{\delta_0}$$

> [!CAUTION]
> Robust LLE estimation from noisy finite time series is an unsolved problem.
> Results are sensitive to $m$, $\tau$, and $\Delta t$. At $n = 200$–$2000$,
> reliable estimates require $m \leq 2$. Do not use for automated triage
> decisions without expert review and surrogate validation.

**Statistical assessment:**
- **Reliability: Low / experimental.**
- **Sample-size:** $n > 10^m$ (crude). At $m = 5$, need $n > 100\,000$.
- **Key risks:** Noise floor inflates LLE, making stochastic series appear
  chaotic. Requires Theiler window correction. Non-stationarity violates
  attractor assumption.

**Architectural decision:** Place in `experimental_scorers.py`. Gate behind
`experimental: true` in config. Never auto-include in composite triage score.

**Acceptance criteria:**
- [x] Stable deterministic execution
- [x] Conservative interpretation text
- [x] Gated behind explicit experimental flag in config
- [x] Not merged into composite readiness score
- [x] Mandatory surrogate validation documented

---

#### F7 — Batch Multi-Signal Ranking (incremental)

**Status:** `run_batch_triage()` already handles per-series triage, composite
ranking by 5 keys, `BatchTriageResponse` with summary/failure tables, and
CSV/JSON export. `comparison_report.py` adds priority scoring.

**Remaining work:**
- Add optional columns for new Phase 2 scorers (spectral predictability,
  permutation entropy, complexity band) to `BatchSummaryRow`.
- Expose individual diagnostic values alongside composite rank (avoids
  Simpson's paradox).
- Optional: ForeCA-inspired projection mode (P2B) as separate experimental
  service—defer to a future cycle.

**Statistical note:** Composite weighting across incommensurable scales
(MI in nats, PE in [0,1], Ω in [0,1]) must be transparent and configurable.
Recommend reporting the full diagnostic vector, not just the rank.

**Acceptance criteria:**
- [x] New scorer columns appear when those scorers are registered
- [x] Handles 50+ signals without memory blow-up
- [x] Composite ranking formula documented and configurable

---

#### F8 — Enhanced Exogenous Screening (incremental)

**Status:** Exogenous screening workbench already implements horizon-specific
usefulness scoring, per-driver keep/review/reject, and pruning with reason codes.

**Remaining work:**
- Add inter-driver redundancy penalty: $U(X_j; h) = I(X_j^{\mathrm{past}}; Y_{t+h}) - \alpha \cdot R(X_j, \mathcal{S})$
  where $R$ penalises redundancy against already-selected drivers.
- Extend `ExogenousScreeningWorkbenchConfig` with `redundancy_alpha`.
- Add Benjamini–Hochberg correction for $p \times H$ tests across drivers
  and horizons.

**Statistical note:** Greedy forward selection (one driver at a time) is safer
than simultaneous conditioning when $d > 5$ drivers at $n < 1000$.

**Acceptance criteria:**
- [x] Integrates with current exogenous triage flow
- [x] Deterministic and lightweight
- [x] BH correction documented and applied

---

#### F9 — Benchmark & Reproducibility Expansion

**Status:** Not started. Existing benchmark infrastructure covers only the original
AMI/pAMI univariate pipeline (5 frozen CSVs under `docs/fixtures/benchmark_examples/expected/`).
No frozen reference outputs exist for the new F1–F6 diagnostics.

**Why it matters:** Without regression fixtures, any refactor, dependency upgrade, or
estimator tweak can silently change diagnostic outputs. The repo already proves this
model works for AMI/pAMI—F9 extends the same guarantee to every new diagnostic.

##### Scope and deliverables

**A. Canonical diagnostic fixture dataset**

Create a small, deterministic fixture series set that exercises each diagnostic's
interesting behaviours:

| Fixture series | Primary purpose | Expected diagnostic signature |
|---|---|---|
| AR(1) φ=0.85, n=500 | Smooth monotone decay | F1: monotone profile, peak at h=1 |
| Seasonal AR + period 12, n=500 | Non-monotone profile | F1: non-monotone, peak near h=12 |
| White noise, n=500 | Null baseline | F4: Ω ≈ 0; F6: PE ≈ 1.0, band = high |
| Sine wave, n=500 | Maximal structure | F4: Ω ≈ 1.0; F6: PE ≈ 0.0, band = low |
| AR(2) finite-memory, n=1000 | Lookback plateau | F3: plateau at k=2–3 |
| Logistic map r=3.9, n=2000 | Chaotic dynamics | F5: λ̂ > 0 (experimental) |
| Mixed AR(1)+noise, n=500 | Medium complexity | F6: band = medium |

All fixtures generated from deterministic seeds (`random_state=42`). Store as
CSV or numpy `.npy` under `docs/fixtures/diagnostic_regression/inputs/`.

**B. Frozen expected outputs per diagnostic**

For each fixture × diagnostic combination, freeze the output fields into JSON
under `docs/fixtures/diagnostic_regression/expected/`:

| Diagnostic | Frozen fields | Tolerance |
|---|---|---|
| F1 ForecastabilityProfile | `horizons`, `values`, `informative_horizons`, `peak_horizon`, `is_non_monotone` | Values: `atol=1e-6`; sets: exact |
| F2 TheoreticalLimitDiagnostics | `forecastability_ceiling_by_horizon`, `compression_warning`, `dpi_warning` | Ceiling: `atol=1e-6`; text: exact |
| F3 PredictiveInfoLearningCurve | `window_sizes`, `information_values`, `recommended_lookback`, `plateau_detected` | Values: `atol=1e-4` (MI variance); lookback: ±1 |
| F4 SpectralPredictability | `omega` (scalar) | `atol=1e-8` (deterministic FFT) |
| F5 LargestLyapunovExponent | `lambda_estimate`, `is_experimental` | `atol=1e-4` (embedding sensitivity) |
| F6 ComplexityBandResult | `permutation_entropy`, `spectral_entropy`, `complexity_band` | PE: `atol=1e-8`; SE: `atol=1e-8`; band: exact |

> [!IMPORTANT]
> F3 tolerances are deliberately wider (`atol=1e-4`) because kNN MI estimates
> carry intrinsic variance at small sample sizes. F4 and F6 use deterministic
> FFT pipelines and can be held to machine-precision tolerances. F5 tolerances
> are moderate because the Rosenstein algorithm involves nearest-neighbor search
> on embedded trajectories.

**C. Regression test module**

Add `tests/test_diagnostic_regression.py` with:

- One parametrised test per diagnostic that loads fixture input, runs the service,
  and compares output fields against frozen expected within tolerances.
- A drift-detection test analogous to `test_fixture_verification_flags_drift`
  that corrupts one expected file and confirms the test fails.
- All tests must be deterministic (fixed seeds) and fast (< 30 s total).

**D. Rebuild and verify script**

Extend `scripts/rebuild_benchmark_fixture_artifacts.py` (or add a sibling
`scripts/rebuild_diagnostic_fixture_artifacts.py`) with:

- `--generate` mode: run all diagnostics on fixture inputs, write expected JSON.
- `--verify` mode: compare generated outputs against frozen expected.
- Print a summary table of pass/fail per fixture × diagnostic.

**E. Exogenous benchmark extension**

Extend the existing exogenous benchmark (`configs/benchmark_exog_panel.yaml`)
to record F8 extension fields (`redundancy_score`, `bh_significant`) in the
frozen outputs. Add one regression test that verifies the 7 existing case IDs
produce stable F8 results.

**F. Batch triage regression**

Add a fixture batch run (5–10 synthetic series) that freezes the F7 extension
columns (`spectral_predictability`, `permutation_entropy`, `complexity_band_label`)
and verifies ranking stability.

##### What to code

- [ ] Fixture generation script: deterministic series → CSV/npy
- [ ] Expected output generation script: run diagnostics → JSON
- [ ] `tests/test_diagnostic_regression.py`: parametrised fixture-vs-expected tests
- [ ] F8 regression fixture for exogenous benchmark extension fields
- [ ] F7 regression fixture for batch triage extension columns
- [ ] Drift-detection tests (corrupt + assert failure)
- [ ] CI integration: regression tests run in `uv run pytest -q -ra`

##### Suggested directory structure

```text
docs/fixtures/diagnostic_regression/
  inputs/
    ar1_smooth.csv
    seasonal_ar.csv
    white_noise.csv
    sine_wave.csv
    ar2_finite_memory.csv
    logistic_map.csv
    mixed_ar1_noise.csv
  expected/
    ar1_smooth/
      forecastability_profile.json
      theoretical_limit_diagnostics.json
      spectral_predictability.json
      complexity_band.json
    seasonal_ar/
      forecastability_profile.json
      ...
    ...
  expected_batch/
    batch_ranking.json
  expected_exog/
    exog_screening_f8.json
```

##### Acceptance criteria

- [ ] Every F1–F6 diagnostic has at least 2 fixture series with frozen expected outputs
- [ ] Regression tests detect intentional drift (tolerance-aware)
- [ ] Rebuild script can regenerate expected outputs from scratch
- [ ] Verify mode confirms no drift on clean checkout
- [ ] Exogenous benchmark includes F8 extension fields
- [ ] Batch benchmark includes F7 extension columns
- [ ] All deterministic, all fast (< 30 s total), all CI-friendly

---

#### Phase 3 gate

- F5 tagged as experimental with gated activation
- F7/F8 extensions integrated and tested
- F9: full regression fixture suite passing for F1–F6 outputs
- F9: batch and exogenous regression fixtures passing
- Theory docs complete for all methods
- Architect + statistician review completed

---

## Cross-cutting deliverables

These apply across all phases and must be maintained incrementally.

### Theory documentation framework

Each new method requires a page in `docs/theory/` with:
- Paper citation
- Exact formula(s)
- Estimator assumptions
- Interpretation notes
- Limitations and failure modes
- Implementation mapping to code

### Deterministic summary schema

Extend triage result payloads so future agents can narrate:
- Forecastability profile + informative horizons
- Theoretical ceiling
- Lookback recommendation
- Spectral predictability score
- Lyapunov estimate (when experimental flag is on)
- Complexity band
- Exogenous ranking

All fields must be stable, deterministic, and schema-versioned.

### Architecture enforcement

- No adapter imports in domain/application layers
- Plotting and serialisation remain adapter-only
- New domain models added to `triage/__init__.py`
- Root `__init__.py` `__all__` updated only for stable public API

---

## Epic cross-reference verification

Verified 2026-04-13 against source epic
[`not_planed/triage_extension_epic_math_grounded.md`](not_planed/triage_extension_epic_math_grounded.md):

| Epic item | Dev plan coverage | Notes |
|---|---|---|
| §1 SOLID / Hexagonal / Mathematical rules | Cross-cutting deliverables + Architecture enforcement | ✅ |
| §2 Definition of done (A–F) | Definition of done section (trimmed; epic §2 is canonical) | ✅ |
| §3 Implementation template (10-step) | Not duplicated; lives in epic only | ✅ By reference |
| F1 Forecastability Profile (P0) | Phase 1 — fully elaborated | ✅ Done |
| F2 IT Limit Diagnostics (P0) | Phase 1 — fully elaborated | ✅ Done |
| F3 Predictive Info Learning Curves (P1) | Phase 2 — fully elaborated; adds statistical assessment | ✅ Done |
| F4 Spectral Predictability (P1) | Phase 2 — fully elaborated; adds statistical assessment | ✅ Done |
| F5 Largest Lyapunov Exponent (P1) | Phase 3 — fully elaborated; adds statistical assessment | ✅ Done |
| F6 Entropy-Based Complexity (P1) | Phase 2 — fully elaborated; adds statistical assessment | ✅ Done |
| F7 Batch Multi-Signal Ranking (P2) | Phase 3 — incremental on existing `run_batch_triage()` | ✅ Done |
| F8 Enhanced Exog Screening (P2) | Phase 3 — incremental; adds BH FDR (beyond epic scope) | ✅ Done |
| F9 Benchmark Expansion (P3) | Phase 3 — now fully elaborated with fixture matrix, tolerances, scripts | ✅ Planned |
| F10 Permutation-AMI Naming (P3) | Phase 1 — documentation-only; convention already followed | ✅ Done |
| Infra: SeriesDiagnosticScorer | Phase 1 — protocol defined | ✅ Done |
| Infra: Shared PSD/FFT utility | Phase 1 — `spectral_utils.py` | ✅ Done |
| Examples per feature (epic §4.x.5/6) | New "Examples, Notebooks & Agent Payloads" section | ✅ Planned |
| Theory docs per feature (epic §4.x.7) | Cross-cutting deliverables — theory doc framework | ✅ Mostly done (F1–F6 theory docs exist) |

**Implementation proposal verification against papers:**

| Feature | Paper | Proposed approach | Assessment |
|---|---|---|---|
| F1 | Catt (2026) `arXiv:2603.27074` | Reuse AMI curve → assemble profile + informative horizon set | ✅ Correct — no new estimator needed; profile is derived from existing MI outputs |
| F2 | Catt (2026) `arXiv:2603.27074` | MI ceiling under log loss + exploitation ratio as placeholder | ✅ Correct — exploitation ratio deferred until model layer exists (pre-model repo) |
| F3 | Morawski et al. (2025) `arXiv:2510.10744` | EvoRate(k) via kNN MI with dimension-aware cap | ✅ Correct — mandatory reliability warnings compensate for kNN bias at high $k$ |
| F4 | Wang et al. (2025) `arXiv:2507.13556` | Welch PSD → spectral entropy → Ω scorer | ✅ Correct — normalise by $\log(N_{\text{bins}})$ not $\log(n)$ per paper |
| F5 | Wang et al. (2025) `arXiv:2507.13556` | Rosenstein LLE via delay embedding | ✅ Correct — experimental gating is appropriate given finite-sample instability |
| F6 | Ponce-Flores et al. (2020), Bandt & Pompe (2002) | PE + SE → complexity band service | ✅ Correct — auto-selected embedding order with sample-size guard |
| F7 | ForeCA-inspired, Goerg (2013) | Batch ranking with new scorer columns; ForeCA projection deferred | ✅ Correct — full ForeCA adds projection risk; incremental column extension is safer |
| F8 | CATS-inspired, Lu et al. (2024) | Deterministic redundancy penalty + BH FDR; no attention model | ✅ Correct — CATS attention model doesn't fit pre-model deterministic core; deterministic screening is the right adaptation |

---

## Exclusions (carried from won't-have)

These remain out of scope:

- Replacing per-horizon AMI/pAMI with a single aggregate metric
- Computing diagnostics on post-origin data
- Treating finite-sample pAMI anomalies as direct evidence
- Reopening delivered baseline as unfinished work
- New forecasting models or deep-learning dependencies in the triage core
- Feature-specific agent orchestration for every method
- Literal port of attention-based CATS into the deterministic layer
- GPU dependencies

---

## Definition of done (per feature)

Carried from epic §2 — every feature is complete when:

- [ ] Equation(s) translated into deterministic domain code
- [ ] Input validation and edge-case handling
- [ ] Unit-testable estimator/service implemented
- [ ] Result model with explicit fields and docstrings
- [ ] Integrated into `run_triage()` without breaking existing outputs
- [ ] One synthetic + one realistic example, runnable end-to-end
- [ ] Theory doc with formulas, citations, interpretation, limitations
- [ ] Stable deterministic summary payload exposed
- [ ] `uv run pytest -q -ra` · `uv run ruff check .` · `uv run ty check` all pass
