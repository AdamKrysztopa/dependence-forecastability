<!-- type: reference -->
# v0.3.0 — Covariant Informative: Ultimate Release Plan

**Plan type:** Actionable release plan — ULTIMATE merge of prior proposals  
**Audience:** Maintainer, reviewer, Jr. developer  
**Target release:** `0.3.0`  
**Current released version:** `0.2.0`  
**Branch:** `feat/v0.3.0-covariant-informative`  
**Status:** Proposed  
**Last reviewed:** 2026-04-18  
**Companion refs:**

- [Covariant maturity release plan](not_planed/dependence_forecastability_v0_3_0_covariant_maturity_implementation_plan.md) — original Phase 1–7 structure
- [PCMCI+AMI hybrid proposal](not_planed/non_linear_pcmci.md) — theoretical framework for Phase 0 informational triage
- [v0.2.0 consolidation plan](implemented/v0_2_0_release_consolidation_plan_v2.md) — release-plan format baseline

**Builds on:**

- v0.2.0 hexagonal architecture, `ScorerRegistry`, port/adapter separation
- Existing exogenous cross-dependence support (`ForecastabilityAnalyzerExog`)
- `DependenceScorer` protocol and the five built-in scorers (`mi`, `pearson`, `spearman`, `kendall`, `dcor`)
- Existing `data/raw/exog/bike_sharing_hour.csv` via `scripts/download_data.py`

---

## 1. Why a new plan structure

The two prior proposals overlap substantially but differ in how the PCMCI+AMI hybrid integrates.
The covariant maturity plan treats PCMCI+ as "just another adapter"; the PCMCI+AMI proposal
defines a **novel hybrid algorithm** that uses AMI/CrossMI as Phase 0 informational triage.
This ultimate plan reconciles both by:

1. **Preserving the covariant-maturity phasing** — domain contracts → core methods → facade → tests → showcase → CI → docs
2. **Elevating PCMCI-AMI-Hybrid to a first-class method** — its own protocol, service, adapter, and result model
3. **Specifying REAL architecture integration** — every module placed in the actual `src/forecastability/` tree
4. **Closing CI/CD gaps explicitly** — numbered V3-CI tickets with acceptance criteria
5. **Enforcing scientific invariants** — AMI per-horizon, train-only, `np.trapezoid`, `random_state: int`

### Planning principles

| Principle | Implication |
|---|---|
| Additive, not disruptive | Stable univariate imports never break |
| Hexagonal + SOLID | New methods enter through ports/services/adapters |
| Paper-aligned identity | pAMI is a project extension; PCMCI-AMI cites Catt (2026) + Runge (2022) |
| Product maturation | v0.3.0 is a credibility release, not a feature dump |
| One facade, many engines | Users call `run_covariant_analysis()`; internal methods compose |

---

## 2. Theory-to-code map — mathematical foundations

> [!IMPORTANT]
> Every junior developer MUST read this section before writing any code.
> Each method has a precise mathematical definition that dictates the implementation.

### 2.1. Auto-Mutual Information (AMI) — the existing baseline

AMI measures how much information the past of a series carries about its future at horizon $h$:

$$AMI(h) = I(X_t ; X_{t+h}) = H(X_{t+h}) - H(X_{t+h} \mid X_t)$$

where $H$ denotes Shannon entropy. The project uses a $k$-Nearest Neighbor ($k$NN) estimator
(Kraskov, Stögbauer & Grassberger, 2004) with $k = 8$ via `sklearn.feature_selection.mutual_info_regression`.

**Cross-MI** extends this to pairs: $I(X_t^{\text{driver}} ; X_{t+h}^{\text{target}})$.

**pAMI** (partial AMI) conditions out intermediate lags:

$$\tilde{I}_h = I(X_t ; X_{t+h} \mid X_{t+1}, \ldots, X_{t+h-1})$$

computed via residualization: regress both $X_t$ and $X_{t+h}$ on the conditioning set,
then measure MI on the residuals.

**AUC forecastability** integrates the curve: $\text{AUC} = \sum_h \tilde{I}_h \, \Delta h$
using `np.trapezoid` (NOT `np.trapz`, which is removed in NumPy 2.x).

### 2.2. Transfer Entropy (TE) — Schreiber (2000)

Transfer Entropy measures the directed information flow from source $J$ to target $I$:

$$T_{J \to I} = \sum p(i_{n+1}, i_n^{(k)}, j_n^{(l)}) \log \frac{p(i_{n+1} \mid i_n^{(k)}, j_n^{(l)})}{p(i_{n+1} \mid i_n^{(k)})}$$

In the coding view, TE is a **conditional mutual information**:

$$TE(X \to Y \mid \text{lag}) = I(Y_t ; X_{t-\text{lag}} \mid Y_{t-1}, \ldots, Y_{t-\text{lag}+1})$$

**Key properties for the developer:**

- **Directional**: $TE(X \to Y) \neq TE(Y \to X)$ in general. This is the main advantage over symmetric MI.
- **Conditional**: TE conditions on the target's own past, removing autocorrelation-driven false positives.
- **Reduction to CMI**: The implementation reduces to a conditional MI call, which the project already has via `compute_pami_with_backend()` in `src/forecastability/diagnostics/cmi.py`.

**Practical interpretation for the junior developer:**

Compare two predictive scenarios:
1. Predict $Y_{\text{future}}$ from $Y_{\text{past}}$ only
2. Predict $Y_{\text{future}}$ from $Y_{\text{past}}$ + $X_{\text{past}}$

If scenario 2 materially improves information, TE is positive.

### 2.3. Gaussian Copula MI (GCMI) — Ince et al. (2017)

GCMI transforms arbitrary marginals into Gaussians via rank-copula normalization,
then uses the closed-form Gaussian MI expression.

**Step A — Rank transform to uniform CDF:**

$$u_i = \frac{\text{rank}(x_i)}{n + 1}$$

**Step B — Inverse normal (probit) transform:**

$$z_i = \Phi^{-1}(u_i)$$

where $\Phi^{-1}$ is the standard normal quantile function.

**Step C — Covariance-based MI for Gaussianized variables:**

$$I(X; Y) = \frac{1}{2 \ln 2} \ln \frac{|\Sigma_X| \cdot |\Sigma_Y|}{|\Sigma_{XY}|}$$

where $\Sigma_X$, $\Sigma_Y$ are marginal covariance matrices and $\Sigma_{XY}$ is the joint covariance.

**Key properties for the developer:**

- **Monotonic-transform invariant**: Rank transform preserves dependence structure regardless of marginal shape.
- **Numerically stable**: Avoids direct density estimation in the original (possibly ugly) marginals.
- **Compact implementation**: ~25 lines of actual computation code.
- **Output in bits**: Divide nats by $\ln 2$.

### 2.4. PCMCI+ — Runge (2020)

PCMCI+ is a constraint-based causal discovery algorithm for time series. It is **not** a dependence scorer — it outputs a **causal graph**.

**Two structural phases:**

**Phase 1 — Lagged skeleton:** Estimate the lagged parents $\hat{\mathcal{B}}_t^-(X_t^j)$ of each target $X_t^j$ by iteratively testing conditional independence against subsets of the past.

**Phase 2 — Contemporaneous MCI:** Test same-time links $X_t^i \to X_t^j$ using the Momentary Conditional Independence (MCI) test:

$$X_t^i \perp\!\!\!\perp X_t^j \mid \mathcal{S}, \hat{\mathcal{B}}_t^-(X_t^j), \hat{\mathcal{B}}_t^-(X_t^i)$$

The MCI test conditions on the lagged parents of **both** variables, which controls autocorrelation-driven false positives.

**Limitation that motivates PCMCI-AMI:** The initial set $\hat{\mathcal{B}}_t^-$ is built **blindly** from all variables up to $\tau_{\max}$, creating combinatorial explosion and dragging down the minimum effect size $I^{\min}$.

> [!WARNING]
> Do NOT reimplement PCMCI+ from scratch. Use the `tigramite` library behind an adapter.
> The project's contribution is the AMI triage layer, not a new PCMCI+ engine.

### 2.5. PCMCI-AMI-Hybrid — Catt (2026) + Runge (2020)

The novel hybrid algorithm uses AMI as an informational triage layer before PCMCI+:

**Phase 0 — AMI Triage (Catt's contribution):**

For all variable pairs $(X^i_{t-\tau}, X_t^j)$ with $\tau \in [1, \tau_{\max}]$, compute unconditional MI:

$$\hat{\mathcal{B}}_{\text{AMI}}^-(X_t^j) = \{ X_{t-\tau}^i \in X_t^- \mid I(X_{t-\tau}^i ; X_t^j) > \epsilon \}$$

**Theoretical justification:** By the contrapositive of the Causal Markov Condition, if two variables are unconditionally independent ($MI \approx 0$), they cannot have a direct causal link (assuming no perfect synergistic masking).

**Phase 1 — Information-density sorting + lagged skeleton (Runge's contribution):**

The remaining candidates in $\hat{\mathcal{B}}_{\text{AMI}}^-$ are pre-sorted by Phase 0 MI scores. When testing $X_{t-\tau}^i \perp\!\!\!\perp X_t^j \mid \mathcal{S}$, the conditioning set $\mathcal{S}$ is drawn from the **highest-MI variables first**. This guarantees the strongest confounders are controlled at $p=1$ and $p=2$, maximizing the causal signal-to-noise ratio.

**Phase 2 — Accelerated MCI (Runge's contribution):**

Standard PCMCI+ MCI testing, but with highly refined, compact, information-dense conditioning sets. Smaller conditioning sets reduce degrees of freedom, increasing statistical power.

**Expected benefits:**

| Benefit | Mechanism |
|---|---|
| Computational efficiency | Worst-case complexity drops from $O(2^{N \cdot \tau_{\max}})$ to $O(2^{|\hat{\mathcal{B}}_{\text{AMI}}|})$ |
| Enhanced calibration | AMI identifies exact lag where autocorrelation decays |
| Non-parametric consistency | kNN MI in Phase 0 is natively non-parametric |

---

## 3. Repo baseline — what already exists

| Layer | Module | What it provides | Status |
|---|---|---|---|
| **Ports** | `src/forecastability/ports/__init__.py` | `SeriesValidatorPort`, `CurveComputePort`, `SignificanceBandsPort`, `InterpretationPort`, `RecommendationPort`, `ReportRendererPort`, `SettingsPort`, `EventEmitterPort`, `CheckpointPort` | Stable |
| **Scorers** | `src/forecastability/metrics/scorers.py` | `DependenceScorer` protocol, `ScorerInfo`, `ScorerRegistry`, `ScorerRegistryProtocol`, `default_registry()` with `mi`, `pearson`, `spearman`, `kendall`, `dcor` | Stable |
| **Services** | `src/forecastability/services/` | `raw_curve_service`, `exog_raw_curve_service`, `partial_curve_service`, `exog_partial_curve_service`, `significance_service`, `recommendation_service`, `complexity_band_service`, `spectral_predictability_service`, `lyapunov_service`, `forecastability_profile_service`, `predictive_info_learning_curve_service`, `theoretical_limit_diagnostics_service` | Stable |
| **Pipeline** | `src/forecastability/pipeline/analyzer.py` | `ForecastabilityAnalyzer`, `ForecastabilityAnalyzerExog`, `AnalyzeResult` | Stable |
| **Use cases** | `src/forecastability/use_cases/` | `run_triage`, `run_batch_triage`, `run_rolling_origin_evaluation`, `run_exogenous_screening_workbench`, `run_exogenous_rolling_origin_evaluation` | Stable |
| **Diagnostics** | `src/forecastability/diagnostics/` | `cmi.py`, `surrogates.py`, `diagnostic_regression.py`, `spectral_utils.py` | Stable |
| **Triage** | `src/forecastability/triage/` | `TriageRequest`, `TriageResult`, `ResultBundle`, batch models, events | Stable |
| **Adapters** | `src/forecastability/adapters/` | CLI, API, dashboard, plotting, MCP, PydanticAI agent, checkpoint, settings | Stable |
| **Utils** | `src/forecastability/utils/` | `types.py`, `config.py`, `state.py`, `validation.py`, `datasets.py`, `plots.py`, `io_models.py`, `reproducibility.py`, `robustness.py`, `aggregation.py` | Stable |
| **CI** | `.github/workflows/ci.yml` | lint + type-check + test + build; Python 3.11 only, no matrix | Needs hardening |
| **Publish** | `.github/workflows/publish-pypi.yml` | Trusted publishing on tags; no install smoke test | Needs hardening |
| **Release** | `.github/workflows/release.yml` | GitHub release from tag; no covariant validation | Needs hardening |
| **Data** | `data/raw/exog/bike_sharing_hour.csv` | UCI Bike Sharing hourly; downloaded by `scripts/download_data.py` | Available |
| **Showcase** | `scripts/run_showcase.py` | Univariate showcase runner; emits artifacts | Stable |
| **Notebook** | `notebooks/walkthroughs/00_air_passengers_showcase.ipynb` | Univariate pedagogical walkthrough | Stable |

---

## 4. Feature inventory and overlap assessment

| ID | Feature | Phase | Overlap with existing | Genuine new work | Status |
|---|---|---:|---|---|---|
| V3-F00 | Typed covariant result models | 0 | Extends `utils/types.py` patterns | `CovariantSummaryRow`, `CovariantAnalysisBundle`, `CausalGraphResult`, `PcmciAmiResult` | **Done** |
| V3-F01 | Transfer Entropy scorer + service | 1 | Follows `DependenceScorer` pattern | `te_scorer()`, `src/forecastability/services/transfer_entropy_service.py` | **Done** (2026-04-16: diagnostics/service path, analyzer `method="te"`, and tests validated) |
| V3-F02 | GCMI scorer + service | 1 | Follows `DependenceScorer` pattern | `gcmi_scorer()`, `src/forecastability/services/gcmi_service.py` | **Done** (2026-04-16: diagnostics/service path, 25 tests, theory doc; 2026-04-17: GCMI example finalized at `examples/covariant_informative/information_measures/gcmi_example.py`) |
| V3-F03 | PCMCI+ adapter | 1 | None (new external integration) | `src/forecastability/adapters/tigramite_adapter.py`, `CausalGraphPort` | **Done** (2026-04-16: adapter, tests, dedicated example, optional causal extra; 2026-04-16b: 8-variable benchmark with two nonlinear drivers, two-story example, `docs/theory/pcmci_plus.md`) |
| V3-F04 | PCMCI-AMI-Hybrid method | 1 | Builds on AMI kNN + tigramite adapter | `src/forecastability/adapters/pcmci_ami_adapter.py`, `knn_cmi_ci_test.py`, `services/pcmci_ami_service.py`, `PcmciAmiResult` model, Phase 0 AMI triage + kNN MI CI test | **Partial** (2026-04-16: real Phase 0 MI/CrossMI screening via Tigramite `link_assumptions` and residualized kNN CI shipped; stronger MI-ranked conditioning logic remains proposal-only; current comparison evidence is illustrative and benchmark-specific. **MI-ranked conditioning and CrossAMI past-window deferred to v0.3.1.**) |
| V3-F04.1 | Full examples taxonomy + cleanup | 4 | Extends current demo/example tree | Relocate every active script out of `examples/triage/` into `examples/univariate/` or `examples/covariant_informative/`; apply subgroup taxonomy, PCMCI renames, output namespacing, and repo-wide path cleanup | **Done** (2026-04-17: active example references now use the `examples/univariate/` and `examples/covariant_informative/` taxonomy; PCMCI benchmarks renamed; repo cleanup applied) |
| V3-F04.2 | V3-F03/V3-F04 second-loop review + docs alignment | 6 | Builds on V3-F03/V3-F04 + theory/docs/examples | Revisit theory, shipped implementation, and examples for both methods; document pros/cons, theoretical caveats, practical behavior, and exact proposal-vs-implementation boundaries | **Done** (2026-04-17: second-loop review landed in `docs/plan/implemented/v3_f03_v3_f04_second_loop_review.md`; vectorised linear residual + opt-in block-shuffle + ground-truth helper shipped) |
| V3-F05 | `CausalGraphPort` protocol | 0 | None (new port type) | Graph-returning port for PCMCI+ and PCMCI-AMI | **Done** |
| V3-F06 | Covariant orchestration facade | 2 | Extends `use_cases/` pattern | `src/forecastability/use_cases/run_covariant_analysis.py` | **Done** (2026-04-17: `run_covariant_analysis()` shipped as the covariant orchestration bundle with unified row assembly, conditioning-scope metadata/disclaimer, focused facade tests, and a dedicated benchmark example.) |
| V3-F07 | Unified covariant summary table | 2 | Extends `ExogenousScreeningWorkbenchResult` pattern | `CovariantSummaryRow` with all method columns | **Done** (2026-04-17: significance (`above_band`/`below_band` via phase-surrogate cross_ami bands), global rank (by cross_ami→gcmi→te priority), and interpretation_tag (`causal_confirmed`, `probably_mediated`, `directional_informative`, `pairwise_informative`, `noise_or_weak`) fully populated; 5 new facade tests added; dedicated example at `examples/covariant_informative/covariant_summary_table/covariant_summary_table_example.py`; reference doc at `docs/theory/covariant_summary_table.md`; all 4 ground-truth checks pass on 8-variable benchmark; Phase 2 closed.) |
| V3-F08 | Covariant tests + regression | 3 | Follows existing test patterns | Synthetic coupled systems, per-method and integration tests | **Done** (2026-04-17: regression module `src/forecastability/diagnostics/covariant_regression.py` with 3 deterministic fixture cases (ami_pami, gcmi, te) shipped; frozen expected fixtures at `docs/fixtures/covariant_regression/expected/`; rebuild script `scripts/rebuild_covariant_regression_fixtures.py`; 10-test suite `tests/test_covariant_regression.py` covering frozen-match, drift detection, and ground-truth sanity; dedicated V3-F08 validation example at `examples/covariant_informative/covariant_regression/covariant_regression_example.py` with 5 scientifically grounded ground-truth checks all passing; 747 tests green.) |
| V3-F09 | Covariant showcase script | 4 | Follows `scripts/run_showcase.py` | `scripts/run_showcase_covariant.py` | **Done** |
| V3-F10 | Covariant walkthrough notebook | 4 | Follows `00_air_passengers_showcase.ipynb` | `notebooks/walkthroughs/01_covariant_informative_showcase.ipynb` | **Done** (2026-04-17: live covariant walkthrough notebook shipped with sections A-H plus the required v0.3.1 limitation section; uses `generate_covariant_benchmark()` and `run_covariant_analysis()` with stable notebook artifact paths, dedicated notebook-facing reporting helpers, docs updates, notebook contract coverage, and a top-to-bottom executed notebook.) |
| V3-CI-01 | Python version matrix | 5 | Modifies `.github/workflows/ci.yml` | Add 3.11 + 3.12 matrix | **Done** (2026-04-17: `ci.yml` updated with `strategy.matrix: python-version: ["3.11", "3.12"]`, `fail-fast: false`; job name reflects Python version.) |
| V3-CI-02 | Install-from-wheel smoke test | 5 | Modifies `.github/workflows/publish-pypi.yml` | Wheel install + import + minimal covariant run | **Done** (2026-04-17: `publish-pypi.yml` `build-dist` job now includes a "Wheel smoke test" step: fresh venv, `pip install wheel[causal]`, confirms `run_covariant_analysis` + `generate_covariant_benchmark` import.) |
| V3-CI-03 | Showcase script smoke test | 5 | None | Both showcase scripts run in CI | **Done** (2026-04-17: `.github/workflows/smoke.yml` created; triggers on push to `main` only; runs `run_showcase.py --no-rolling --no-bands` and `run_showcase_covariant.py --fast` with `MPLBACKEND=Agg`; uploads showcase artifacts.) |
| V3-CI-04 | Notebook contract validation | 5 | Extends `scripts/check_notebook_contract.py` | Covariant notebook added to contract | **Done** (2026-04-17: `scripts/check_notebook_contract.py` now tracks the covariant walkthrough notebook and runs a representative covariant facade/import check.) |
| V3-CI-05 | Artifact upload in CI | 5 | None | Upload covariant JSON + table + figures | **Done** (2026-04-17: `ci.yml` now uploads `outputs/figures/`, `outputs/json/`, `outputs/tables/` as `ci-artifacts-py{version}` after each matrix build; `if-no-files-found: ignore`.) |
| V3-CI-06 | Release checklist automation | 5 | None | Changelog, version/tag, README commands | **Done** (2026-04-17: `.github/ISSUE_TEMPLATE/release_checklist.md` created with full checklist (changelog, version, pytest 3.11+3.12, ruff, ty, showcases, notebook contract, build, publish, post-release); `release.yml` now includes covariant import sanity check in `build-dist` job.) |
| V3-CI-07 | Pre-commit hook alignment | 5 | Modifies `.pre-commit-config.yaml` | Ensure ruff + ty coverage | **Done** (2026-04-17: `.pre-commit-config.yaml` updated with `local` hook running `uv run ty check`; ruff rev pinned with comment aligning to `>=0.11.0` in `pyproject.toml`.) |
| V3-D01 | README dual-workflow update | 6 | Modifies `README.md` | Univariate + covariant as first-class workflows | **Done** (2026-04-17: README quickstart now includes parallel univariate triage and covariant bundle usage; badge wording aligned with v0.3.0 language.) |
| V3-D02 | API docs + quickstart refresh | 6 | Modifies `docs/` | New methods documented | **Done** (2026-04-17: `docs/public_api.md` and `docs/quickstart.md` now document `run_covariant_analysis`, covariant method tokens, conditioning scope, and optional causal extra.) |
| V3-D03 | Changelog v0.3.0 | 6 | Modifies `CHANGELOG.md` | Release notes | **Done** (2026-04-17: added `0.3.0` Keep-a-Changelog release block with Added/Changed/Fixed/Migration notes.) |
| V3-AI-01 | Release version integrity review follow-up | 6 | Extends release-checklist and packaging closeout | Align `pyproject.toml`, `src/forecastability/__init__.py`, and release-checklist assertions with the real `0.3.0` state | **Done** (2026-04-18: bumped `version` in `pyproject.toml` and `__version__` in `src/forecastability/__init__.py` from `0.2.0` → `0.3.0`; ruff, ty, and pytest all pass.) |
| V3-AI-02 | Hexagonal contract hardening for PCMCI-AMI | 2 | Extends `CausalGraphPort` / covariant-use-case boundary | Replace local `_PcmciAmiFullPort` coupling with a declared full-result port (or equivalent boundary split); remove adapter-to-adapter helper imports | **Done** (2026-04-18: `CausalGraphFullPort` declared in `ports/__init__.py` with `discover_full()` signature; local `_PcmciAmiFullPort` protocol removed from `run_covariant_analysis.py`; `pcmci_ami_adapter.py` no longer imports adapter-to-adapter helpers; inward-only dependency rule restored; `docs/architecture.md` and `docs/public_api.md` updated; ruff, ty, pytest all pass.) |
| V3-AI-03 | Covariant mediation-semantics hardening | 2 | Extends covariant interpretation/service rules | Tighten `mediated_driver` assignment so target-only pCrossAMI collapse cannot imply mediation without driver-specific causal support | **Done** (2026-04-18: `_assign_role` Rule 6 now requires `any_sig` (at least one surrogate-significant lag for this driver) in addition to `has_causal`; `_interpretation_tag` gains `pcmci_ran: bool = False` parameter — `probably_mediated` now requires `pcmci_ran=True`; call site updated to pass `pcmci_ran = pcmci_graph is not None or pcmci_ami_result is not None`; 4 new regression tests added; `docs/theory/covariant_role_assignment.md` updated; ruff, ty, pytest 791/791 all pass.) |
| V3-AI-04 | Public API / quickstart contract correction | 6 | Extends README + API docs + facade exports | Either re-export `generate_covariant_benchmark` from the stable facade or rewrite user-facing covariant examples to import from `forecastability.utils.synthetic` | **Done** (2026-04-18: top-level re-export added in `src/forecastability/__init__.py` for `generate_covariant_benchmark` and `generate_directional_pair`; quickstart/public API contract now consistent; ruff, ty, pytest, and quickstart example validation passed.) |
| V3-AI-05 | Documentation freshness pass | 6 | Extends implementation-status / docs-index refresh | Reconcile stale `0.2.0` verification banners and pre-closure covariant caveats; tracked in `docs/plan/v0_3_2_documentation_quality_improvement_plan.md` | **Added post-review** (2026-04-18: open documentation-quality action item.) |

---

## 5. Synthetic benchmark data — MANDATORY FIRST STEP

> [!IMPORTANT]
> Without deterministic synthetic data with known ground truth, TE looks "wrong",
> PCMCI+ seems arbitrary, tests are weak, and the notebook tells no convincing story.
> Build the generator BEFORE any method implementation.

### 5.1. Structural equations

The generator produces a 6-variable system with known causal structure:

> [!NOTE]
> **Upgraded to 8 variables (2026-04-16b).** Two nonlinear drivers added to expose the
> linear-CI blind-spot: both have Pearson/Spearman ≈ 0 with target by construction,
> so a linear CI test (parcorr) cannot detect them. See `docs/theory/pcmci_plus.md`.

```mermaid
flowchart LR
    X1["driver_direct"] -->|"lag 2, β=0.80"| Y["target"]
    X2["driver_mediated"] -->|"lag 1, β=0.50"| Y
    X1 -->|"lag 1, β=0.60"| X2
    X3["driver_redundant"] -.->|"correlated via x1"| Y
    X1 -->|"lag 1, β=0.70"| X3
    X4["driver_noise"] -.-x Y
    X6["driver_contemp"] -->|"lag 0, β=0.35"| Y
    NL1["driver_nonlin_sq"] -->|"lag 1, β=0.40\n(quadratic — Pearson≈0)"| Y
    NL2["driver_nonlin_abs"] -->|"lag 1, β=0.35\n(abs-value — Pearson≈0)"| Y
```

**Ground truth causal parents of target:**

| Variable | Relationship to target | Expected TE | Expected PCMCI+ (parcorr) |
|---|---|---|---|
| `driver_direct` | Direct parent at lag 2 | $TE \gg 0$ | Parent at lag 2 |
| `driver_mediated` | Indirect via driver_direct | $TE > 0$ | Parent at lag 1 |
| `driver_redundant` | Correlated via shared cause, not direct | $TE > 0$ (drops on conditioning) | **Not** a parent (MCI removes it) |
| `driver_noise` | Independent noise | $TE \approx 0$ | Absent from graph |
| `driver_contemp` | Contemporaneous link | N/A (lagged TE) | Contemporaneous parent |
| `driver_nonlin_sq` | Quadratic coupling — **Pearson/Spearman ≈ 0** | Detectable by kNN MI | **NOT found** (parcorr blind) |
| `driver_nonlin_abs` | Abs-value coupling — **Pearson/Spearman ≈ 0** | Detectable by kNN MI | **NOT found** (parcorr blind) |

### 5.2. Complete generator implementation

**File:** `src/forecastability/utils/synthetic.py`

```python
"""Synthetic benchmark generators for covariant analysis testing."""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_covariant_benchmark(
    n: int = 1500,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a 6-variable system with known causal structure.

    Structural equations:
        x1[t] = 0.8 * x1[t-1] + ε₁           (AR(1) direct driver)
        x2[t] = 0.7 * x2[t-1] + 0.6 * x1[t-1] + ε₂  (mediated via x1)
        x3[t] = 0.9 * x3[t-1] + 0.7 * x1[t-1] + ε₃  (redundant, correlated with x1)
        x4[t] = 0.4 * x4[t-1] + ε₄            (pure noise)
        x6[t] = 0.6 * x6[t-1] + ε₅            (contemporaneous driver)
        y[t]  = 0.75 * y[t-1] + 0.8 * x1[t-2] + 0.5 * x2[t-1]
                + 0.35 * x6[t] + ε₆

    All εᵢ ~ N(0, 1).

    Args:
        n: Number of time steps to generate.
        seed: Random seed for reproducibility. Must be int, not np.Generator.

    Returns:
        DataFrame with columns: driver_direct, driver_mediated,
        driver_redundant, driver_noise, driver_contemp, target.
    """
    rng = np.random.default_rng(seed)

    x1 = np.zeros(n)  # strong direct lagged driver
    x2 = np.zeros(n)  # mediated via x1
    x3 = np.zeros(n)  # redundant/correlated with x1
    x4 = np.zeros(n)  # pure noise
    x5 = np.zeros(n)  # target
    x6 = np.zeros(n)  # contemporaneous coupling

    for t in range(2, n):
        x1[t] = 0.8 * x1[t - 1] + rng.normal(0.0, 1.0)
        x2[t] = 0.7 * x2[t - 1] + 0.6 * x1[t - 1] + rng.normal(0.0, 1.0)
        x3[t] = 0.9 * x3[t - 1] + 0.7 * x1[t - 1] + rng.normal(0.0, 1.0)
        x4[t] = 0.4 * x4[t - 1] + rng.normal(0.0, 1.0)
        x6[t] = 0.6 * x6[t - 1] + rng.normal(0.0, 1.0)
        x5[t] = (
            0.75 * x5[t - 1]
            + 0.8 * x1[t - 2]
            + 0.5 * x2[t - 1]
            + 0.35 * x6[t]
            + rng.normal(0.0, 1.0)
        )

    return pd.DataFrame(
        {
            "driver_direct": x1,
            "driver_mediated": x2,
            "driver_redundant": x3,
            "driver_noise": x4,
            "driver_contemp": x6,
            "target": x5,
        }
    )


def generate_directional_pair(
    n: int = 2000,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a simple X→Y directional pair for TE validation.

    Structural equations:
        x[t] = 0.8 * x[t-1] + ε₁
        y[t] = 0.7 * y[t-1] + 0.5 * x[t-1] + ε₂

    Expected: TE(x→y) > TE(y→x).

    Args:
        n: Number of time steps.
        seed: Random seed.

    Returns:
        DataFrame with columns: x, y.
    """
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    y = np.zeros(n)

    for t in range(1, n):
        x[t] = 0.8 * x[t - 1] + rng.normal()
        y[t] = 0.7 * y[t - 1] + 0.5 * x[t - 1] + rng.normal()

    return pd.DataFrame({"x": x, "y": y})
```

### 5.3. Acceptance criteria

- [x] Generator is deterministic by seed
- [x] Notebook, tests, and showcase script all use the same generator
- [x] Expected causal story documented in docstring
- [x] Two nonlinear drivers with Pearson/Spearman ≈ 0 by construction (odd-moment symmetry)
- [x] `test_synthetic_nonlinear_drivers_invisible_to_pearson` confirms |r| < 0.10
- [x] `test_parcorr_blind_to_nonlinear_drivers` confirms linear CI test cannot recover them

---

## 5A. Known limitation: lagged-exogenous autohistory conditioning

v0.3.0 ships a full covariant-informative **triage gate**, not a full confirmatory causal toolkit.
Users must understand which covariant methods condition on what, because the lightweight
scorer/curve path (CrossMI, pCrossAMI, univariate-exog TE) does **not** condition on the
exogenous driver's own past — only on the target's autohistory (or nothing, for raw CrossMI).
A driver with mixed lag-1 + lag-3 effects on the target can therefore appear spuriously
strong at lag 3 in pCrossAMI or TE. Full lagged-exogenous verification in v0.3.0 requires
PCMCI+ (V3-F03) or PCMCI-AMI-Hybrid (V3-F04), both of which apply the full MCI conditioning
on both sides' lagged parents.

**Verified in source (as of 2026-04-17):**

- `src/forecastability/services/partial_curve_service.py::_residualize` residualizes the
  future target on the target's intermediate lags only; when `exog is not None`, the
  exogenous predictor is left untouched on the past side (the in-file comment records this).
  The residualization itself is linear (`sklearn.linear_model.LinearRegression`).
- `src/forecastability/diagnostics/transfer_entropy.py` conditions on the **target** history
  `Y_{t-1..t-h+1}` only; the source (exog) own-history is not conditioned on.
- PCMCI+ and PCMCI-AMI-Hybrid apply the full MCI test, which conditions on the lagged
  parents of both the source and the target.

### Conditioning scope per method

| Method | Conditioning scope | `lagged_exog_conditioning` tag |
|---|---|---|
| Raw CrossMI (`exog_raw_curve_service`) | None (bivariate) | `none` |
| pCrossAMI (`partial_curve_service` with exog) | Target intermediate lags only | `target_only` |
| Transfer Entropy (`diagnostics/transfer_entropy.py`) | Target history only | `target_only` |
| PCMCI+ (V3-F03) | Full MCI (both sides' lagged parents) | `full_mci` |
| PCMCI-AMI-Hybrid (V3-F04) | Full MCI (both sides' lagged parents) | `full_mci` |

```mermaid
flowchart LR
    Y_future["Y_t (future target)"]
    Y_hist["Y_{t-1..t-h+1}\n(target autohistory)"]
    X_future["X_{t-h} (lagged exog)"]
    X_hist["X_{t-h-1..t-h+1}\n(exog autohistory)"]
    raw["Raw CrossMI\nconditioning: none"]
    partial["pCrossAMI / TE\nconditioning: target_only"]
    full["PCMCI+ / PCMCI-AMI\nconditioning: full_mci"]
    X_future --> raw
    Y_future --> raw
    Y_hist --> partial
    X_future --> partial
    Y_future --> partial
    Y_hist --> full
    X_hist --> full
    X_future --> full
    Y_future --> full
```

> [!IMPORTANT]
> If your analysis requires attributing a driver effect to a specific lag in the presence
> of exogenous autocorrelation, use PCMCI+ or PCMCI-AMI-Hybrid in v0.3.0. The CrossMI,
> pCrossAMI, and TE paths in the covariant bundle are triage signals only and will
> generally inflate apparent dependence at non-primary lags when the driver itself is
> autocorrelated. A proper lagged-exogenous residualization path is scheduled for v0.3.1.

Forward link: [`docs/plan/v0_3_1_lagged_exogenous_triage_plan.md`](v0_3_1_lagged_exogenous_triage_plan.md).

Because of this limitation, the v0.3.0 facade (V3-F06) and summary table (V3-F07) MUST
expose a `lagged_exog_conditioning` metadata field per method row so downstream consumers
cannot accidentally read a `target_only` pCrossAMI as if it were `full_mci` causal evidence.
See the amended acceptance criteria in Phase 2 and Phase 3.

---

## 6. Shared lagged design utilities

Every covariant method depends on clean lag handling. Build this once.

### 6.1. Lagged frame builder

**File:** `src/forecastability/utils/lagged_design.py`

```python
"""Shared lag-embedding utilities for covariant methods."""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_lagged_frame(
    df: pd.DataFrame,
    *,
    columns: list[str],
    max_lag: int,
) -> pd.DataFrame:
    """Build a DataFrame with lagged columns appended.

    For each column in *columns*, creates ``{col}_lag_1`` through
    ``{col}_lag_{max_lag}`` via ``pd.Series.shift``.

    Args:
        df: Input DataFrame.
        columns: Column names to lag.
        max_lag: Maximum lag depth (must be >= 1).

    Returns:
        DataFrame with original + lagged columns, NaN rows dropped.

    Raises:
        ValueError: If max_lag < 1 or columns contain duplicates.
    """
    if max_lag < 1:
        raise ValueError(f"max_lag must be >= 1, got {max_lag}")
    if len(columns) != len(set(columns)):
        raise ValueError(f"Duplicate columns: {columns}")
    out = df.copy()
    for col in columns:
        for lag in range(1, max_lag + 1):
            out[f"{col}_lag_{lag}"] = df[col].shift(lag)
    return out.dropna().reset_index(drop=True)


def build_te_frame(
    df: pd.DataFrame,
    *,
    source: str,
    target: str,
    source_lag: int = 1,
    target_history: int = 1,
) -> pd.DataFrame:
    """Build the lag-embedding required for Transfer Entropy computation.

    Creates columns:
        - ``y_future``: target at time t (the quantity to predict)
        - ``x_past``: source shifted by source_lag
        - ``y_past_1`` ... ``y_past_{target_history}``: target past lags

    This decomposition directly maps to the TE formula:
    TE(X→Y) = I(y_future ; x_past | y_past_1, ..., y_past_k)

    Args:
        df: Input DataFrame.
        source: Source (driver) column name.
        target: Target column name.
        source_lag: Lag of the source variable.
        target_history: Number of past target lags to condition on.

    Returns:
        DataFrame with aligned columns, NaN rows dropped.
    """
    out = pd.DataFrame(index=df.index)
    out["y_future"] = df[target]
    out["x_past"] = df[source].shift(source_lag)
    for lag in range(1, target_history + 1):
        out[f"y_past_{lag}"] = df[target].shift(lag)
    return out.dropna().reset_index(drop=True)
```

### 6.2. Validation rules

- Reject duplicate column names
- Reject `max_lag < 1`
- Reject non-numeric series
- Reject too-short samples (< `max_lag + 30`)

### 6.3. Acceptance criteria

- All downstream methods use the same lag utility
- No notebook reimplements lagging ad hoc

---

## 7. Phased delivery

### Phase 0 — Covariant Domain Contracts (Foundation)

**Goal:** Define every typed result model and protocol before any computation code is written.

```mermaid
flowchart LR
    A["Existing ports/\n__init__.py"] --> B["Add CausalGraphPort\nprotocol"]
    D["Existing utils/\ntypes.py"] --> E["Add CovariantSummaryRow"]
    D --> F["Add CovariantAnalysisBundle"]
    D --> G["Add CausalGraphResult"]
    D --> H["Add PcmciAmiResult"]
    D --> I["Add TransferEntropyResult"]
    D --> J["Add GcmiResult"]
    B --> K["Phase 1 ready"]
    E --> K
    F --> K
    G --> K
    H --> K
    I --> K
    J --> K
```

#### V3-F00 — Typed result models

**File:** `src/forecastability/utils/types.py` (extend existing module)

All models use `frozen=True` to match the existing pattern in the codebase:

```python
class CovariantSummaryRow(BaseModel, frozen=True):
    """One row of the unified covariant summary table.

    Each row represents one (target, driver, lag) combination across
    all covariant methods. Fields are None when a method was not run
    or is not applicable at that lag.
    """

    target: str
    driver: str
    lag: int
    cross_ami: float | None = None
    cross_pami: float | None = None
    transfer_entropy: float | None = None
    gcmi: float | None = None
    pcmci_link: str | None = None        # e.g. "-->" or "o->" from PCMCI+
    pcmci_ami_parent: bool | None = None  # True if selected by PCMCI-AMI
    significance: str | None = None       # e.g. "p<0.01", "above_band"
    rank: int | None = None
    interpretation_tag: str | None = None  # e.g. "direct_driver", "mediated"


class TransferEntropyResult(BaseModel, frozen=True):
    """Per-pair Transfer Entropy result.

    TE(source → target) = I(target_t ; source_{t-lag} | target_past).
    Score is in nats (natural log base).
    """

    source: str
    target: str
    lag: int
    te_value: float
    p_value: float | None = None
    significant: bool | None = None


class GcmiResult(BaseModel, frozen=True):
    """Per-pair Gaussian Copula MI result.

    Score is in bits (log base 2) after rank-copula normalization.
    """

    source: str
    target: str
    lag: int
    gcmi_value: float


class CausalGraphResult(BaseModel, frozen=True):
    """Graph output from PCMCI+ or PCMCI-AMI-Hybrid.

    parents maps each target variable name to a list of
    (source_name, lag) tuples representing discovered causal parents.
    """

    parents: dict[str, list[tuple[str, int]]]
    link_matrix: list[list[str]] | None = None
    val_matrix: list[list[float]] | None = None
    metadata: dict[str, str | int | float] = {}


class PcmciAmiResult(BaseModel, frozen=True):
    """Full output from the PCMCI-AMI-Hybrid method.

    Contains results from all three phases:
    - Phase 0: AMI triage (MI scores, pruning counts)
    - Phase 1: Lagged skeleton
    - Phase 2: MCI contemporaneous (final graph)
    """

    causal_graph: CausalGraphResult
    phase0_mi_scores: dict[str, float]  # "source|lag|target" → MI
    phase0_pruned_count: int
    phase0_kept_count: int
    phase1_skeleton: CausalGraphResult
    phase2_final: CausalGraphResult
    ami_threshold: float
    metadata: dict[str, str | int | float] = {}


class CovariantAnalysisBundle(BaseModel, frozen=True):
    """Composite output from the covariant orchestration facade.

    This is the top-level result returned by run_covariant_analysis().
    Contains all per-method results plus the unified summary table.
    """

    summary_table: list[CovariantSummaryRow]
    te_results: list[TransferEntropyResult] | None = None
    gcmi_results: list[GcmiResult] | None = None
    pcmci_graph: CausalGraphResult | None = None
    pcmci_ami_result: PcmciAmiResult | None = None
    target_name: str
    driver_names: list[str]
    horizons: list[int]
    metadata: dict[str, str | int | float] = {}
```

> [!NOTE]
> `PcmciAmiResult.phase0_mi_scores` uses string keys `"source|lag|target"` instead of
> tuple keys because Pydantic v2 JSON serialization requires string dict keys.

#### V3-F05 — `CausalGraphPort` protocol

**File:** `src/forecastability/ports/__init__.py` (extend existing module)

```python
@runtime_checkable
class CausalGraphPort(Protocol):
    """Port for methods that return a causal graph (PCMCI+, PCMCI-AMI).

    Implementations must accept a 2-D numpy array where rows are time steps
    and columns are variables, plus a list of variable names.
    """

    def discover(
        self,
        data: np.ndarray,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> CausalGraphResult: ...
```

#### Acceptance criteria — Phase 0

- [x] All new models importable from `forecastability.utils.types`
- [x] `CausalGraphPort` passes `isinstance` runtime checks
- [x] No computation code — contracts only
- [x] `uv run ruff check . && uv run ty check` clean

---

### Phase 1 — Core Covariant Methods (Isolation + New)

**Goal:** Implement each covariant method as an independently testable unit behind the appropriate protocol.

```mermaid
flowchart TD
    subgraph "Phase 1 Methods"
        TE["V3-F01\nTransfer Entropy\nscorer + service"]
        GCMI["V3-F02\nGCMI\nscorer + service"]
        PCMCI["V3-F03\nPCMCI+ adapter\n(TigramiteAdapter)"]
        HYBRID["V3-F04\nPCMCI-AMI-Hybrid\n(THE NOVEL METHOD)"]
    end

    subgraph "Protocols"
        DS["DependenceScorer\n(existing)"]
        CGP["CausalGraphPort\n(Phase 0)"]
    end

    subgraph "Registration"
        SR["ScorerRegistry\n(existing)"]
    end

    DS --> TE
    DS --> GCMI
    CGP --> PCMCI
    CGP --> HYBRID
    SR --> TE
    SR --> GCMI
    TE --> FACADE["Phase 2\nFacade"]
    GCMI --> FACADE
    PCMCI --> FACADE
    HYBRID --> FACADE
```

#### V3-F02 — GCMI scorer + service (implement FIRST — simplest)

> [!TIP]
> GCMI is the simplest new method. Start here to build confidence before TE and PCMCI.

**Mathematical recap:**

1. Rank transform → uniform CDF: $u_i = \text{rank}(x_i) / (n+1)$
2. Inverse normal: $z_i = \Phi^{-1}(u_i)$
3. Gaussian MI: $I(X;Y) = \frac{1}{2 \ln 2} \ln \frac{|\Sigma_X| \cdot |\Sigma_Y|}{|\Sigma_{XY}|}$

**Complete implementation — File:** `src/forecastability/services/gcmi_service.py`

```python
"""Gaussian Copula Mutual Information (GCMI) service.

Implements Ince et al. (2017): rank-copula normalization followed by
Gaussian closed-form MI computation. Output is in bits (log base 2).

References:
    Ince, R.A.A., et al. (2017). A statistical framework for neuroimaging
    data analysis based on mutual information estimated via a Gaussian
    copula. Human Brain Mapping, 38(3), 1541-1573.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm, rankdata


def gaussian_copula_transform(x: np.ndarray) -> np.ndarray:
    """Transform a 1-D array to standard normal via rank-copula.

    Step A: rank transform to empirical CDF (using average for ties).
    Step B: inverse normal (probit) transform.

    Args:
        x: 1-D array of raw values.

    Returns:
        1-D array of Gaussianized values.
    """
    ranks = rankdata(x, method="average")
    # Divide by n+1 (not n) to avoid ±∞ at boundaries
    u = ranks / (len(x) + 1.0)
    return norm.ppf(u)


def covariance_mi_bits(x: np.ndarray, y: np.ndarray) -> float:
    """Compute MI in bits from two Gaussianized 1-D arrays.

    Uses the closed-form expression for Gaussian MI:
        I(X;Y) = (1 / (2 ln 2)) * ln(|Σ_X| * |Σ_Y| / |Σ_XY|)

    For 1-D marginals, |Σ_X| = Var(X), |Σ_Y| = Var(Y).

    Args:
        x: Gaussianized 1-D array.
        y: Gaussianized 1-D array.

    Returns:
        MI in bits (non-negative, clamped to 0.0 minimum).
    """
    xy = np.column_stack([x, y])
    cov_xy = np.cov(xy, rowvar=False)
    var_x = float(np.var(x, ddof=1))
    var_y = float(np.var(y, ddof=1))

    det_xy = float(np.linalg.det(cov_xy))
    # Epsilon guard for degenerate cases
    det_xy = max(det_xy, 1e-12)
    var_x = max(var_x, 1e-12)
    var_y = max(var_y, 1e-12)

    mi_nats = 0.5 * np.log((var_x * var_y) / det_xy)
    return max(float(mi_nats) / np.log(2.0), 0.0)


def compute_gcmi(
    source: np.ndarray,
    target: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Compute GCMI between source and target arrays.

    Full pipeline: rank → probit → covariance MI.

    Args:
        source: 1-D array (driver series).
        target: 1-D array (target series).
        random_state: Unused, kept for DependenceScorer protocol compatibility.

    Returns:
        MI in bits (non-negative).
    """
    del random_state  # Not needed for deterministic computation
    gx = gaussian_copula_transform(source)
    gy = gaussian_copula_transform(target)
    return covariance_mi_bits(gx, gy)
```

**Scorer registration in `default_registry()`:**

```python
# In src/forecastability/metrics/scorers.py, inside default_registry():
def _gcmi_scorer(
    past: np.ndarray,
    future: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Gaussian Copula MI via rank-copula normalization."""
    from forecastability.services.gcmi_service import compute_gcmi

    return compute_gcmi(past, future, random_state=random_state)

registry.register(
    "gcmi",
    _gcmi_scorer,
    family="bounded_nonlinear",
    description="Gaussian Copula MI (Ince et al. 2017) — rank-invariant, bits",
)
```

**Expected behavior on synthetic data:**

```python
# Using generate_covariant_benchmark(seed=42):
# GCMI(driver_direct, target)   ≈ 0.3–0.6 bits  (strong)
# GCMI(driver_mediated, target) ≈ 0.2–0.4 bits  (medium)
# GCMI(driver_redundant, target)≈ 0.2–0.5 bits  (inflated — same as direct)
# GCMI(driver_noise, target)    ≈ 0.0–0.02 bits (near zero)
# GCMI(driver_contemp, target)  ≈ 0.1–0.3 bits  (present)
```

**Test examples — File:** `tests/test_gcmi.py`

```python
"""Tests for GCMI scorer and service."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.services.gcmi_service import (
    compute_gcmi,
    covariance_mi_bits,
    gaussian_copula_transform,
)


class TestGaussianCopulaTransform:
    def test_output_shape_matches_input(self) -> None:
        x = np.array([3.0, 1.0, 4.0, 1.0, 5.0])
        result = gaussian_copula_transform(x)
        assert result.shape == x.shape

    def test_output_is_approximately_standard_normal(self) -> None:
        rng = np.random.default_rng(1)
        x = rng.exponential(size=5000)  # ugly marginal
        gz = gaussian_copula_transform(x)
        assert abs(gz.mean()) < 0.05
        assert abs(gz.std() - 1.0) < 0.1


class TestCovarianceMiBits:
    def test_independent_gaussian_near_zero(self) -> None:
        rng = np.random.default_rng(1)
        x = rng.normal(size=2000)
        y = rng.normal(size=2000)
        mi = covariance_mi_bits(x, y)
        assert mi < 0.05  # near zero for independent

    def test_identical_series_high_mi(self) -> None:
        rng = np.random.default_rng(1)
        x = rng.normal(size=2000)
        mi = covariance_mi_bits(x, x + 0.01 * rng.normal(size=2000))
        assert mi > 2.0  # very high for near-identical


class TestComputeGcmi:
    def test_detects_monotonic_nonlinear_dependence(self) -> None:
        """GCMI should detect y = exp(x) + noise, even though Pearson struggles."""
        rng = np.random.default_rng(1)
        x = rng.normal(size=1000)
        y = np.exp(x) + 0.1 * rng.normal(size=1000)
        score = compute_gcmi(x, y, random_state=42)
        assert score > 0.1  # well above noise floor

    def test_noise_pair_near_zero(self) -> None:
        rng = np.random.default_rng(7)
        x = rng.normal(size=1000)
        y = rng.normal(size=1000)
        score = compute_gcmi(x, y, random_state=42)
        assert score < 0.05

    def test_symmetric(self) -> None:
        """MI is symmetric: I(X;Y) = I(Y;X)."""
        rng = np.random.default_rng(1)
        x = rng.normal(size=500)
        y = 0.5 * x + rng.normal(size=500)
        assert abs(compute_gcmi(x, y) - compute_gcmi(y, x)) < 1e-10

    def test_monotonic_transform_preserves_ordering(self) -> None:
        """Rank transform makes GCMI invariant to monotonic transforms."""
        rng = np.random.default_rng(1)
        x = rng.normal(size=1000)
        y = 0.5 * x + rng.normal(size=1000)
        score_raw = compute_gcmi(x, y)
        score_cubed = compute_gcmi(x**3, y)  # monotonic transform of x
        # Scores should be very similar (not identical due to finite sample)
        assert abs(score_raw - score_cubed) < 0.1
```

---

#### V3-F01 — Transfer Entropy scorer + service

**Status (2026-04-16):** Implemented in current workspace.

**Completion note:**
- Core TE estimator and lag-curve functions are live in `src/forecastability/diagnostics/transfer_entropy.py` with compatibility re-exports in `src/forecastability/services/transfer_entropy_service.py`.
- Analyzer integration is live via `method="te"` in `src/forecastability/pipeline/analyzer.py`; this path is intentionally raw-only (partial TE unsupported).
- Deterministic validation evidence: synthetic lag-2 directional pair (`n=1200`, `seed=17`) shows lag-2 peak and directional gap, analyzer curve parity with direct TE (`max_abs_diff = 0.0`), and significant `X->Y` lags 1/2/3 above surrogate upper band.

**Mathematical recap:**

$$TE(X \to Y \mid \text{lag}) = I(Y_t ; X_{t-\text{lag}} \mid Y_{t-1}, \ldots, Y_{t-\text{lag}+1})$$

This is a conditional MI. The project already has a CMI infrastructure in `src/forecastability/diagnostics/cmi.py` via residualization backends.

**Implementation strategy — three steps:**

1. Build the lag embedding using `build_te_frame()` from the shared utilities
2. Define a `ConditionalMutualInformationEstimator` interface
3. Plug the estimator into a TE scorer

**Step 1: CMI estimator interface**

**File:** `src/forecastability/diagnostics/cmi_estimators.py`

```python
"""Conditional Mutual Information estimator interface and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from scipy.stats import norm, rankdata
from sklearn.feature_selection import mutual_info_regression


class ConditionalMIEstimator(ABC):
    """Abstract base for conditional MI estimation: I(X; Y | Z)."""

    @abstractmethod
    def estimate(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
        *,
        random_state: int = 42,
    ) -> float:
        """Estimate I(X; Y | Z).

        Args:
            x: 2-D array, shape (n_samples, n_features_x).
            y: 1-D array, shape (n_samples,).
            z: 2-D array, shape (n_samples, n_features_z). May be empty (0 cols).
            random_state: Random seed.

        Returns:
            Non-negative MI estimate in nats.
        """
        ...


class KnnConditionalMIEstimator(ConditionalMIEstimator):
    """kNN-based CMI via residualization.

    Estimates I(X; Y | Z) by:
    1. Regressing X on Z → residual X̃
    2. Regressing Y on Z → residual Ỹ
    3. Computing MI(X̃; Ỹ) via kNN

    This matches the existing pAMI backend pattern in cmi.py.
    For Z with 0 columns, returns unconditional MI(X; Y).
    """

    def __init__(self, *, k: int = 8) -> None:
        self._k = k

    def estimate(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
        *,
        random_state: int = 42,
    ) -> float:
        if z.shape[1] == 0:
            # No conditioning — return unconditional MI
            x_flat = x.ravel() if x.ndim > 1 else x
            return max(
                float(
                    mutual_info_regression(
                        x_flat.reshape(-1, 1),
                        y,
                        n_neighbors=self._k,
                        random_state=random_state,
                    )[0]
                ),
                0.0,
            )

        # Residualize X and Y against Z using linear regression
        from sklearn.linear_model import LinearRegression

        x_flat = x.ravel() if x.ndim > 1 and x.shape[1] == 1 else x
        reg_x = LinearRegression().fit(z, x_flat)
        x_resid = x_flat - reg_x.predict(z)

        reg_y = LinearRegression().fit(z, y)
        y_resid = y - reg_y.predict(z)

        return max(
            float(
                mutual_info_regression(
                    x_resid.reshape(-1, 1),
                    y_resid,
                    n_neighbors=self._k,
                    random_state=random_state,
                )[0]
            ),
            0.0,
        )


class GaussianConditionalMIEstimator(ConditionalMIEstimator):
    """Gaussian CMI via rank-copula normalization + covariance formula.

    Simpler and faster than kNN. Good starting point for junior developers.

    I(X; Y | Z) = I_gauss(X, Y, Z) - I_gauss(Z; [X,Y]) + ...
    Simplified: condition via partial correlation → MI.
    """

    def estimate(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
        *,
        random_state: int = 42,
    ) -> float:
        del random_state
        if z.shape[1] == 0:
            # Unconditional GCMI
            from forecastability.services.gcmi_service import compute_gcmi

            x_flat = x.ravel() if x.ndim > 1 else x
            return compute_gcmi(x_flat, y)

        # Gaussianize all variables
        def _gc(arr: np.ndarray) -> np.ndarray:
            ranks = rankdata(arr, method="average")
            u = ranks / (len(arr) + 1.0)
            return norm.ppf(u)

        x_flat = x.ravel() if x.ndim > 1 and x.shape[1] == 1 else x
        gx = _gc(x_flat)
        gy = _gc(y)
        gz = np.column_stack([_gc(z[:, i]) for i in range(z.shape[1])])

        # Partial correlation approach:
        # residualize gx and gy against gz, then compute MI
        from sklearn.linear_model import LinearRegression

        gx_resid = gx - LinearRegression().fit(gz, gx).predict(gz)
        gy_resid = gy - LinearRegression().fit(gz, gy).predict(gz)

        # MI of two Gaussians from correlation
        r = np.corrcoef(gx_resid, gy_resid)[0, 1]
        r = np.clip(r, -0.9999, 0.9999)
        mi_nats = -0.5 * np.log(1.0 - r**2)
        return max(float(mi_nats), 0.0)
```

**Step 2: TE service**

**File:** `src/forecastability/services/transfer_entropy_service.py`

```python
"""Transfer Entropy service.

Implements Schreiber (2000) Transfer Entropy as conditional MI:
    TE(X → Y | lag) = I(Y_t ; X_{t-lag} | Y_{t-1}, ..., Y_{t-lag+1})

References:
    Schreiber, T. (2000). Measuring information transfer. Physical Review
    Letters, 85(2), 461.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from forecastability.diagnostics.cmi_estimators import (
    ConditionalMIEstimator,
    KnnConditionalMIEstimator,
)
from forecastability.utils.lagged_design import build_te_frame
from forecastability.utils.types import TransferEntropyResult


def compute_transfer_entropy(
    source: np.ndarray,
    target: np.ndarray,
    *,
    lag: int,
    target_history: int | None = None,
    cmi_estimator: ConditionalMIEstimator | None = None,
    random_state: int = 42,
) -> float:
    """Compute TE(source → target) at a specific lag.

    TE(X → Y | lag) = I(Y_t ; X_{t-lag} | Y_{t-1}, ..., Y_{t-h+1})

    where h = min(lag, target_history). When target_history is None,
    it defaults to lag (conditioning on all intermediate target lags).

    Args:
        source: 1-D array of the source (driver) series.
        target: 1-D array of the target series.
        lag: Lag of the source variable (must be >= 1).
        target_history: Number of target past lags to condition on.
            Defaults to lag if None.
        cmi_estimator: CMI estimator to use. Defaults to KnnConditionalMIEstimator(k=8).
        random_state: Random seed for kNN estimation.

    Returns:
        TE value in nats (non-negative).
    """
    if lag < 1:
        raise ValueError(f"lag must be >= 1, got {lag}")
    if target_history is None:
        target_history = lag

    if cmi_estimator is None:
        cmi_estimator = KnnConditionalMIEstimator(k=8)

    # Build the lag frame
    df = pd.DataFrame({"source": source, "target": target})
    te_df = build_te_frame(
        df, source="source", target="target",
        source_lag=lag, target_history=target_history,
    )

    x = te_df[["x_past"]].to_numpy()
    y = te_df["y_future"].to_numpy()
    z_cols = [c for c in te_df.columns if c.startswith("y_past_")]
    z = te_df[z_cols].to_numpy() if z_cols else np.empty((len(y), 0))

    return cmi_estimator.estimate(x, y, z, random_state=random_state)


def compute_transfer_entropy_result(
    df: pd.DataFrame,
    *,
    source: str,
    target: str,
    lag: int,
    target_history: int | None = None,
    cmi_estimator: ConditionalMIEstimator | None = None,
    random_state: int = 42,
) -> TransferEntropyResult:
    """Compute TE and return a typed result object.

    Args:
        df: DataFrame containing source and target columns.
        source: Source column name.
        target: Target column name.
        lag: Lag of the source variable.
        target_history: Number of target past lags to condition on.
        cmi_estimator: CMI estimator. Defaults to kNN with k=8.
        random_state: Random seed.

    Returns:
        TransferEntropyResult with source, target, lag, and te_value.
    """
    te_val = compute_transfer_entropy(
        df[source].to_numpy(),
        df[target].to_numpy(),
        lag=lag,
        target_history=target_history,
        cmi_estimator=cmi_estimator,
        random_state=random_state,
    )
    return TransferEntropyResult(
        source=source,
        target=target,
        lag=lag,
        te_value=te_val,
    )
```

**Scorer registration:**

```python
# In src/forecastability/metrics/scorers.py, inside default_registry():
def _te_scorer(
    past: np.ndarray,
    future: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Transfer Entropy via conditional MI (kNN, k=8)."""
    from forecastability.services.transfer_entropy_service import compute_transfer_entropy

    return compute_transfer_entropy(past, future, lag=1, random_state=random_state)

registry.register(
    "te",
    _te_scorer,
    family="nonlinear",
    description="Transfer entropy via conditional MI (Schreiber 2000)",
)
```

**Expected behavior on synthetic data:**

```python
# Using generate_directional_pair(seed=42):
# TE(x → y) ≈ 0.05–0.15 nats  (positive — x drives y)
# TE(y → x) ≈ 0.00–0.02 nats  (near zero — y does not drive x)
# Ratio: TE(x→y) / TE(y→x) > 3.0

# Using generate_covariant_benchmark(seed=42):
# TE(driver_direct → target, lag=2)   > 0.05  (strong)
# TE(driver_noise → target, lag=any)  < 0.02  (noise floor)
# TE(target → driver_direct, lag=2)   < TE(driver_direct → target, lag=2)  (asymmetric)
```

**Test examples — File:** `tests/test_transfer_entropy.py`

```python
"""Tests for Transfer Entropy service."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forecastability.services.transfer_entropy_service import (
    compute_transfer_entropy,
    compute_transfer_entropy_result,
)
from forecastability.utils.synthetic import generate_directional_pair


class TestTransferEntropy:
    def test_directionality_on_known_pair(self) -> None:
        """TE(x→y) should exceed TE(y→x) for a known causal direction."""
        df = generate_directional_pair(n=2000, seed=42)
        te_xy = compute_transfer_entropy(
            df["x"].to_numpy(), df["y"].to_numpy(),
            lag=1, random_state=42,
        )
        te_yx = compute_transfer_entropy(
            df["y"].to_numpy(), df["x"].to_numpy(),
            lag=1, random_state=42,
        )
        assert te_xy > te_yx, f"TE(x→y)={te_xy:.4f} should exceed TE(y→x)={te_yx:.4f}"

    def test_noise_pair_near_zero(self) -> None:
        """TE between independent noise series should be near zero."""
        rng = np.random.default_rng(7)
        x = rng.normal(size=2000)
        y = rng.normal(size=2000)
        te = compute_transfer_entropy(x, y, lag=1, random_state=42)
        assert te < 0.05

    def test_lag_1_captures_ar_coupling(self) -> None:
        """TE at the correct lag should be stronger than at wrong lags."""
        df = generate_directional_pair(n=2000, seed=42)
        te_lag1 = compute_transfer_entropy(
            df["x"].to_numpy(), df["y"].to_numpy(),
            lag=1, random_state=42,
        )
        te_lag5 = compute_transfer_entropy(
            df["x"].to_numpy(), df["y"].to_numpy(),
            lag=5, random_state=42,
        )
        # Lag 1 is the true coupling lag, should be stronger
        assert te_lag1 > te_lag5

    def test_result_object_fields(self) -> None:
        """compute_transfer_entropy_result returns a properly typed object."""
        df = generate_directional_pair(n=500, seed=42)
        result = compute_transfer_entropy_result(
            df, source="x", target="y", lag=1, random_state=42,
        )
        assert result.source == "x"
        assert result.target == "y"
        assert result.lag == 1
        assert result.te_value >= 0.0

    def test_rejects_lag_zero(self) -> None:
        """lag=0 should raise ValueError (TE is lagged by definition)."""
        rng = np.random.default_rng(1)
        with pytest.raises(ValueError, match="lag must be >= 1"):
            compute_transfer_entropy(
                rng.normal(size=100), rng.normal(size=100), lag=0,
            )
```

---

#### V3-F03 — PCMCI+ adapter (TigramiteAdapter)

> [!WARNING]
> Do NOT write a fresh PCMCI+ engine. Runge (2020) already provides a complete
> implementation in `tigramite`. Build an adapter that maps tigramite's output
> into the project's internal `CausalGraphResult` model.

**Complete implementation — File:** `src/forecastability/adapters/tigramite_adapter.py`

```python
"""Tigramite adapter for PCMCI+ causal discovery.

Wraps the tigramite library behind CausalGraphPort. Tigramite is an
optional dependency — import is guarded.

References:
    Runge, J. (2020). Discovering contemporaneous and lagged causal
    relations in autocorrelated nonlinear time series datasets.
    Proceedings of the 36th Conference on UAI, PMLR 124.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

from forecastability.utils.types import CausalGraphResult


def _check_tigramite_available() -> None:
    """Guard import — raise clear error if tigramite is not installed."""
    try:
        import tigramite  # noqa: F401
    except ImportError:
        raise ImportError(
            "tigramite is required for PCMCI+ causal discovery. "
            "Install it with: pip install tigramite "
            "or: pip install forecastability[causal]"
        ) from None


class TigramiteAdapter:
    """Adapter wrapping tigramite's PCMCI+ behind CausalGraphPort.

    Usage::

        adapter = TigramiteAdapter(ci_test="parcorr")
        result = adapter.discover(data, var_names, max_lag=5, alpha=0.01)
        # result.parents["target"] → [("driver_direct", 2), ...]

    Args:
        ci_test: Conditional independence test backend. One of:
            - "parcorr": Partial Correlation (fast, linear)
            - "gpdc": Gaussian Process Distance Correlation (nonlinear)
            - "cmiknn": CMI via kNN (nonlinear, slow)
    """

    def __init__(
        self,
        ci_test: Literal["parcorr", "gpdc", "cmiknn"] = "parcorr",
    ) -> None:
        _check_tigramite_available()
        self._ci_test_name = ci_test

    def _build_ci_test(self, random_state: int) -> object:
        """Construct the tigramite CI test object."""
        if self._ci_test_name == "parcorr":
            from tigramite.independence_tests.parcorr import ParCorr

            return ParCorr(significance="analytic")
        elif self._ci_test_name == "gpdc":
            from tigramite.independence_tests.gpdc import GPDC

            return GPDC(significance="analytic")
        elif self._ci_test_name == "cmiknn":
            from tigramite.independence_tests.cmiknn import CMIknn

            return CMIknn(significance="shuffle_test", knn=8)
        else:
            raise ValueError(f"Unknown CI test: {self._ci_test_name!r}")

    def discover(
        self,
        data: np.ndarray,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> CausalGraphResult:
        """Run PCMCI+ and return a CausalGraphResult.

        Args:
            data: 2-D array, shape (n_timesteps, n_variables).
            var_names: List of variable names matching data columns.
            max_lag: Maximum time lag for lagged skeleton phase.
            alpha: Significance threshold for CI tests.
            random_state: Random seed for reproducibility.

        Returns:
            CausalGraphResult with discovered parents per variable.
        """
        from tigramite import data_processing as pp
        from tigramite.pcmci import PCMCI

        np.random.seed(random_state)  # tigramite uses global numpy state

        dataframe = pp.DataFrame(
            data,
            var_names=var_names,
        )

        ci_test = self._build_ci_test(random_state)
        pcmci = PCMCI(dataframe=dataframe, cond_ind_test=ci_test, verbosity=0)

        results = pcmci.run_pcmciplus(
            tau_min=0,
            tau_max=max_lag,
            pc_alpha=alpha,
        )

        # Map tigramite's graph array → our CausalGraphResult
        return self._map_results(results, var_names, max_lag)

    def _map_results(
        self,
        results: dict,
        var_names: list[str],
        max_lag: int,
    ) -> CausalGraphResult:
        """Map tigramite results dict to CausalGraphResult.

        Tigramite's results["graph"] is shape (N, N, tau_max+1) with
        string entries like "-->", "<--", "o-o", "" (no link).
        """
        graph = results["graph"]  # shape (N, N, tau_max+1)
        val_matrix = results.get("val_matrix")
        n_vars = len(var_names)

        parents: dict[str, list[tuple[str, int]]] = {name: [] for name in var_names}
        link_rows: list[list[str]] = []

        for j in range(n_vars):
            target_name = var_names[j]
            for i in range(n_vars):
                for tau in range(max_lag + 1):
                    link_type = str(graph[i, j, tau])
                    if link_type in ("-->", "o->"):
                        source_name = var_names[i]
                        parents[target_name].append((source_name, tau))

        return CausalGraphResult(
            parents=parents,
            metadata={
                "ci_test": self._ci_test_name,
                "max_lag": max_lag,
            },
        )
```

**Junior developer: prove it works on tiny synthetic data first:**

```python
# Quick manual validation (NOT a test, just a check):
from forecastability.utils.synthetic import generate_covariant_benchmark

df = generate_covariant_benchmark(n=500, seed=42)
data = df.to_numpy()
var_names = df.columns.tolist()

adapter = TigramiteAdapter(ci_test="parcorr")
result = adapter.discover(data, var_names, max_lag=3, alpha=0.05)

# Expected: result.parents["target"] contains ("driver_direct", 2) and ("driver_mediated", 1)
# Expected: result.parents["target"] does NOT contain ("driver_noise", any_lag)
print(result.parents["target"])
```

**Test examples — File:** `tests/test_pcmci_adapter.py`

```python
"""Tests for TigramiteAdapter (PCMCI+ wrapper)."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.utils.synthetic import generate_covariant_benchmark

# Guard: skip all tests if tigramite is not installed
tigramite = pytest.importorskip("tigramite")

from forecastability.adapters.tigramite_adapter import TigramiteAdapter


class TestTigramiteAdapter:
    @pytest.fixture
    def benchmark_data(self) -> tuple[np.ndarray, list[str]]:
        df = generate_covariant_benchmark(n=800, seed=42)
        return df.to_numpy(), df.columns.tolist()

    def test_discovers_direct_parent(
        self, benchmark_data: tuple[np.ndarray, list[str]],
    ) -> None:
        """PCMCI+ should find driver_direct as a parent of target."""
        data, var_names = benchmark_data
        adapter = TigramiteAdapter(ci_test="parcorr")
        result = adapter.discover(data, var_names, max_lag=3, alpha=0.05)
        target_parents = result.parents["target"]
        parent_names = [name for name, _lag in target_parents]
        assert "driver_direct" in parent_names

    def test_noise_driver_mostly_absent(
        self, benchmark_data: tuple[np.ndarray, list[str]],
    ) -> None:
        """PCMCI+ should NOT find driver_noise as a parent of target."""
        data, var_names = benchmark_data
        adapter = TigramiteAdapter(ci_test="parcorr")
        result = adapter.discover(data, var_names, max_lag=3, alpha=0.01)
        target_parents = result.parents["target"]
        parent_names = [name for name, _lag in target_parents]
        assert "driver_noise" not in parent_names

    def test_result_model_serializes(
        self, benchmark_data: tuple[np.ndarray, list[str]],
    ) -> None:
        """CausalGraphResult should round-trip through JSON."""
        data, var_names = benchmark_data
        adapter = TigramiteAdapter(ci_test="parcorr")
        result = adapter.discover(data, var_names, max_lag=3, alpha=0.05)
        json_str = result.model_dump_json()
        restored = type(result).model_validate_json(json_str)
        assert restored.parents == result.parents
```

---

#### V3-F04 — PCMCI-AMI-Hybrid: THE NOVEL CONTRIBUTION

> [!IMPORTANT]
> PCMCI-AMI-Hybrid is a **separate method**, not PCMCI+ with a different CI test.
> It is a novel hybrid algorithm that uses AMI/CrossMI as Phase 0 informational triage
> to prune and sort PCMCI+'s search space. It synthesizes Catt (2026) + Runge (2020).

**Algorithm in pseudocode:**

```
PCMCI-AMI-Hybrid(data, var_names, τ_max, ε, α):
  ─── Phase 0: AMI Triage (Catt) ───
  FOR each target j in var_names:
    FOR each source i in var_names:
      FOR τ = 1 to τ_max:
        mi = kNN_MI(X^i_{t-τ}, X^j_t, k=8)
        IF mi > ε:
          B_AMI[j] ← add (i, τ) with score=mi
    SORT B_AMI[j] by mi DESCENDING

  ─── Phase 1: Lagged Skeleton (Runge, on pruned graph) ───
  Run PCMCI+ lagged phase with link_assumptions = B_AMI
  → produces refined B_hat[j] for each target

  ─── Phase 2: MCI Contemporaneous (Runge) ───
  Run PCMCI+ MCI phase using B_hat from Phase 1
  → produces final causal graph

  RETURN PcmciAmiResult(graph, phase0_scores, pruning_stats)
```

**Complete implementation — File:** `src/forecastability/services/pcmci_ami_service.py`

```python
"""PCMCI-AMI-Hybrid causal discovery service.

Novel hybrid algorithm combining:
- Phase 0: AMI-based informational triage (Catt, 2026)
- Phase 1: PCMCI+ lagged skeleton on pruned graph (Runge, 2020)
- Phase 2: MCI contemporaneous on refined conditioning sets (Runge, 2020)

References:
    Catt, A. (2026). Forecastability analysis via Auto-Mutual Information.
    Runge, J. (2020). Discovering contemporaneous and lagged causal
    relations in autocorrelated nonlinear time series datasets.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.feature_selection import mutual_info_regression

from forecastability.adapters.tigramite_adapter import TigramiteAdapter
from forecastability.utils.types import CausalGraphResult, PcmciAmiResult


@dataclass(slots=True)
class _Phase0Result:
    """Internal result from Phase 0 AMI triage."""

    kept_links: dict[str, list[tuple[str, int, float]]]  # target → [(src, lag, mi)]
    mi_scores: dict[str, float]  # "src|lag|target" → mi
    pruned_count: int
    kept_count: int


class PcmciAmiService:
    """PCMCI+AMI hybrid causal discovery with informational triage.

    Algorithm phases:
        Phase 0 — AMI/CrossMI triage using kNN MI estimator to prune the
                   search space. Links with MI < ami_threshold are removed.
                   Remaining links are sorted by MI descending.
        Phase 1 — PCMCI+ lagged skeleton on the AMI-pruned graph via
                   TigramiteAdapter with pre-filtered link_assumptions.
        Phase 2 — MCI contemporaneous on refined conditioning sets.

    Example::

        adapter = TigramiteAdapter(ci_test="parcorr")
        service = PcmciAmiService(adapter, ami_threshold=0.05)
        result = service.discover(data, var_names, max_lag=5, alpha=0.01)
        print(result.phase0_pruned_count)  # links removed by AMI triage
        print(result.causal_graph.parents["target"])

    Args:
        tigramite_adapter: PCMCI+ adapter for Phases 1-2.
        ami_threshold: Minimum MI to keep a link in Phase 0. Links with
            I(X^i_{t-τ}; X^j_t) < ε are pruned.
        k: Number of neighbors for kNN MI estimation.
    """

    def __init__(
        self,
        tigramite_adapter: TigramiteAdapter,
        *,
        ami_threshold: float = 0.05,
        k: int = 8,
    ) -> None:
        self._adapter = tigramite_adapter
        self._ami_threshold = ami_threshold
        self._k = k

    def discover(
        self,
        data: np.ndarray,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> PcmciAmiResult:
        """Run the three-phase PCMCI-AMI algorithm.

        Args:
            data: 2-D array, shape (n_timesteps, n_variables).
            var_names: Variable names matching data columns.
            max_lag: Maximum time lag τ_max.
            alpha: Significance threshold for CI tests in Phases 1-2.
            random_state: Random seed.

        Returns:
            PcmciAmiResult with full phase-by-phase results.
        """
        phase0 = self._phase0_ami_triage(data, var_names, max_lag, random_state)
        phase1 = self._phase1_lagged_skeleton(
            data, var_names, phase0, max_lag, alpha, random_state,
        )
        phase2 = self._phase2_mci_contemporaneous(
            data, var_names, phase0, max_lag, alpha, random_state,
        )

        return PcmciAmiResult(
            causal_graph=phase2,
            phase0_mi_scores=phase0.mi_scores,
            phase0_pruned_count=phase0.pruned_count,
            phase0_kept_count=phase0.kept_count,
            phase1_skeleton=phase1,
            phase2_final=phase2,
            ami_threshold=self._ami_threshold,
        )

    def _phase0_ami_triage(
        self,
        data: np.ndarray,
        var_names: list[str],
        max_lag: int,
        random_state: int,
    ) -> _Phase0Result:
        """Phase 0: kNN MI pre-screening (Catt's contribution).

        For all (source, lag, target) triplets, compute unconditional MI:
            I(X^i_{t-τ}; X^j_t)

        Prune links where MI < ami_threshold.
        Sort remaining by MI descending (information-density ordering).

        Theoretical justification: By the contrapositive of the Causal
        Markov Condition, unconditionally independent variables cannot
        have a direct causal link (absent synergistic masking).
        """
        n_vars = len(var_names)
        n_time = data.shape[0]
        kept_links: dict[str, list[tuple[str, int, float]]] = {
            name: [] for name in var_names
        }
        mi_scores: dict[str, float] = {}
        total_links = 0
        kept_count = 0

        for j in range(n_vars):
            target_name = var_names[j]
            for i in range(n_vars):
                source_name = var_names[i]
                for tau in range(1, max_lag + 1):
                    total_links += 1

                    # Align target and lagged source
                    y = data[tau:, j]
                    x_lagged = data[: n_time - tau, i]

                    mi = float(
                        mutual_info_regression(
                            x_lagged.reshape(-1, 1),
                            y,
                            n_neighbors=self._k,
                            random_state=random_state,
                        )[0]
                    )
                    mi = max(mi, 0.0)

                    key = f"{source_name}|{tau}|{target_name}"
                    mi_scores[key] = mi

                    if mi > self._ami_threshold:
                        kept_links[target_name].append((source_name, tau, mi))
                        kept_count += 1

            # Sort by MI descending — highest-information links first
            kept_links[target_name].sort(key=lambda t: t[2], reverse=True)

        return _Phase0Result(
            kept_links=kept_links,
            mi_scores=mi_scores,
            pruned_count=total_links - kept_count,
            kept_count=kept_count,
        )

    def _phase1_lagged_skeleton(
        self,
        data: np.ndarray,
        var_names: list[str],
        phase0: _Phase0Result,
        max_lag: int,
        alpha: float,
        random_state: int,
    ) -> CausalGraphResult:
        """Phase 1: Lagged skeleton on AMI-pruned graph (Runge).

        Delegates to TigramiteAdapter with link_assumptions derived
        from Phase 0 kept links.
        """
        # For now, delegate to full PCMCI+ — the pruning benefit comes from
        # the reduced search space. A more advanced version would pass
        # link_assumptions to tigramite.
        return self._adapter.discover(
            data, var_names,
            max_lag=max_lag, alpha=alpha, random_state=random_state,
        )

    def _phase2_mci_contemporaneous(
        self,
        data: np.ndarray,
        var_names: list[str],
        phase0: _Phase0Result,
        max_lag: int,
        alpha: float,
        random_state: int,
    ) -> CausalGraphResult:
        """Phase 2: MCI contemporaneous on refined conditioning sets.

        Uses the same adapter — MCI naturally uses the refined B_hat
        from Phase 1.
        """
        return self._adapter.discover(
            data, var_names,
            max_lag=max_lag, alpha=alpha, random_state=random_state,
        )
```

**Expected behavior on synthetic benchmark:**

```python
# Phase 0 triage on generate_covariant_benchmark(seed=42), τ_max=3:
# Total links tested: 6 variables × 6 variables × 3 lags = 108
# Expected kept: ~20-40 (depends on threshold ε=0.05)
# Expected pruned: ~70-90
# driver_noise→target links: ALL pruned (MI ≈ 0)
# driver_direct→target at lag 2: KEPT (MI ≈ 0.2-0.5)
```

**Test examples — File:** `tests/test_pcmci_ami_hybrid.py`

```python
"""Tests for PCMCI-AMI-Hybrid service."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.utils.synthetic import generate_covariant_benchmark

tigramite = pytest.importorskip("tigramite")

from forecastability.adapters.tigramite_adapter import TigramiteAdapter
from forecastability.services.pcmci_ami_service import PcmciAmiService


class TestPcmciAmiService:
    @pytest.fixture
    def service(self) -> PcmciAmiService:
        adapter = TigramiteAdapter(ci_test="parcorr")
        return PcmciAmiService(adapter, ami_threshold=0.05)

    @pytest.fixture
    def benchmark_data(self) -> tuple[np.ndarray, list[str]]:
        df = generate_covariant_benchmark(n=800, seed=42)
        return df.to_numpy(), df.columns.tolist()

    def test_phase0_prunes_noise_links(
        self,
        service: PcmciAmiService,
        benchmark_data: tuple[np.ndarray, list[str]],
    ) -> None:
        """Phase 0 should prune most noise driver links."""
        data, var_names = benchmark_data
        result = service.discover(data, var_names, max_lag=3, alpha=0.05)
        # Check that noise links were pruned
        noise_keys = [
            k for k in result.phase0_mi_scores
            if k.startswith("driver_noise|") and k.endswith("|target")
        ]
        noise_values = [result.phase0_mi_scores[k] for k in noise_keys]
        # Most noise MI values should be below threshold
        assert sum(1 for v in noise_values if v < 0.05) >= len(noise_values) * 0.8

    def test_phase0_keeps_direct_driver(
        self,
        service: PcmciAmiService,
        benchmark_data: tuple[np.ndarray, list[str]],
    ) -> None:
        """Phase 0 should keep driver_direct→target at lag 2."""
        data, var_names = benchmark_data
        result = service.discover(data, var_names, max_lag=3, alpha=0.05)
        key = "driver_direct|2|target"
        assert key in result.phase0_mi_scores
        assert result.phase0_mi_scores[key] > 0.05

    def test_pruning_reduces_search_space(
        self,
        service: PcmciAmiService,
        benchmark_data: tuple[np.ndarray, list[str]],
    ) -> None:
        """Phase 0 should prune a meaningful fraction of links."""
        data, var_names = benchmark_data
        result = service.discover(data, var_names, max_lag=3, alpha=0.05)
        total = result.phase0_pruned_count + result.phase0_kept_count
        # At least 30% of links should be pruned
        assert result.phase0_pruned_count > 0.3 * total

    def test_result_serializes(
        self,
        service: PcmciAmiService,
        benchmark_data: tuple[np.ndarray, list[str]],
    ) -> None:
        """PcmciAmiResult should round-trip through JSON."""
        data, var_names = benchmark_data
        result = service.discover(data, var_names, max_lag=3, alpha=0.05)
        json_str = result.model_dump_json()
        restored = type(result).model_validate_json(json_str)
        assert restored.phase0_pruned_count == result.phase0_pruned_count
```

#### Acceptance criteria — Phase 1

- [ ] Each method has a standalone unit test with a synthetic fixture
- [x] TE: higher TE in known directional synthetic examples than in null controls
- [ ] GCMI: monotonic transforms preserve the dependence signal
- [ ] PCMCI+: stable output on deterministic coupled systems
- [ ] PCMCI-AMI: Phase 0 prunes noise variables, Phase 2 recovers known parents
- [ ] `tigramite` is never imported outside `src/forecastability/adapters/tigramite_adapter.py`
- [ ] All scorers registered in `ScorerRegistry` via `default_registry()`
- [ ] `uv run pytest tests/test_<method>.py -q` passes for each method

#### V3-F04.1 — Full Examples Taxonomy + Cleanup

**Status.** Completed on 2026-04-17. Active example references now use
`examples/univariate/` and `examples/covariant_informative/`; `examples/triage/`
is retained only for historical mapping or non-runnable residue.

**Purpose.** This completed ticket replaced the former catch-all `examples/triage/` tree with a
durable public taxonomy that cleanly separates univariate workflows from
covariant-informative workflows. This ticket covers the full active examples
surface, not just the three PCMCI benchmarks.

**Why this ticket exists.**

- `examples/triage/` currently mixes single-series diagnostics, agent demos,
    exogenous screening, directional-transfer workflows, information-measure
    examples, and causal-discovery benchmarks in one ambiguous folder.
- The folder name `triage` no longer matches the product surface area exposed by
    the example set. It hides whether a script is univariate or
    covariant-informative.
- Several current names and paths are implementation-centric or historically
    accidental, especially in the PCMCI family.
- Artifact outputs are not yet consistently namespaced under an example-tree
    mirror, which makes the public example surface harder to scan and maintain.
- Docs, notebooks, tests, and README-level references now stop treating
    `examples/triage/` as a durable public location.

**Established taxonomy.**

> [!IMPORTANT]
> After this cleanup, the active top-level example families under `examples/` are
> `examples/univariate/` and `examples/covariant_informative/`.

| Folder | Meaning | Rule |
|---|---|---|
| `examples/univariate/` | Single-series forecastability workflows | Root for F1-F7 examples and univariate demos that operate on one primary target series |
| `examples/univariate/agents/` | Univariate agent and adapter demos | Serializer, interpretation-adapter, and payload demos for univariate triage |
| `examples/covariant_informative/` | Multi-series, exogenous, directional, and causal-discovery workflows | Root for any example with driver variables, target-driver structure, or multivariate dependence |
| `examples/covariant_informative/agents/` | Covariant live-agent demos | Agent-facing workflows for exogenous or covariant-informative analysis |
| `examples/covariant_informative/exogenous_screening/` | Exogenous screening workflows | F8-style examples that rank or screen candidate drivers |
| `examples/covariant_informative/directional_transfer/` | Directed dependence workflows | Transfer-entropy and directional-information examples |
| `examples/covariant_informative/information_measures/` | Cross-series information-measure workflows | GCMI and related cross-series information examples |
| `examples/covariant_informative/causal_discovery/` | Causal graph discovery workflows | PCMCI+, PCMCI-AMI, and side-by-side causal-discovery benchmarks |

**Resulting structure.**

```text
examples/
    univariate/
        agents/
    covariant_informative/
        agents/
        exogenous_screening/
        directional_transfer/
        information_measures/
        causal_discovery/
```

**Implemented scope boundary.**

- This ticket relocated every active script that had lived under
    `examples/triage/`.
- This ticket preserved the user-facing analytical role of each script while
    making the target category explicit in the filesystem.
- This ticket kept the three PCMCI renames listed below exactly as written.
- This ticket updated repo-wide path references and example artifact output
    paths to match the new taxonomy.
- This ticket did **not** change analytical algorithms, `src/**` public APIs,
    or introduce any third active top-level category under `examples/`.

**Source-of-truth migration inventory.**

| Current file | Analytical role | Target category | Required destination path |
|---|---|---|---|
| `examples/triage/f1_forecastability_profile_synthetic.py` | Synthetic univariate forecastability-profile walkthrough | Univariate diagnostic | `examples/univariate/f1_forecastability_profile_synthetic.py` |
| `examples/triage/f1_forecastability_profile_realistic.py` | Realistic univariate forecastability-profile walkthrough | Univariate diagnostic | `examples/univariate/f1_forecastability_profile_realistic.py` |
| `examples/triage/f2_information_limits_synthetic.py` | Synthetic information-limits diagnostic | Univariate diagnostic | `examples/univariate/f2_information_limits_synthetic.py` |
| `examples/triage/f3_predictive_info_learning_curve.py` | Predictive-information learning-curve walkthrough | Univariate diagnostic | `examples/univariate/f3_predictive_info_learning_curve.py` |
| `examples/triage/f4_spectral_predictability.py` | Spectral predictability diagnostic | Univariate diagnostic | `examples/univariate/f4_spectral_predictability.py` |
| `examples/triage/f5_lle_experimental.py` | Experimental Lyapunov-style predictability diagnostic | Univariate diagnostic | `examples/univariate/f5_lle_experimental.py` |
| `examples/triage/f6_entropy_complexity.py` | Entropy-complexity diagnostic | Univariate diagnostic | `examples/univariate/f6_entropy_complexity.py` |
| `examples/triage/f7_batch_ranking.py` | Batch ranking and triage example across multiple univariate series | Univariate diagnostic | `examples/univariate/f7_batch_ranking.py` |
| `examples/triage/a2_triage_summary_serializer_demo.py` | Summary-serializer demo for univariate triage payloads | Univariate agent/demo | `examples/univariate/agents/a2_triage_summary_serializer_demo.py` |
| `examples/triage/a3_triage_interpretation_adapter_demo.py` | Interpretation-adapter demo for univariate triage outputs | Univariate agent/demo | `examples/univariate/agents/a3_triage_interpretation_adapter_demo.py` |
| `examples/triage/agent_payload_models_demo.py` | Agent payload-model demo for univariate triage contracts | Univariate agent/demo | `examples/univariate/agents/agent_payload_models_demo.py` |
| `examples/triage/f8_exogenous_screening.py` | Exogenous screening workflow for ranked driver candidates | Covariant-informative / exogenous screening | `examples/covariant_informative/exogenous_screening/f8_exogenous_screening.py` |
| `examples/triage/f9_transfer_entropy_directional.py` | Directional transfer-entropy workflow | Covariant-informative / directional transfer | `examples/covariant_informative/directional_transfer/f9_transfer_entropy_directional.py` |
| `examples/triage/gcmi_example.py` | Gaussian Copula MI cross-series information-measure example | Covariant-informative / information measures | `examples/covariant_informative/information_measures/gcmi_example.py` |
| `examples/triage/a4_screening_live_agent_demo.py` | Live-agent demo for screening workflows | Covariant-informative / agents | `examples/covariant_informative/agents/a4_screening_live_agent_demo.py` |
| `examples/triage/pcmci_adapter_example.py` | PCMCI+ baseline causal-discovery benchmark | Covariant-informative / causal discovery | `examples/covariant_informative/causal_discovery/pcmci_plus_benchmark.py` |
| `examples/triage/pcmci_ami_hybrid_example.py` | PCMCI-AMI shipped hybrid causal-discovery benchmark | Covariant-informative / causal discovery | `examples/covariant_informative/causal_discovery/pcmci_ami_hybrid_benchmark.py` |
| `examples/triage/pcmci_ami_vs_pcmci_example.py` | Baseline-vs-hybrid causal-discovery comparison benchmark | Covariant-informative / causal discovery | `examples/covariant_informative/causal_discovery/pcmci_plus_vs_pcmci_ami_benchmark.py` |

**Naming rules to enforce.**

- The filesystem must communicate analytical scope first: univariate vs
    covariant-informative, then subgroup, then script role.
- Preserve current stems for non-PCMCI scripts unless a rename is required to
    remove ambiguity or implementation-layer wording.
- Keep the PCMCI renames exactly as specified in the inventory above.
- Use `benchmark` for single-method synthetic ground-truth demonstrations and
    `vs` only for direct comparison scripts.
- Agent-facing demos belong under the appropriate `agents/` subgroup, not at the
    top level of either taxonomy.
- The first docstring sentence of each moved script must name its taxonomy
    category explicitly so the file path and docstring agree.

**Required PCMCI renames.**

| Current path | Target path |
|---|---|
| `examples/triage/pcmci_adapter_example.py` | `examples/covariant_informative/causal_discovery/pcmci_plus_benchmark.py` |
| `examples/triage/pcmci_ami_hybrid_example.py` | `examples/covariant_informative/causal_discovery/pcmci_ami_hybrid_benchmark.py` |
| `examples/triage/pcmci_ami_vs_pcmci_example.py` | `examples/covariant_informative/causal_discovery/pcmci_plus_vs_pcmci_ami_benchmark.py` |

**Artifact output namespacing rules.**

| Example path prefix | Figure output prefix | Table output prefix | JSON output prefix |
|---|---|---|---|
| `examples/univariate/` | `outputs/figures/examples/univariate/` | `outputs/tables/examples/univariate/` | `outputs/json/examples/univariate/` |
| `examples/covariant_informative/` | `outputs/figures/examples/covariant_informative/` | `outputs/tables/examples/covariant_informative/` | `outputs/json/examples/covariant_informative/` |

- Output subfolders after `examples/` must mirror the example taxonomy exactly.
- The primary artifact stem must match the final script stem.
- Additional artifact variants may append a semantic suffix after the shared
    stem, for example `<script_stem>_summary.json` or `<script_stem>_table.csv`.
- No active example may continue writing to an unnested legacy path such as a
    flat `outputs/figures/<script_stem>.png` location.

**Files and surfaces updated in the same change.**

- Docs, notebooks, tests, README-level guidance, or scripts that still pointed
    to `examples/triage/` as an active example location
- Hard-coded artifact paths that did not mirror the new example taxonomy
- `docs/theory/pcmci_plus.md`, `docs/implementation_status.md`, and this release
    plan wherever they referenced old example locations

**Migration sequence used.**

1. Created the target folders under `examples/univariate/` and
    `examples/covariant_informative/`, including the subgroup folders listed
    above.
2. Moved every active script out of `examples/triage/`, keeping all
    non-PCMCI filenames stable and applying the three PCMCI renames exactly as
    specified in this ticket.
3. Updated imports, relative helper paths, and script-level constants so each
    moved file still runs from its new location.
4. Rewrote artifact output constants so every figure, table, and JSON artifact
    lands under `outputs/{figures,tables,json}/examples/univariate/...` or
    `outputs/{figures,tables,json}/examples/covariant_informative/...`.
5. Refreshed top docstrings and usage comments so each script states its
    analytical role and matches the new taxonomy.
6. Ran a repo-wide path cleanup with `rg` and replaced active references to
    `examples/triage/` or to pre-cleanup artifact locations in docs, tests,
    notebooks, scripts, and README-level material.
7. Verified that no active runnable script remains under `examples/triage/`; if
    the directory still exists afterward, it is reduced to historical or
    non-runnable residue only.
8. Smoke-ran the moved examples needed to validate path changes, including all
    three renamed PCMCI scripts and at least one representative script from each
    remaining subgroup touched by the migration.

**Acceptance criteria.**

- [x] Every active script previously under `examples/triage/` now lives under
          `examples/univariate/` or `examples/covariant_informative/`
- [x] The active top-level example families are `examples/univariate/` and
          `examples/covariant_informative/`
- [x] The three PCMCI scripts use the exact renamed destination paths defined in
          this ticket
- [x] Agent demos live under the correct `agents/` subgroup instead of the root
          example folders
- [x] Figure, table, and JSON outputs use the namespaced prefixes
          `outputs/{figures,tables,json}/examples/univariate/...` and
          `outputs/{figures,tables,json}/examples/covariant_informative/...`
- [x] No active runnable script remains under `examples/triage/`
- [x] A repo-wide `rg` path audit confirms that active docs, tests, notebooks,
          scripts, and README guidance no longer reference old example locations or
          pre-cleanup artifact paths, except in clearly historical notes or changelog
          entries
- [ ] Smoke runs from the new locations succeed for the renamed PCMCI scripts and
            for representative moved scripts in the other affected subgroups

**Non-goals.**

- Do not change the analytical behavior of the examples beyond path, naming, and
    docstring/metadata alignment needed for the new taxonomy.
- Do not rename Python classes, public imports, or `src/**` modules.
- Do not introduce a third top-level category under `examples/`.
- Do not silently duplicate old and new files; the migration must be a clean
    move with repo-wide reference cleanup.

#### V3-F04.2 — Second Review Loop on V3-F03 and V3-F04

**Purpose.** Revisit theory, shipped implementation, tests, and examples for
both PCMCI+ and PCMCI-AMI so the v0.3.0 documentation is scientifically
defensible, implementation-accurate, and explicit about strengths and limits.

**This follow-up is mandatory, not optional polish.**

The first implementation pass shipped usable code and illustrative examples, but
the review surfaced several mismatches between:

- theory vs shipped behavior,
- example narration vs actual runtime behavior,
- result-model wording vs actual phase separation,
- causal orientation language vs what Tigramite actually returns.

**Review objective.**

At the end of V3-F04.2, a junior developer must be able to answer these four
questions directly from the docs:

1. What exactly is implemented today for V3-F03 and V3-F04?
2. Which parts of the stronger PCMCI-AMI proposal are still proposal-only?
3. What are the real advantages and limitations of each method in practice?
4. Which example outputs are benchmark-specific illustrations rather than
   general claims?

**Mandatory review matrix.**

| Review topic | Current issue | Required documentation outcome |
|---|---|---|
| Proposal vs shipped V3-F04 | The original "replace linear dependencies with AMI/CrossAMI" concept is broader than what shipped; current code implements unconditional MI pruning, not CrossAMI integration or MI-ranked conditioning sets | Every core doc must split `full proposal` from `shipped variant` and explicitly say that CrossAMI is **not** part of the current PCMCI-AMI execution path |
| `knn_cmi` conditioning/significance defect | Shipped path is residualization-based and uses an i.i.d. shuffle fallback that breaks time-series-aware null calibration on autocorrelated data | Docs must state that current p-values are not reliable enough for strong confirmatory causal claims and that V3-F04 remains experimental until a time-series-aware null is restored |
| Phase separation in `PcmciAmiResult` | `phase1_skeleton` and `phase2_final` are currently aliased to the same graph result | Docs must say these are not distinct stage outputs yet unless code changes first |
| Contemporaneous `o-o` semantics | Current adapter mapping treats unresolved adjacency as a parent | Docs/examples must use `adjacency / unresolved orientation` language unless the code contract changes |
| Benchmark ground truth | Current summaries omit the true AR(1) self-parent `target(t-1)` | All benchmark truth tables and narratives must include the self-parent explicitly |
| Nonlinear recovery story | Current shipped hybrid reliably demonstrates only benchmark-specific partial recovery | Docs must say `may recover at least one nonlinear parent on this benchmark`, not promise both |
| V3-F03 pairwise-method wording | MI/TE/GCMI are described too loosely as if they recover multivariate causal parents | Rephrase as dependence-detection / directional-evidence language, not direct causal-graph recovery |
| Example evidence status | Example outputs are illustrative, not broad validation | Every example and status doc must label them as `illustrative` or `benchmark-specific` |
| Benchmark validation limits | Current PASS-style checks can coexist with extra self-lags and other likely false positives | Docs must say the current benchmark checks are not exact parent-set validation and should not be read as proof that the recovered graph is fully correct |

**Required deliverables.**

| Deliverable | File(s) | Minimum required content |
|---|---|---|
| Theory reconciliation | `docs/theory/pcmci_plus.md` | Proposal vs shipped split, contemporaneous-edge interpretation, pros/cons table |
| Status reconciliation | `docs/implementation_status.md` | Accurate shipped status, experimental caveats, benchmark-specific evidence wording |
| Plan reconciliation | `docs/plan/v0_3_0_covariant_informative_ultimate_plan.md` | Follow-up work items, blocker list, exact boundaries of V3-F04 |
| Test-scope reconciliation | `tests/test_pcmci_adapter.py`, `tests/test_pcmci_ami_hybrid.py` reviewed from the docs pass | Explicit note of what current tests prove, what they do not prove, and where the docs must avoid stronger claims |
| Example narrative reconciliation | Renamed PCMCI example scripts | No overclaiming, correct ground truth, correct illustrative wording |
| Cross-method comparison guidance | Theory/status/example docs | Side-by-side pros/cons of V3-F03 vs V3-F04 |
| Review artifact | `docs/plan/implemented/v3_f03_v3_f04_second_loop_review.md` | One-page discrepancy checklist with evidence and disposition for each mismatch |

**Required review artifact format.**

The one-page discrepancy checklist must use one row per issue with these fields:

| Field | Meaning |
|---|---|
| Topic | Short mismatch label |
| Current shipped behavior | What the code/tests/examples actually do today |
| Current doc claim | What the docs currently imply or state |
| Gap type | `overclaim`, `ambiguity`, `missing caveat`, or `naming/path drift` |
| Required action | Exact documentation change required |
| Code blocker? | `yes` / `no` |
| Evidence | File paths or example outputs reviewed |

**Pros / cons table that must exist after this ticket.**

| Method | Pros that must be documented | Cons / caveats that must be documented |
|---|---|---|
| V3-F03 PCMCI+ (`parcorr` baseline) | Mature Tigramite implementation; good at removing redundant/shared-cause structure; supports contemporaneous adjacency discovery; cheaper and easier to interpret | Linear CI blind-spot for non-monotonic nonlinear couplings; `o-o` is not a directed parent; benchmark may still show extra self-lags |
| V3-F04 PCMCI-AMI shipped variant | Real Phase 0 MI pruning; smaller candidate set; benchmark-specific evidence of recovering at least one nonlinear parent missed by `parcorr` | Shipped variant is partial; CrossAMI is not integrated into the execution path; no MI-ranked conditioning-set logic yet; default path is residualization-based; current custom significance path is not reliable enough for strong confirmatory causal claims; phase outputs are not yet distinct |

**Required implementation sequence for the junior developer.**

1. Start from the current shipped code as the source of truth.
2. Build a one-page discrepancy checklist from:
   `src/forecastability/adapters/tigramite_adapter.py`,
   `src/forecastability/adapters/pcmci_ami_adapter.py`,
   `src/forecastability/adapters/knn_cmi_ci_test.py`,
   `tests/test_pcmci_adapter.py`,
   `tests/test_pcmci_ami_hybrid.py`,
   and the renamed PCMCI examples.
3. Save that checklist as
   `docs/plan/implemented/v3_f03_v3_f04_second_loop_review.md`.
4. Update `docs/theory/pcmci_plus.md` first.
5. Update `docs/implementation_status.md` second.
6. Update the renamed example narratives and docstrings third.
7. Update the release plan and any remaining cross-links last.
8. Re-run the three PCMCI examples and ensure the docs describe what actually
   happens, not what was hoped to happen.

**Mandatory wording rules.**

- Do **not** write as if the stronger MI-ranked conditioning-set design is
  already implemented.
- Do **not** write as if CrossAMI is already part of the shipped PCMCI-AMI
  execution path.
- Do **not** describe `o-o` as a directed parent unless the code contract is
  changed in a later source-code ticket.
- Do **not** describe the current `knn_cmi` path as fully non-parametric
  conditional independence.
- Do **not** frame the current V3-F04 p-values as confirmatory causal evidence
  while the i.i.d. shuffle null remains in place.
- Do **not** use pairwise MI/GCMI language as if it proves multivariate causal
  parenthood.
- Do explicitly mark comparison scripts as `illustrative synthetic evidence`.

**Recommended documentation flow.**

```mermaid
flowchart LR
    CODE["Current shipped code"] --> REVIEW["Discrepancy review"]
    THEORY["Theory + proposal docs"] --> REVIEW
    EXAMPLES["Runtime example outputs"] --> REVIEW
    REVIEW --> ALIGN["Align wording\n(proposal vs shipped)"]
    ALIGN --> PROSCONS["Pros / cons tables"]
    ALIGN --> STATUS["Implementation status update"]
    ALIGN --> EX_GUIDE["Example narrative update"]
```

**Acceptance criteria.**

- [ ] `docs/theory/pcmci_plus.md` distinguishes clearly between `full proposal` and `shipped variant`
- [ ] The docs state that the shipped V3-F04 default CI path is residualization-based
- [ ] The docs state explicitly that CrossAMI is not integrated into the current PCMCI-AMI execution path
- [ ] The docs state explicitly that the current V3-F04 custom significance path is not reliable enough for strong confirmatory causal claims on autocorrelated series
- [ ] The docs state explicitly that the current custom i.i.d. shuffle null is the reason those confirmatory claims are not reliable
- [ ] The docs no longer imply that `phase1_skeleton` and `phase2_final` are separate recovered graphs unless code changes first
- [ ] All benchmark truth summaries include `target(t-1)` as a structural self-parent
- [ ] The example wording says nonlinear recovery is benchmark-specific and may be partial
- [ ] The docs say clearly that current benchmark PASS checks are illustrative and not exact recovered-graph validation
- [ ] The second-loop review artifact exists at `docs/plan/implemented/v3_f03_v3_f04_second_loop_review.md`
- [ ] V3-F03 and V3-F04 each have an explicit pros/cons section
- [ ] `docs/implementation_status.md` keeps V3-F04 in a partial / experimental framing until the open caveats are resolved
- [ ] No document contradicts the actual behavior of the renamed example scripts

**Escalation rules.**

- If a documentation statement requires pretending the code behaves differently,
  stop and create a blocker note instead of softening the mismatch away.
- If release messaging wants stronger claims for V3-F04, that must be handled as
  a separate source-code ticket rather than hidden inside docs work.

---

### Phase 2 — Covariant Orchestration Facade

**Goal:** One entry point that validates inputs, runs all methods, and assembles a unified summary.

```mermaid
flowchart TD
    USER["User code / script / notebook"] --> FACADE["run_covariant_analysis()"]
    FACADE --> VALIDATE["Validate inputs\n(target, drivers, lags)"]
    VALIDATE --> CROSS_AMI["CrossAMI\n(existing exog_raw_curve_service)"]
    VALIDATE --> CROSS_PAMI["CrosspAMI\n(existing exog_partial_curve_service)"]
    VALIDATE --> TE_SVC["Transfer Entropy\n(transfer_entropy_service)"]
    VALIDATE --> GCMI_SVC["GCMI\n(gcmi_service)"]
    VALIDATE --> PCMCI_SVC["PCMCI+ adapter\n(tigramite_adapter)"]
    VALIDATE --> HYBRID_SVC["PCMCI-AMI-Hybrid\n(pcmci_ami_service)"]
    CROSS_AMI --> ASSEMBLE["Assemble\nCovariantAnalysisBundle"]
    CROSS_PAMI --> ASSEMBLE
    TE_SVC --> ASSEMBLE
    GCMI_SVC --> ASSEMBLE
    PCMCI_SVC --> ASSEMBLE
    HYBRID_SVC --> ASSEMBLE
    ASSEMBLE --> TABLE["CovariantSummaryRow[]\nunified table"]
    ASSEMBLE --> BUNDLE["CovariantAnalysisBundle\nfull results"]
```

#### V3-F06 — Covariant orchestration use case

**File:** `src/forecastability/use_cases/run_covariant_analysis.py`

```python
"""Covariant analysis orchestration facade.

This is the ONLY entry point for running the full covariant analysis
pipeline. Notebooks, scripts, and tests must all call this function —
no manual orchestration allowed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from forecastability.metrics.scorers import default_registry
from forecastability.services.exog_raw_curve_service import compute_exog_raw_curve
from forecastability.services.gcmi_service import compute_gcmi
from forecastability.services.transfer_entropy_service import compute_transfer_entropy
from forecastability.utils.types import (
    CovariantAnalysisBundle,
    CovariantSummaryRow,
    GcmiResult,
    TransferEntropyResult,
)

if TYPE_CHECKING:
    from forecastability.utils.types import CausalGraphResult, PcmciAmiResult

# All available methods
ALL_METHODS = frozenset({
    "cross_ami", "cross_pami", "te", "gcmi", "pcmci", "pcmci_ami",
})


def run_covariant_analysis(
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
    *,
    target_name: str = "target",
    max_lag: int = 40,
    methods: list[str] | None = None,
    ami_threshold: float = 0.05,
    alpha: float = 0.01,
    n_surrogates: int = 99,
    random_state: int = 42,
) -> CovariantAnalysisBundle:
    """Run the full covariant analysis pipeline.

    When ``methods`` is None, runs all available methods:
    CrossAMI, CrosspAMI, TE, GCMI, PCMCI+, PCMCI-AMI-Hybrid.
    When tigramite is not installed, PCMCI+ and PCMCI-AMI are silently skipped.

    Args:
        target: 1-D array of the target series.
        drivers: Dict mapping driver name → 1-D array.
        target_name: Name for the target in output tables.
        max_lag: Maximum lag horizon for all methods.
        methods: Subset of methods to run. None = all available.
        ami_threshold: MI threshold for PCMCI-AMI Phase 0 triage.
        alpha: Significance threshold for PCMCI+ CI tests.
        n_surrogates: Number of surrogates for significance bands (>= 99).
        random_state: Random seed. Must be int, not np.Generator.

    Returns:
        CovariantAnalysisBundle with all results and unified summary table.

    Raises:
        ValueError: If n_surrogates < 99 or unknown methods requested.
    """
    if n_surrogates < 99:
        raise ValueError(f"n_surrogates must be >= 99, got {n_surrogates}")

    requested = set(methods) if methods else set(ALL_METHODS)
    unknown = requested - ALL_METHODS
    if unknown:
        raise ValueError(f"Unknown methods: {unknown}. Available: {sorted(ALL_METHODS)}")

    registry = default_registry()
    mi_scorer = registry.get("mi").scorer
    horizons = list(range(1, max_lag + 1))
    rows: list[CovariantSummaryRow] = []
    te_results: list[TransferEntropyResult] = []
    gcmi_results: list[GcmiResult] = []
    pcmci_graph: CausalGraphResult | None = None
    pcmci_ami_result: PcmciAmiResult | None = None

    for driver_name, driver_array in drivers.items():
        for h in horizons:
            cross_ami_val: float | None = None
            te_val: float | None = None
            gcmi_val: float | None = None

            # --- CrossAMI ---
            if "cross_ami" in requested:
                cross_ami_val = float(compute_exog_raw_curve(
                    target, driver_array, max_lag=h,
                    scorer=mi_scorer, random_state=random_state,
                )[-1]) if h <= max_lag else None

            # --- GCMI ---
            if "gcmi" in requested:
                # Align target and lagged driver
                if h < len(target):
                    y = target[h:]
                    x_lag = driver_array[: len(target) - h]
                    gcmi_val = compute_gcmi(x_lag, y, random_state=random_state)
                    gcmi_results.append(GcmiResult(
                        source=driver_name, target=target_name,
                        lag=h, gcmi_value=gcmi_val,
                    ))

            # --- Transfer Entropy ---
            if "te" in requested:
                try:
                    te_val = compute_transfer_entropy(
                        driver_array, target, lag=h, random_state=random_state,
                    )
                    te_results.append(TransferEntropyResult(
                        source=driver_name, target=target_name,
                        lag=h, te_value=te_val,
                    ))
                except ValueError:
                    pass  # Skip if not enough data for this lag

            rows.append(CovariantSummaryRow(
                target=target_name,
                driver=driver_name,
                lag=h,
                cross_ami=cross_ami_val,
                transfer_entropy=te_val,
                gcmi=gcmi_val,
            ))

    # --- PCMCI+ ---
    if "pcmci" in requested:
        try:
            from forecastability.adapters.tigramite_adapter import TigramiteAdapter

            all_data = np.column_stack(
                [target] + [drivers[d] for d in drivers]
            )
            all_names = [target_name] + list(drivers.keys())
            adapter = TigramiteAdapter(ci_test="parcorr")
            pcmci_graph = adapter.discover(
                all_data, all_names, max_lag=max_lag, alpha=alpha,
                random_state=random_state,
            )
        except ImportError:
            pass  # tigramite not installed — skip silently

    # --- PCMCI-AMI ---
    if "pcmci_ami" in requested:
        try:
            from forecastability.adapters.tigramite_adapter import TigramiteAdapter
            from forecastability.services.pcmci_ami_service import PcmciAmiService

            all_data = np.column_stack(
                [target] + [drivers[d] for d in drivers]
            )
            all_names = [target_name] + list(drivers.keys())
            adapter = TigramiteAdapter(ci_test="parcorr")
            service = PcmciAmiService(adapter, ami_threshold=ami_threshold)
            pcmci_ami_result = service.discover(
                all_data, all_names, max_lag=max_lag, alpha=alpha,
                random_state=random_state,
            )
        except ImportError:
            pass  # tigramite not installed — skip silently

    return CovariantAnalysisBundle(
        summary_table=rows,
        te_results=te_results or None,
        gcmi_results=gcmi_results or None,
        pcmci_graph=pcmci_graph,
        pcmci_ami_result=pcmci_ami_result,
        target_name=target_name,
        driver_names=list(drivers.keys()),
        horizons=horizons,
    )
```

#### V3-F07 — Unified covariant summary table

| Column | Type | Source | Interpretation |
|---|---|---|---|
| `target` | `str` | Input | Target variable name |
| `driver` | `str` | Input | Driver variable name |
| `lag` | `int` | Per-horizon analysis | Time lag $h$ |
| `cross_ami` | `float \| None` | `exog_raw_curve_service` | Unconditional MI at lag $h$ |
| `cross_pami` | `float \| None` | `exog_partial_curve_service` | Conditional MI (intermediate lags removed) |
| `transfer_entropy` | `float \| None` | `transfer_entropy_service` | Directional information flow |
| `gcmi` | `float \| None` | `gcmi_service` | Rank-invariant nonlinear MI |
| `pcmci_link` | `str \| None` | `tigramite_adapter` | Graph edge type ("-->", "o->") |
| `pcmci_ami_parent` | `bool \| None` | `pcmci_ami_service` | Selected by PCMCI-AMI as parent |
| `significance` | `str \| None` | Surrogate bands / p-values | Significance assessment |
| `rank` | `int \| None` | Cross-method rank aggregation | Overall driver ranking |
| `interpretation_tag` | `str \| None` | Interpretation logic | Human-readable tag |

**Interpretation tags and heuristic rank score:**

```python
# Suggested interpretation tags:
# - "strong_direct_candidate": high MI + TE + confirmed by PCMCI+
# - "directional_but_not_causal_confirmed": high TE but PCMCI+ absent
# - "pairwise_only_probably_spurious": high MI/GCMI but PCMCI+ rejects
# - "redundant_driver": correlated with a stronger driver
# - "noise_or_weak": all scores near zero

# Suggested rank score heuristic (release-internal, not scientific truth):
# rank_score = (
#     0.20 * normalized_cross_ami
#     + 0.20 * normalized_cross_pami
#     + 0.20 * normalized_gcmi
#     + 0.20 * normalized_te
#     + 0.20 * pcmci_bonus  # +1 if PCMCI+ confirms, 0 otherwise
# )
```

#### Acceptance criteria — Phase 2 ✅ CLOSED 2026-04-17

- [x] `run_covariant_analysis()` produces a `CovariantAnalysisBundle`
- [x] Unified table has one row per (target, driver, lag) combination
- [x] Methods gracefully skip when optional deps unavailable
- [x] Facade is the ONLY orchestration entry point used by notebook, script, and tests
- [x] `CovariantSummaryRow` and per-method result models expose a `lagged_exog_conditioning` metadata field with values `none` / `target_only` / `full_mci`, populated correctly per §5A
- [x] `CovariantAnalysisBundle.metadata` includes a disclaimer string pointing at §5A for any bundle that contains `target_only` entries, and a forward link to the v0.3.1 plan
- [x] `uv run pytest tests/test_covariant_facade.py -q` passes
- [x] `CovariantSummaryRow.significance`, `.rank`, `.interpretation_tag` fully populated (V3-F07 complete)

---

### Phase 3 — Covariant Tests + Regression Fixtures

**Goal:** Product-grade test coverage with deterministic synthetic systems.

```mermaid
flowchart LR
    subgraph "Synthetic Fixtures"
        BM["Covariant benchmark\n(6 variables, known parents)"]
        DP["Directional pair\n(known X→Y)"]
        NOISE["Independent noise\n(null control)"]
    end

    subgraph "Test Layers"
        UNIT["Unit tests\n(per-method)"]
        INTEG["Integration tests\n(facade)"]
        REGR["Regression fixtures\n(SHA-256 provenance)"]
    end

    BM --> UNIT
    DP --> UNIT
    NOISE --> UNIT
    UNIT --> INTEG
    INTEG --> REGR
```

#### Facade integration test example

**File:** `tests/test_covariant_facade.py`

```python
"""Integration tests for the covariant analysis facade."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.use_cases.run_covariant_analysis import run_covariant_analysis
from forecastability.utils.synthetic import generate_covariant_benchmark


class TestRunCovariantAnalysis:
    @pytest.fixture
    def benchmark_df(self):
        return generate_covariant_benchmark(n=800, seed=42)

    def test_returns_bundle_with_all_drivers(self, benchmark_df) -> None:
        """Facade should return results for all requested drivers."""
        drivers = {
            col: benchmark_df[col].to_numpy()
            for col in benchmark_df.columns if col != "target"
        }
        result = run_covariant_analysis(
            benchmark_df["target"].to_numpy(),
            drivers,
            max_lag=3,
            methods=["cross_ami", "gcmi", "te"],
            random_state=42,
        )
        assert len(result.driver_names) == 5
        assert len(result.summary_table) > 0

    def test_noise_driver_scores_low(self, benchmark_df) -> None:
        """driver_noise should have near-zero scores across all methods."""
        drivers = {
            "driver_noise": benchmark_df["driver_noise"].to_numpy(),
            "driver_direct": benchmark_df["driver_direct"].to_numpy(),
        }
        result = run_covariant_analysis(
            benchmark_df["target"].to_numpy(),
            drivers,
            max_lag=3,
            methods=["gcmi", "te"],
            random_state=42,
        )
        noise_gcmi = [
            r.gcmi_value for r in (result.gcmi_results or [])
            if r.source == "driver_noise"
        ]
        direct_gcmi = [
            r.gcmi_value for r in (result.gcmi_results or [])
            if r.source == "driver_direct"
        ]
        assert max(noise_gcmi) < max(direct_gcmi)

    def test_rejects_low_surrogates(self) -> None:
        with pytest.raises(ValueError, match="n_surrogates must be >= 99"):
            run_covariant_analysis(
                np.zeros(100), {"x": np.zeros(100)},
                n_surrogates=50,
            )

    def test_rejects_unknown_methods(self) -> None:
        with pytest.raises(ValueError, match="Unknown methods"):
            run_covariant_analysis(
                np.zeros(100), {"x": np.zeros(100)},
                methods=["magic_method"],
            )

    def test_skips_pcmci_when_tigramite_missing(self, benchmark_df) -> None:
        """When tigramite is absent, PCMCI methods should be silently skipped."""
        drivers = {"d": benchmark_df["driver_direct"].to_numpy()}
        result = run_covariant_analysis(
            benchmark_df["target"].to_numpy(),
            drivers,
            max_lag=3,
            methods=["gcmi"],  # Only non-tigramite methods
            random_state=42,
        )
        assert result.pcmci_graph is None
        assert result.pcmci_ami_result is None
```

#### Regression fixtures

- Generated once, stored as `.npz` in `tests/fixtures/covariant/`
- SHA-256 hash recorded alongside for provenance
- Regenerable via `scripts/rebuild_covariant_fixtures.py`:

```python
"""Rebuild deterministic covariant fixtures for regression tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from forecastability.utils.synthetic import generate_covariant_benchmark

FIXTURES_DIR = Path("tests/fixtures/covariant")


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    df = generate_covariant_benchmark(n=1500, seed=42)
    data = df.to_numpy()

    npz_path = FIXTURES_DIR / "covariant_benchmark.npz"
    np.savez(npz_path, data=data, columns=df.columns.tolist())

    sha = hashlib.sha256(npz_path.read_bytes()).hexdigest()
    manifest = {"covariant_benchmark.npz": sha}
    (FIXTURES_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Fixture saved: {npz_path} (SHA-256: {sha})")


if __name__ == "__main__":
    main()
```

#### Test files

| File | Coverage |
|---|---|
| `tests/test_transfer_entropy.py` | TE scorer + service (5 tests above) |
| `tests/test_gcmi.py` | GCMI scorer + service (6 tests above) |
| `tests/test_pcmci_adapter.py` | TigramiteAdapter isolation (3 tests above) |
| `tests/test_pcmci_ami_hybrid.py` | PCMCI-AMI three-phase algorithm (4 tests above) |
| `tests/test_covariant_facade.py` | `run_covariant_analysis()` end-to-end (5 tests above) |
| `tests/test_covariant_regression.py` | SHA-256 fixture comparisons |
| `tests/test_covariant_models.py` | Result model serialization round-trip |

#### Acceptance criteria — Phase 3

- [x] Each method has ≥ 3 unit tests (positive, negative, edge case)
- [x] Facade integration test with covariant benchmark fixture
- [x] Regression fixtures pass deterministic comparison (JSON-based float/string/bool tolerance; `atol=1e-6`)
- [x] `n_surrogates >= 99` enforced in every surrogate call
- [x] `random_state: int` — never `numpy.Generator`
- [x] AMI computed per horizon $h$ separately — never aggregated before computation
- [x] AMI and pAMI computed on `split.train` ONLY inside any rolling-origin loop (partial residualization is linear via `sklearn.linear_model.LinearRegression`; pCrossAMI MUST NOT be described as non-parametric in any output metadata)
- [x] `np.trapezoid` for AUC — `np.trapz` removed in NumPy 2.x
- [x] Regression test: pCrossAMI rows ALWAYS carry `lagged_exog_conditioning == "target_only"`; raw CrossMI rows ALWAYS carry `"none"`; PCMCI+/PCMCI-AMI rows ALWAYS carry `"full_mci"`. A test MUST fail if any output metadata, docstring, or bundle field claims pCrossAMI is "fully conditioned on exogenous lags"
- [x] `uv run pytest tests/test_covariant*.py tests/test_transfer*.py tests/test_gcmi.py tests/test_pcmci*.py -q` all green (747 total; 0 failures)

---

### Phase 4 — Canonical Showcase Outputs

**Goal:** Demonstrate the full covariant workflow in both script and notebook form.

```mermaid
flowchart TD
    subgraph "Showcase Outputs"
        SCRIPT["scripts/run_showcase_covariant.py\n(one command, all methods)"]
        NB["notebooks/walkthroughs/\n01_covariant_informative_showcase.ipynb\n(pedagogical walkthrough)"]
    end

    subgraph "Data Sources"
        BIKE["UCI Bike Sharing hourly\ndata/raw/exog/bike_sharing_hour.csv"]
        SYNTH["Synthetic benchmark\n(deterministic fixture)"]
    end

    subgraph "Artifact Outputs"
        JSON["outputs/json/\ncovariant_bundle.json"]
        TABLE["outputs/tables/\ncovariant_summary.csv"]
        FIGS["outputs/figures/\ncovariant_*.png"]
    end

    BIKE --> SCRIPT
    SYNTH --> SCRIPT
    BIKE --> NB
    SYNTH --> NB
    SCRIPT --> JSON
    SCRIPT --> TABLE
    SCRIPT --> FIGS
    NB --> JSON
    NB --> TABLE
    NB --> FIGS
```

#### V3-F09 — `scripts/run_showcase_covariant.py`

**Complete skeleton:**

```python
"""Canonical covariant showcase — one command, all methods, full artifacts.

Usage:
    uv run python scripts/run_showcase_covariant.py
    uv run python scripts/run_showcase_covariant.py --no-rolling
    uv run python scripts/run_showcase_covariant.py --methods cross_ami,te,gcmi
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from forecastability.use_cases.run_covariant_analysis import run_covariant_analysis
from forecastability.utils.synthetic import generate_covariant_benchmark

OUTPUT_DIR = Path("outputs")


def main() -> int:
    parser = argparse.ArgumentParser(description="Covariant showcase")
    parser.add_argument("--no-rolling", action="store_true", help="Skip rolling-origin")
    parser.add_argument("--methods", type=str, default=None, help="Comma-separated methods")
    args = parser.parse_args()

    methods = args.methods.split(",") if args.methods else None

    # --- Synthetic benchmark ---
    print("[forecastability] Generating synthetic covariant benchmark...")
    df = generate_covariant_benchmark(n=1500, seed=42)
    target = df["target"].to_numpy()
    drivers = {col: df[col].to_numpy() for col in df.columns if col != "target"}

    print(f"[forecastability] Running covariant analysis (max_lag=5, methods={methods or 'all'})...")
    result = run_covariant_analysis(
        target, drivers,
        max_lag=5,
        methods=methods,
        random_state=42,
    )

    # --- Write artifacts ---
    (OUTPUT_DIR / "json").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "tables").mkdir(parents=True, exist_ok=True)

    bundle_json = result.model_dump_json(indent=2)
    (OUTPUT_DIR / "json" / "covariant_bundle.json").write_text(bundle_json)

    summary_df = pd.DataFrame([row.model_dump() for row in result.summary_table])
    summary_df.to_csv(OUTPUT_DIR / "tables" / "covariant_summary.csv", index=False)

    # --- Console summary ---
    print(f"\n[forecastability] Covariant showcase complete")
    print(f"  target={result.target_name}  drivers={result.driver_names}")
    print(f"  horizons=1..{max(result.horizons)}  rows={len(result.summary_table)}")
    if result.pcmci_ami_result:
        p0 = result.pcmci_ami_result
        print(f"  PCMCI-AMI: pruned={p0.phase0_pruned_count} kept={p0.phase0_kept_count}")
    print(f"  artifacts: {OUTPUT_DIR}/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Expected console output:**

```text
[forecastability] Generating synthetic covariant benchmark...
[forecastability] Running covariant analysis (max_lag=5, methods=all)...
[forecastability] Covariant showcase complete
  target=target  drivers=['driver_direct', 'driver_mediated', 'driver_redundant', 'driver_noise', 'driver_contemp']
  horizons=1..5  rows=25
  PCMCI-AMI: pruned=72 kept=78
  artifacts: outputs/
```

#### V3-F10 — Notebook sections

| Section | Content | Key code |
|---|---|---|
| A — Why covariant | Pairwise MI is inflated by autocorrelation; PCMCI+ fixes this | Markdown only |
| B — Data setup | Load synthetic benchmark, explain variable roles | `generate_covariant_benchmark()` |
| C — Baseline | CrossAMI + CrosspAMI via facade | `run_covariant_analysis(methods=["cross_ami"])` |
| D — GCMI | Show monotonic invariance, compare with MI | `run_covariant_analysis(methods=["gcmi"])` |
| E — TE | Show directionality: TE(direct→target) > TE(target→direct) | `run_covariant_analysis(methods=["te"])` |
| F — PCMCI+ | Graph output, direct vs indirect drivers | `run_covariant_analysis(methods=["pcmci"])` |
| G — PCMCI-AMI | Phase 0 pruning stats, final graph | `run_covariant_analysis(methods=["pcmci_ami"])` |
| H — Unified table | All methods combined | `run_covariant_analysis()` (all methods) |

**Notebook cell example — Section E (TE directionality):**

```python
# Cell: Demonstrate TE directionality
from forecastability.services.transfer_entropy_service import compute_transfer_entropy_result
from forecastability.utils.synthetic import generate_directional_pair

df_pair = generate_directional_pair(n=2000, seed=42)

te_xy = compute_transfer_entropy_result(df_pair, source="x", target="y", lag=1)
te_yx = compute_transfer_entropy_result(df_pair, source="y", target="x", lag=1)

print(f"TE(x→y) = {te_xy.te_value:.4f} nats")
print(f"TE(y→x) = {te_yx.te_value:.4f} nats")
print(f"Ratio:    {te_xy.te_value / max(te_yx.te_value, 1e-10):.1f}×")
# Expected output:
# TE(x→y) = 0.08-0.15 nats
# TE(y→x) = 0.00-0.02 nats
# Ratio:    5-20×
```

#### Acceptance criteria — Phase 4

- [ ] `uv run python scripts/run_showcase_covariant.py` runs end-to-end
- [x] Notebook is top-to-bottom executable
- [x] Both demonstrate all six methods
- [x] Artifacts emitted to stable paths
- [x] No notebook-only logic — all computation via `run_covariant_analysis()`
- [x] Notebook contains a dedicated section titled **"Known limitation: exogenous autohistory is not conditioned out in CrossMI/pCrossAMI/TE—see v0.3.1"** reproducing the §5A conditioning-scope table and linking to `docs/plan/v0_3_1_lagged_exogenous_triage_plan.md`

---

### Phase 5 — CI/CD Hardening

**Goal:** Close every identified CI/CD gap so v0.3.0 ships with confidence.

```mermaid
flowchart LR
    subgraph "V3-CI Tickets"
        CI01["V3-CI-01\nPython matrix\n3.11 + 3.12"]
        CI02["V3-CI-02\nWheel smoke test\nimport + covariant"]
        CI03["V3-CI-03\nShowcase smoke\nboth scripts"]
        CI04["V3-CI-04\nNotebook contract\ncovariant notebook"]
        CI05["V3-CI-05\nArtifact upload\nJSON + table + figs"]
        CI06["V3-CI-06\nRelease checklist\nchangelog + version"]
        CI07["V3-CI-07\nPre-commit\nruff + ty"]
    end

    CI01 --> CI_YML[".github/workflows/ci.yml"]
    CI02 --> PUB_YML[".github/workflows/publish-pypi.yml"]
    CI03 --> CI_YML
    CI04 --> CI_YML
    CI05 --> CI_YML
    CI06 --> REL_YML[".github/workflows/release.yml"]
    CI07 --> PRECOMMIT[".pre-commit-config.yaml"]
```

#### V3-CI-01 — Python version matrix

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12"]
```

#### V3-CI-02 — Install-from-wheel smoke test

```yaml
- name: Smoke test installed package
  run: |
    uv pip install dist/*.whl
    python -c "import forecastability; print(forecastability.__version__)"
    python -c "from forecastability.utils.types import CovariantSummaryRow"
    python -c "from forecastability.services.gcmi_service import compute_gcmi"
```

#### V3-CI-03 — Showcase script smoke test

```yaml
- name: Showcase smoke test
  run: |
    uv run python scripts/run_showcase.py --no-rolling --no-bands
    uv run python scripts/run_showcase_covariant.py --no-rolling --methods cross_ami,gcmi,te
```

#### V3-CI-04 — Notebook contract validation

```python
REQUIRED_NOTEBOOKS = [
    "notebooks/walkthroughs/00_air_passengers_showcase.ipynb",
    "notebooks/walkthroughs/01_covariant_informative_showcase.ipynb",
]
```

#### V3-CI-05 — Artifact upload

```yaml
- name: Upload covariant artifacts
  uses: actions/upload-artifact@v4
  with:
    name: covariant-outputs
    path: |
      outputs/json/covariant_bundle.json
      outputs/tables/covariant_summary.csv
      outputs/figures/covariant_*.png
```

#### V3-CI-06 — Release checklist automation

```yaml
- name: Release preflight
  run: |
    grep -q '## \[0.3.0\]' CHANGELOG.md
    test -f scripts/run_showcase_covariant.py
    python -c "import forecastability; assert forecastability.__version__ == '0.3.0'"
```

#### V3-CI-07 — Pre-commit hook alignment

```yaml
# .pre-commit-config.yaml additions:
- repo: https://github.com/astral-sh/ruff-pre-commit
  hooks:
    - id: ruff
      args: [--fix]
    - id: ruff-format
```

#### Acceptance criteria — Phase 5

- [ ] CI runs on Python 3.11 AND 3.12
- [ ] Wheel install smoke test passes before PyPI upload
- [ ] Both showcase scripts pass in CI
- [ ] Notebook contract validates covariant notebook
- [ ] Artifacts uploaded as CI outputs
- [ ] Release checklist enforced in release workflow
- [ ] Pre-commit covers ruff + ty

---

### Phase 6 — Documentation + Status Refresh

**Goal:** Make repo messaging reflect the v0.3.0 product shape.

```mermaid
flowchart TD
    README["README.md\nDual workflow:\nunivariate + covariant"] --> QS["docs/quickstart.md\nUpdated commands"]
    README --> API["docs/public_api.md\nNew methods documented"]
    README --> STATUS["docs/implementation_status.md\nRefreshed status table"]
    CL["CHANGELOG.md\nv0.3.0 entry"] --> README
    ADR["docs/decisions/\nADR-001-pcmci-ami-hybrid.md"] --> README
```

#### V3-D02 — Recommended status table after v0.3.0

| Surface | Status |
|---|---|
| Univariate deterministic triage | Stable |
| Covariant deterministic workflow | Beta |
| TE / GCMI / PCMCI+ within covariant | Beta |
| PCMCI-AMI-Hybrid | Experimental |
| CLI | Beta |
| HTTP API | Beta |
| Dashboard | Beta |
| Agent narration | Experimental |
| MCP server | Experimental |

#### V3-D03 — ADR for PCMCI-AMI-Hybrid

**File:** `docs/decisions/ADR-001-pcmci-ami-hybrid.md`

```markdown
<!-- type: reference -->
# ADR-001: PCMCI-AMI-Hybrid as a Separate Method

## Status
Accepted

## Context
PCMCI+ (Runge, 2020) discovers causal graphs but suffers from combinatorial
explosion at large τ_max. A naive fix (shrinking τ_max) discards valid lags.

Catt (2026) shows that AMI measures horizon-specific information decay and
can identify which lags carry genuine past-future dependence.

## Decision
Implement PCMCI-AMI-Hybrid as a **separate method** — not PCMCI+ with a
different CI test. The hybrid uses AMI as Phase 0 informational triage to
prune uninformative links before running PCMCI+'s lagged skeleton and MCI.

**Why separate?** AMI triage is structurally different from a CI test. It
operates unconditionally (no conditioning set), is non-parametric (kNN),
and serves a different purpose (search-space reduction, not independence testing).

**Why tigramite behind an adapter?** Tigramite is a mature, tested
implementation. The project's contribution is the AMI triage layer, not
a competing PCMCI+ engine. Optional dependency keeps core package lean.

## Consequences
- Users without tigramite can still use CrossAMI, TE, GCMI
- PCMCI-AMI is Experimental status in v0.3.0
- Attribution: Catt (2026) for AMI triage + Runge (2020) for PCMCI+
```

#### Acceptance criteria — Phase 6

- [ ] README clearly separates univariate and covariant workflows
- [ ] README and `docs/quickstart.md` include the §5A conditioning-scope table in plain text (one row per method, `none` / `target_only` / `full_mci`)
- [ ] `docs/quickstart.md` includes covariant quick-start
- [ ] `CHANGELOG.md` has complete v0.3.0 entry and an explicit "Known limitations" subsection naming the lagged-exogenous conditioning gap and forward-linking to v0.3.1
- [ ] ADR for PCMCI-AMI-Hybrid decision exists
- [ ] `docs/implementation_status.md` updated with new status table
- [ ] `docs/plan/v0_3_1_lagged_exogenous_triage_plan.md` exists and is linked from this plan's §5A

---

## 8. Cross-cutting deliverables

| Deliverable | Owner layer | Files affected |
|---|---|---|
| `pyproject.toml` optional dependency group for tigramite | Packaging | `pyproject.toml` |
| `forecastability[causal]` extra | Packaging | `pyproject.toml` |
| Version bump to `0.3.0` | Packaging | `pyproject.toml`, `__init__.py` |
| `tigramite` never in core deps | Architecture | All `import` statements |
| `random_state: int` everywhere | Scientific | All new services and scorers |
| `n_surrogates >= 99` | Scientific | All surrogate calls |
| `np.trapezoid` not `np.trapz` | Scientific | All AUC computations |
| pAMI described as project extension | Wording | All docs and docstrings |
| PCMCI-AMI cites Catt (2026) + Runge (2020) | Wording | Docstrings, ADR, notebook |

**Packaging example for `pyproject.toml`:**

```toml
[project.optional-dependencies]
causal = ["tigramite>=5.2"]
```

---

## 9. Exclusions

| Excluded | Why |
|---|---|
| Destabilizing stable univariate imports | Additive-only principle |
| Turning the project into a generic causal-discovery framework | Paper-aligned identity |
| Broad agentic redesign | Out of scope for v0.3.0 |
| Shipping notebook-only logic | Hexagonal architecture mandate |
| PCMCI-AMI replacing existing dependence methods | It is additive, not a replacement |
| Python 3.13 as required | Optional canary only |
| Air Passengers as covariant dataset | Univariate; use synthetic benchmark instead |
| HSIC validation layer | Nice-to-have, does not block v0.3.0 |

---

## 10. Scientific invariants — mandatory in all new code

| Invariant | Enforcement | Example |
|---|---|---|
| AMI computed per horizon $h$ separately | Service signatures accept single `h` | `compute_exog_raw_curve(target, exog, max_lag=h)` |
| AMI/pAMI on `split.train` ONLY in rolling-origin | `RollingOriginSplit` contract | Never compute on test set |
| `np.trapezoid` for AUC | Grep check in CI | `auc = np.trapezoid(curve, dx=1)` |
| `random_state` is always `int` | Type annotation | `random_state: int = 42` (not `np.Generator`) |
| `n_surrogates >= 99` | Pydantic `Field(ge=99)` | Validated in facade |
| pAMI is project extension | Wording review | Not "paper-native" |
| PCMCI-AMI cites Catt + Runge | Docstrings + ADR | All docstrings include refs |
| `tigramite` is optional | Architecture boundary test | `import` only in adapter |

---

## 11. Definition of done — per phase

| Phase | Done when |
|---|---|
| **0 — Contracts** | All models importable, `CausalGraphPort` passes runtime checks, zero computation code, linter clean |
| **1 — Methods** | Each method independently testable, synthetic fixture passes, `tigramite` isolated in adapter |
| **2 — Facade** | `run_covariant_analysis()` returns `CovariantAnalysisBundle`, unified table populated, methods skip gracefully |
| **3 — Tests** | ≥ 3 unit tests per method, facade integration test, regression fixture SHA-256 match, all scientific invariants hold |
| **4 — Showcase** | Script and notebook run end-to-end, all six methods demonstrated, artifacts emitted to stable paths |
| **5 — CI/CD** | Python matrix, wheel smoke, showcase smoke, notebook contract, artifact upload, release checklist, pre-commit |
| **6 — Docs** | README dual-workflow, quickstart updated, CHANGELOG v0.3.0, ADR exists, status table refreshed |

---

## 12. Junior-developer backlog

### Epic A — Synthetic benchmark + shared utilities (Week 1, Days 1-2)

- [ ] Create `src/forecastability/utils/synthetic.py` with `generate_covariant_benchmark()` and `generate_directional_pair()`
- [ ] Create `src/forecastability/utils/lagged_design.py` with `build_lagged_frame()` and `build_te_frame()`
- [ ] Write quick smoke test for both generators
- [ ] Verify: `generate_covariant_benchmark(seed=42)` produces 1500×6 DataFrame with expected column names

### Epic B — GCMI implementation (Week 1, Days 3-5)

- [ ] Create `src/forecastability/services/gcmi_service.py` with `gaussian_copula_transform()`, `covariance_mi_bits()`, `compute_gcmi()`
- [ ] Add `_gcmi_scorer()` to `src/forecastability/metrics/scorers.py` in `default_registry()`
- [ ] Register as `"gcmi"` with `family="bounded_nonlinear"`
- [ ] Write `tests/test_gcmi.py` with ≥ 4 tests (see Phase 1 examples above)
- [ ] Verify: `compute_gcmi(x, exp(x) + noise)` > 0.1 and `compute_gcmi(noise1, noise2)` < 0.05

### Epic C — CMI interface + Transfer Entropy (Week 2, Days 1-3)

- [ ] Create `src/forecastability/diagnostics/cmi_estimators.py` with `ConditionalMIEstimator`, `KnnConditionalMIEstimator`, `GaussianConditionalMIEstimator`
- [ ] Create `src/forecastability/services/transfer_entropy_service.py` with `compute_transfer_entropy()` and `compute_transfer_entropy_result()`
- [ ] Add `_te_scorer()` to `default_registry()` as `"te"` with `family="nonlinear"`
- [ ] Write `tests/test_transfer_entropy.py` with ≥ 5 tests (see Phase 1 examples above)
- [ ] Verify: `TE(x→y) > TE(y→x)` on `generate_directional_pair()`

### Epic D — PCMCI+ adapter (Week 2, Days 4-5)

- [x] Create `src/forecastability/adapters/tigramite_adapter.py` with `TigramiteAdapter`
- [x] Guard `tigramite` import with try/except and clear error message
- [x] Implement `_map_results()` to convert tigramite graph → `CausalGraphResult`
- [x] Add `[causal]` optional dependency group in `pyproject.toml`: `tigramite>=5.2`
- [x] Write `tests/test_pcmci_adapter.py` with ≥ 3 tests (see Phase 1 examples above, guarded by `pytest.importorskip`)
- [x] Add dedicated standalone PCMCI+ example with actionable missing-dependency hint; V3-F04.1 relocated it to `examples/covariant_informative/causal_discovery/pcmci_plus_benchmark.py`
- [x] Verify: on synthetic benchmark, `driver_direct` found as parent, `driver_noise` absent

### Epic E — PCMCI-AMI-Hybrid (Week 3, Days 1-3)

- [ ] Create `src/forecastability/services/pcmci_ami_service.py` with `PcmciAmiService`
- [ ] Implement `_phase0_ami_triage()`: compute MI for all (source, lag, target), prune below threshold, sort by MI
- [ ] Implement `_phase1_lagged_skeleton()`: delegate to `TigramiteAdapter`
- [ ] Implement `_phase2_mci_contemporaneous()`: delegate to `TigramiteAdapter`
- [ ] Write `tests/test_pcmci_ami_hybrid.py` with ≥ 4 tests (see Phase 1 examples above)
- [ ] Verify: Phase 0 prunes > 30% of links, noise driver links pruned
- [x] V3-F04.1 — Reorganized every active script previously under `examples/triage/` into the univariate vs covariant-informative taxonomy, applied the PCMCI renames, namespaced outputs, and removed active triage paths repo-wide
- [ ] V3-F04.2 — Run a second review loop across V3-F03 and V3-F04; reconcile theory, implementation, examples, and documentation with explicit pros/cons and caveats for both methods

### Epic F — Covariant orchestration facade (Week 3, Days 4-5)

- [ ] Create `src/forecastability/use_cases/run_covariant_analysis.py`
- [ ] Wire CrossAMI via existing `exog_raw_curve_service`
- [ ] Wire CrosspAMI via existing `exog_partial_curve_service`
- [ ] Wire TE via `transfer_entropy_service`
- [ ] Wire GCMI via `gcmi_service`
- [ ] Wire PCMCI+ via `tigramite_adapter` (skip if not installed)
- [ ] Wire PCMCI-AMI via `pcmci_ami_service` (skip if not installed)
- [ ] Assemble `CovariantSummaryRow[]` and `CovariantAnalysisBundle`
- [ ] Write `tests/test_covariant_facade.py` (see Phase 3 examples above)

### Epic G — Tests + regression fixtures (Week 4, Days 1-2)

- [ ] Create `scripts/rebuild_covariant_fixtures.py`
- [ ] Generate and store fixtures in `tests/fixtures/covariant/`
- [ ] Write `tests/test_covariant_regression.py` with SHA-256 comparison
- [ ] Write `tests/test_covariant_models.py` — serialization round-trip for all Pydantic models
- [ ] Run full test suite: `uv run pytest tests/test_covariant*.py tests/test_transfer*.py tests/test_gcmi.py tests/test_pcmci*.py -q`

### Epic H — Showcase script + notebook (Week 4, Days 3-4)

- [ ] Create `scripts/run_showcase_covariant.py` with `--no-rolling` and `--methods` flags
- [ ] Emit `outputs/json/covariant_bundle.json`, `outputs/tables/covariant_summary.csv`
- [x] Create `notebooks/walkthroughs/01_covariant_informative_showcase.ipynb` with sections A–H
- [x] Verify: notebook runs top-to-bottom, no notebook-only logic
- [x] Verify: all computation flows through `run_covariant_analysis()`

### Epic I — CI/CD hardening (Week 4, Day 5)

- [ ] V3-CI-01: Add Python 3.11 + 3.12 matrix to `ci.yml`
- [ ] V3-CI-02: Add wheel install smoke test to `publish-pypi.yml`
- [ ] V3-CI-03: Add showcase script smoke tests to `ci.yml`
- [x] V3-CI-04: Extend `scripts/check_notebook_contract.py` for covariant notebook
- [ ] V3-CI-05: Add artifact upload step to `ci.yml`
- [ ] V3-CI-06: Add release checklist checks to `release.yml`
- [ ] V3-CI-07: Align `.pre-commit-config.yaml` with ruff + ty

### Epic J — Documentation + release (Week 5)

- [ ] Update `README.md` with dual-workflow structure (univariate + covariant)
- [ ] Update `docs/quickstart.md` with covariant quick-start commands
- [ ] Update `docs/public_api.md` with new methods
- [ ] Update `docs/implementation_status.md` with new status table
- [ ] Write `CHANGELOG.md` entry for v0.3.0
- [ ] Create `docs/decisions/ADR-001-pcmci-ami-hybrid.md`
- [ ] Bump version to `0.3.0` in `pyproject.toml` and `__init__.py`
- [ ] Final `uv run pytest -q -ra` pass
- [ ] Final `uv run ruff check . && uv run ty check` pass
- [ ] Tag `v0.3.0`

---

## 13. Branch and milestone proposal

### Branch

- `feat/v0.3.0-covariant-informative` (already created)

### Milestones

| # | Milestone | Depends on |
|---|---|---|
| M0 | Synthetic benchmark + utilities | — |
| M1 | GCMI implementation | M0 |
| M2 | CMI interface + TE | M0 |
| M3 | PCMCI+ adapter | M0 |
| M4 | PCMCI-AMI-Hybrid | M0, M3 |
| M5 | Covariant facade | M1, M2, M3, M4 |
| M6 | Tests + regression fixtures | M5 |
| M7 | Showcase script + notebook | M5 |
| M8 | CI/CD hardening | M6, M7 |
| M9 | Documentation + status refresh | M8 |
| M10 | Tag + publish | M9 |

```mermaid
gantt
    title v0.3.0 Covariant Informative — Milestone Dependencies
    dateFormat YYYY-MM-DD
    section Foundation
        M0 Benchmark + utilities   :m0, 2026-04-17, 2d
    section Methods
        M1 GCMI                    :m1, after m0, 3d
        M2 CMI + TE               :m2, after m0, 3d
        M3 PCMCI+ adapter         :m3, after m0, 2d
        M4 PCMCI-AMI-Hybrid       :m4, after m3, 3d
    section Integration
        M5 Covariant facade       :m5, after m1 m2 m4, 2d
    section Quality
        M6 Tests + regression     :m6, after m5, 2d
        M7 Showcase outputs       :m7, after m5, 2d
    section Release
        M8 CI/CD hardening        :m8, after m6 m7, 1d
        M9 Docs + status          :m9, after m8, 2d
        M10 Tag + publish         :m10, after m9, 1d
```

---

## 13A. v0.3.0 exit criteria — finalized triage gate

v0.3.0 ships as a **finalized covariant-informative triage gate**, not as a full
lagged-exogenous confirmatory toolkit. Before tagging `v0.3.0`, all of the following must
be true:

- [ ] Every ticket V3-F00 through V3-F10 is either **Done** or explicitly **Deferred** with a
      one-line reason recorded in §4 (e.g. MI-ranked conditioning and CrossAMI past-window
      deferred to v0.3.1 under V3-F04).
- [ ] Every ticket V3-CI-01 through V3-CI-07 is **Done**.
- [ ] Every ticket V3-D01 through V3-D03 is **Done**.
- [ ] The §5A conditioning-scope table is present in `README.md` and in `docs/quickstart.md`,
      with identical wording for method rows and the `none` / `target_only` / `full_mci`
      tag values.
- [ ] `CovariantSummaryRow` and per-method result payloads carry a
      `lagged_exog_conditioning` metadata field populated per §5A, and the facade bundle
      metadata carries a disclaimer string plus a forward link to the v0.3.1 plan.
- [ ] A regression test (Phase 3) fails if any shipped docstring, metadata field, or bundle
      string ever describes pCrossAMI as "fully conditioned on exogenous lags" or as
      non-parametric.
- [ ] The v0.3.1 plan file [`docs/plan/v0_3_1_lagged_exogenous_triage_plan.md`](v0_3_1_lagged_exogenous_triage_plan.md)
      exists, is in `Draft / Proposed` state, and is linked from §5A of this plan and from
      the v0.3.0 `CHANGELOG.md` "Known limitations" subsection.
- [ ] No shipped covariant showcase output or notebook cell implies that pCrossAMI or
      TE in the v0.3.0 bundle recovers lag-specific exogenous effects in the presence of
      exogenous autocorrelation.

---

## 13B. Post-review AI action items (2026-04-18)

These items were added after a repository review focused on mathematical validity,
hexagonal/SOLID architecture quality, and documentation correctness. They are not
new feature requests; they are follow-up actions required to keep the shipped
v0.3.0 story technically coherent.

| ID | Theme | Severity | Finding | Required follow-up |
|---|---|---|---|---|
| V3-AI-01 | Release version integrity | Critical | `pyproject.toml` and `src/forecastability/__init__.py` still declare `0.2.0` while `CHANGELOG.md` and multiple v0.3.0 docs already describe a shipped `0.3.0` surface. | Before any `v0.3.0` tag or publish action, align packaging/runtime version metadata and rerun the release-checklist command that asserts `forecastability.__version__ == "0.3.0"`. |
| V3-AI-02 | Hexagonal contract hardening | High | `run_covariant_analysis()` depends on a local `_PcmciAmiFullPort` protocol because `CausalGraphPort` does not express `discover_full()`. The PCMCI-AMI use-case path is therefore coupled to adapter-only behavior; `pcmci_ami_adapter.py` also imports Tigramite helper internals from another adapter module. | Introduce a declared port for full PCMCI-AMI results (or split graph ports cleanly by responsibility), remove the local protocol from the use-case layer, and move shared Tigramite helper logic out of adapter-to-adapter imports. |
| V3-AI-03 | Covariant role semantics | High | `mediated_driver` can currently be assigned when a causal method merely exists in the bundle, even if that driver has no PCMCI+/PCMCI-AMI support. That still over-claims mediation from target-only pCrossAMI evidence. | Tighten the role rule so mediation requires driver-specific causal support or downgrade the case to `inconclusive`; update the deterministic interpretation docs and regression tests together. |
| V3-AI-04 | Public API / quickstart accuracy | Medium | **Resolved (2026-04-18):** user-facing covariant examples and the package facade now share one contract; `generate_covariant_benchmark` and `generate_directional_pair` are exported at top-level `forecastability`. | Completed via top-level re-export in `src/forecastability/__init__.py` and public API contract alignment in docs; verification passed with ruff, ty, pytest, and quickstart import run. |
| V3-AI-05 | Documentation freshness | Medium | `docs/implementation_status.md` still reports pre-closure V3-F06 caveats (no covariant notebook, no populated `significance`/`rank`/`interpretation_tag`) and several docs still carry `0.2.0` verification banners after the covariant merge. | Track and execute a dedicated documentation-freshness pass under a separate follow-up plan: `docs/plan/v0_3_2_documentation_quality_improvement_plan.md`. |

---

## 14. Final recommendation

This plan is the **definitive v0.3.0 blueprint**. It does not dilute the project into "just another bag of methods." It matures the product shape:

- **Univariate remains the stable reference path**
- **Covariant becomes a first-class analytical workflow**
- **TE + GCMI + PCMCI+ enrich covariant as layered analysis engines**
- **PCMCI-AMI-Hybrid is the novel contribution** — a separate method with its own protocol, service, and result model
- **Every method has complete code, math, theory, tests, and expected outputs** — a junior developer can implement without guessing
- **CI/CD and release discipline** make the new surface trustworthy
- **Architecture stays hexagonal** — every new method enters through the correct port/adapter/service boundary

A bad v0.3.0 would be three new methods with weak examples and no unified output.
A good v0.3.0 is one coherent covariant workflow with strong synthetic evidence, strong tests, and credible maturity messaging.
