<!-- type: reference -->
# v0.3.2 — Lagged-Exogenous Triage: Ultimate Release Plan

**Plan type:** Actionable release plan — fixed-lag exogenous follow-up to implemented `0.3.0`  
**Audience:** Maintainer, reviewer, Jr. developer  
**Target release:** `0.3.2`  
**Current released version:** `0.3.1`  
**Branch:** `feat/v0.3.2-lagged-exogenous-triage`  
**Status:** Draft / Proposed  
**Last reviewed:** 2026-04-18  

**Companion refs:**

- [v0.3.0 Covariant Informative: Ultimate Release Plan](v0_3_0_covariant_informative_ultimate_plan.md)
- [prior draft: v0.3.1 Lagged-Exogenous Triage](v0_3_1_lagged_exogenous_triage_plan.md)

**Builds on:**

- implemented `0.3.0` covariant triage gate
- `0.3.1` fingerprint/routing layer as an additive decision surface
- existing `cross_ami`, `cross_pami`, `te`, `gcmi`, `pcmci`, `pcmci_ami`
- existing covariant bundle, plot helpers, notebook contract, and examples taxonomy

---

## 1. Why this plan exists

The repo still lacks a clean **fixed-lag exogenous triage workflow** that separates:

- contemporaneous structure (`lag = 0`)
- predictive lag search (`lag >= 1`)
- linear baselines vs nonlinear lag dependence
- dense lag profiles vs sparse lag selection
- chronologically valid lag screening vs elastic alignment methods

The earlier draft already identified the core gap correctly. This ultimate version
brings it to the same maturity level and structure as the `0.3.0` implemented plan.

### Planning principles

| Principle | Implication |
|---|---|
| Fixed-lag chronology first | This release serves forecasting tensors, not elastic alignment |
| Additive, not disruptive | Existing covariant methods remain valid and correctly labeled |
| Hexagonal + SOLID | lag-profile services, pruning services, and rendering adapters remain separated |
| Honest semantics | `cross_pami` shipped in `0.3.0` remains `target_only` unless a truly stronger method is added |
| Diagnostic vs predictive clarity | `lag = 0` is reportable but never selectable for tensor construction |
| Architecture-neutral hand-off | output is a sparse lag map, not a commitment to one downstream model class |

---

## 2. Theory-to-code map — mathematical foundations

> [!IMPORTANT]
> The release is semantically sensitive. A wrong lag contract will contaminate every
> downstream exogenous model story.

### 2.1. Lag semantics

For target series $Y_t$ and exogenous series $X_t$:

- contemporaneous diagnostic: $I(X_t ; Y_t)$
- predictive lag candidate: $I(X_{t-k} ; Y_t)$ for $k \ge 1$

This release must encode the rule:

- `lag = 0` may appear in diagnostics and plots
- `lag = 0` may not appear in predictive candidate sets or lagged tensors

### 2.2. Linear baseline

For each pair and lag, compute standard cross-correlation as the cheap linear baseline.
This is descriptive and useful, but not causal.

### 2.3. Nonlinear lag profile

For each pair and lag, compute a `cross_ami` lag profile over `0..max_lag`.
This remains the nonlinear baseline for fixed-lag dependence.

### 2.4. Redundancy pruning

Dense lag profiles are not yet usable downstream. This release therefore adds a
crosspAMI-style sparse lag selector that prunes redundant lags and emits a clean
candidate set.

### 2.5. Confirmatory causal follow-up stays downstream

PCMCI+ / PCMCI-AMI remain confirmatory or higher-fidelity follow-up tools.
This release does not replace them. It improves the triage layer in front of them.

### 2.6. DTW omission is intentional

DTW and related warping methods are out of scope because they solve elastic-alignment
similarity, not fixed-lag predictive feature selection.

---

## 3. Repo baseline — what already exists

| Layer | Module | What it provides | Status |
|---|---|---|---|
| **Covariant methods** | existing `cross_ami`, `cross_pami`, `te`, `gcmi`, `pcmci`, `pcmci_ami` | current covariant dependence surfaces | Stable |
| **Services** | `raw_curve_service`, `exog_raw_curve_service`, `partial_curve_service`, `exog_partial_curve_service` | lag/horizon profile precedent | Stable |
| **Use cases** | `run_covariant_analysis()` and related workbench flows | orchestration surface | Stable |
| **Types** | `utils/types.py` | typed result model precedent | Stable |
| **Docs** | `docs/theory/covariant_summary_table.md` and walkthrough notebook | user-facing covariant explanation | Stable |
| **CI** | matrix + smoke + notebook contract + release checklist | release hygiene baseline | Stable |

---

## 4. Feature inventory and overlap assessment

| ID | Feature | Phase | Overlap with existing | Genuine new work | Status |
|---|---|---:|---|---|---|
| V3_2-F00 | Typed lagged-exogenous result models | 0 | Extends `utils/types.py` patterns | `LaggedExogProfileRow`, `LaggedExogSelectionRow`, `LaggedExogBundle` | Proposed |
| V3_2-F01 | Zero-lag-aware lag plumbing | 1 | Extends existing lag-profile paths | explicit `lag = 0` representation and role metadata | Proposed |
| V3_2-F02 | Standard cross-correlation baseline | 1 | Reuses Pearson logic | signed lag profile over `0..max_lag` | Proposed |
| V3_2-F03 | Extended `cross_ami` lag profile | 1 | Extends shipped `cross_ami` path | diagnostic `lag = 0` plus stable fixed-lag profile output | Proposed |
| V3_2-F04 | Sparse lag selector (crosspAMI-style pruning) | 1 | Builds on current target-only profile semantics | new selection layer with `selected_for_tensor` metadata | Proposed |
| V3_2-F05 | Lagged-exogenous orchestration use case | 2 | Follows `use_cases/` pattern | `run_lagged_exogenous_triage()` | Proposed |
| V3_2-F06 | Integration back into covariant bundle | 2 | Extends `run_covariant_analysis()` optionally | hand-off rows and sparse lag map | Proposed |
| V3_2-F07 | Tests and regression fixtures | 3 | Follows current deterministic regression pattern | lag semantics, zero-lag ban, selection drift checks | Proposed |
| V3_2-F08 | Plotting and notebook refresh | 4 | Extends covariant plots / notebook | correlogram-first human-facing artifact | Proposed |
| V3_2-CI-01 | Smoke path for lagged-exog triage | 5 | Extends smoke workflow | quick import + run on synthetic pair panel | Proposed |
| V3_2-CI-02 | Notebook contract extension | 5 | Extends notebook checks | lagged-exog notebook included | Proposed |
| V3_2-CI-03 | Release checklist update | 5 | Extends release template | zero-lag and sparse-map assertions | Proposed |
| V3_2-D01 | Theory doc and README update | 6 | Extends docs | lag semantics, DTW omission, sparse lag hand-off | Proposed |
| V3_2-D02 | Changelog and migration notes | 6 | Release docs | additive surface, no breaking analyzer change | Proposed |

---

## 5. Domain contracts — MANDATORY FIRST STEP

### 5.1. Typed result models

**File:** `src/forecastability/utils/types.py`

```python
class LaggedExogProfileRow(BaseModel, frozen=True):
    """One lag-domain diagnostic row for a target-driver pair."""

    target: str
    driver: str
    lag: int
    lag_role: str
    correlation: float | None = None
    cross_ami: float | None = None
    cross_pami: float | None = None
    significance: str | None = None
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class LaggedExogSelectionRow(BaseModel, frozen=True):
    """Sparse predictive lag selection row."""

    target: str
    driver: str
    lag: int
    selected_for_tensor: bool
    selection_order: int | None = None
    selector_name: str
    score: float | None = None
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class LaggedExogBundle(BaseModel, frozen=True):
    """Composite output from fixed-lag exogenous triage."""

    profile_rows: list[LaggedExogProfileRow]
    selected_lags: list[LaggedExogSelectionRow]
    metadata: dict[str, str | int | float] = Field(default_factory=dict)
```

### 5.2. Boundary rules

- profile computation is separate from pruning / selection
- selection logic is separate from plotting code
- rendering adapters do not decide whether `lag = 0` is predictive
- existing `cross_pami` semantics remain unchanged unless a new selector path is created

### 5.3. Acceptance criteria

- `lag = 0` is representable and explicitly tagged
- `selected_for_tensor=True` is impossible at `lag = 0`
- typed sparse output exists independently from plots

---

## 6. Synthetic benchmark panel — MANDATORY FIRST STEP

### 6.1. Required cases

1. direct lag-2 driver
2. mediated lag-1 driver
3. redundant correlated driver
4. pure noise driver
5. contemporaneous-only driver
6. optional nonlinear exogenous driver

### 6.2. Expected behavior

| Driver type | Expected `lag = 0` story | Expected selected lags |
|---|---|---|
| direct lagged | may or may not be small | correct predictive lag retained |
| mediated | profile may be broad | sparse set remains interpretable |
| redundant | dense profile may look strong | pruning should reduce redundancy |
| noise | weak profile | none |
| contemporaneous | strong at `0` only | none |
| nonlinear exogenous | correlation may miss it | `cross_ami` / selector may recover it |

### 6.3. Acceptance criteria

- deterministic by seed
- used in tests, showcase, and notebook
- at least one case proves `lag = 0` strong yet unselectable
- at least one case proves correlation and `cross_ami` disagree for a nonlinear driver

---

## 7. Phased delivery

### Phase 0 — Domain contracts and benchmark panel

#### V3_2-F00 — Typed lagged-exog result models

**Acceptance criteria**

- additive types exist
- JSON serialization is stable
- no existing covariant bundle breaks

#### V3_2-F00.1 — Benchmark generators / fixtures

**Acceptance criteria**

- canonical driver cases exist
- no notebook reimplements generators
- fixture expectations are documented

---

### Phase 1 — Core methods

#### V3_2-F01 — Zero-lag-aware lag plumbing

**File targets**

- `src/forecastability/services/raw_curve_service.py`
- `src/forecastability/services/exog_raw_curve_service.py`
- `src/forecastability/utils/types.py`
- supporting helpers as needed

**Acceptance criteria**

- diagnostic lag domain supports `0..max_lag`
- predictive logic still works on `1..max_lag`
- every `lag = 0` row is tagged as `contemporaneous`

#### V3_2-F02 — Standard cross-correlation baseline

**File targets**

- covariant use case or dedicated service
- plotting helpers
- tests

**Acceptance criteria**

- signed correlogram retained
- not immediately collapsed to absolute score
- documented as linear baseline, not causal evidence

#### V3_2-F03 — Extended `cross_ami` profile

**File targets**

- relevant covariant service path
- tests
- docs/theory touchpoints

**Acceptance criteria**

- `cross_ami` profile available over `0..max_lag`
- significance semantics remain honest and method-specific
- no silent estimator swap

#### V3_2-F04 — Sparse lag selector

**File targets**

- `src/forecastability/use_cases/screen_lagged_exog.py` or dedicated selector service
- tests
- type exports

**Acceptance criteria**

- evaluates only `k >= 1`
- emits `selected_for_tensor`, `selection_order`, or equivalent metadata
- does not relabel shipped `cross_pami` as fully conditioned
- if a stronger PMIME-style selector is introduced, it gets a new label and docs

---

### Phase 2 — Orchestration and integration

#### V3_2-F05 — `run_lagged_exogenous_triage()`

**Goal.** Provide a dedicated orchestration use case.

**Acceptance criteria**

- returns `LaggedExogBundle`
- profile rows + sparse selected lags both available
- no adapter-to-adapter coupling

#### V3_2-F06 — Integration back into covariant bundle

**Goal.** Make the new capability consumable from the higher-level covariant flow.

**Acceptance criteria**

- additive integration only
- covariant bundle can expose sparse lag hand-off metadata
- architecture remains neutral with respect to downstream model class

---

### Phase 3 — Tests and regression

#### V3_2-F07 — Lag semantics tests

Required classes:

- `test_zero_lag_row_is_diagnostic_only`
- `test_zero_lag_never_selected_for_tensor`
- `test_direct_driver_selected_at_expected_lag`
- `test_contemporaneous_only_driver_not_selected`
- `test_redundant_driver_pruned`
- `test_nonlinear_driver_can_exceed_linear_baseline`
- `test_shipped_cross_pami_semantics_not_overwritten`

#### V3_2-F07.1 — Regression fixtures

**Acceptance criteria**

- fixture rebuild script exists
- sparse selection drift is visible in CI
- docs strings protecting `target_only` semantics are regression-tested

---

### Phase 4 — Plotting and notebook

#### V3_2-F08 — Plotting refresh

**Acceptance criteria**

- correlograms and lag-domain `cross_ami` profiles are primary
- `lag = 0` visually separated
- selected predictive lags highlighted directly in plots

#### V3_2-F08.1 — Walkthrough notebook

**File targets**

- `notebooks/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb`

**Acceptance criteria**

- explains diagnostic vs predictive lag roles
- shows sparse lag map hand-off
- explains explicit DTW omission
- uses reusable services only

---

### Phase 5 — CI / release hygiene

#### V3_2-CI-01 — Smoke workflow addition

- run a quick lagged-exogenous triage example

#### V3_2-CI-02 — Notebook contract extension

- include the lagged-exog notebook

#### V3_2-CI-03 — Release checklist update

- add assertions for zero-lag handling and sparse lag selection

---

### Phase 6 — Documentation

#### V3_2-D01 — Theory doc + README update

Must state plainly:

- `lag = 0` is diagnostic only
- sparse lag map is the predictive hand-off
- DTW / FastDTW / shapeDTW are intentionally omitted

#### V3_2-D02 — Changelog and migration notes

Document additive surfaces and semantic clarifications.

---

## 8. Out of scope for v0.3.2

- using `lag = 0` as predictive tensor input
- claiming causal identification from correlation or pairwise MI
- replacing PCMCI+ / PCMCI-AMI as the confirmatory path
- adding elastic alignment methods as official exogenous triage tools
- committing downstream architecture to a single neural or tabular family

---

## 9. Exit criteria

- [ ] Every ticket V3_2-F00 through V3_2-F08.1 is either **Done** or explicitly **Deferred** in §4.
- [ ] Every ticket V3_2-CI-01 through V3_2-CI-03 is **Done**.
- [ ] Every ticket V3_2-D01 through V3_2-D02 is **Done**.
- [ ] `lag = 0` is supported diagnostically and blocked predictively.
- [ ] standard cross-correlation and `cross_ami` both exist as lag profiles over `0..max_lag`.
- [ ] sparse selected-lag output is restricted to `1..max_lag`.
- [ ] no active docs or notebook imply DTW is a recommended triage path.
- [ ] no active docs or notebook redescribe shipped `cross_pami` as a fully conditioned selector.

---

## 10. Recommended implementation order

```text
1. Phase 0 models + benchmark panel
2. Zero-lag lag plumbing
3. Correlation baseline
4. Extended cross_ami profile
5. Sparse lag selector
6. Use case + covariant integration
7. Tests + fixtures
8. Plotting + notebook
9. CI + docs + changelog
```
