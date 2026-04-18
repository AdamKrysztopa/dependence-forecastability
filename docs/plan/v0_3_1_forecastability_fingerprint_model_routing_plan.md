<!-- type: reference -->
# v0.3.1 — Forecastability Fingerprint & Model Routing: Ultimate Release Plan

**Plan type:** Actionable release plan — first follow-up to implemented `0.3.0`  
**Audience:** Maintainer, reviewer, Jr. developer  
**Target release:** `0.3.1`  
**Current released version:** `0.3.0`  
**Branch:** `feat/v0.3.1-forecastability-fingerprint`  
**Status:** Draft / Proposed  
**Last reviewed:** 2026-04-18  

**Companion refs:**

- [v0.3.0 Covariant Informative: Ultimate Release Plan](v0_3_0_covariant_informative_ultimate_plan.md)
- [v0.3.2 Lagged-Exogenous Triage: Ultimate Release Plan](v0_3_2_lagged_exogenous_triage_ultimate_plan.md)
- [v0.3.3 Documentation Quality Improvement: Ultimate Release Plan](v0_3_3_documentation_quality_improvement_ultimate_plan.md)
- [v0.3.4 Routing Validation & Benchmark Hardening: Ultimate Release Plan](v0_3_4_routing_validation_benchmark_hardening_plan.md)

**Builds on:**

- implemented `0.3.0` univariate + covariant triage surfaces
- hexagonal architecture, `ScorerRegistry`, port / adapter separation
- existing AMI / pAMI / directness-ratio logic and profile-oriented interpretation
- current recommendation and interpretation service patterns
- existing examples, showcase scripts, notebook contract checks, and CI / release workflows

---

## 1. Why this plan exists

`0.3.0` made the repo much stronger mathematically and architecturally, but the
package still presents many diagnostics as separate outputs instead of a compact,
decision-ready **forecastability fingerprint**.

Peter Catt's comment points to the right missing abstraction:

- `information_mass`
- `information_horizon`
- `information_structure`
- `nonlinear_share`

These should not be implemented as another disconnected metric family. They should
be the first-class **summary layer over the AMI profile**, and they should drive
model-family routing.

This plan therefore reframes the next release around one product question:

> Given a forecastability profile, what compact fingerprint best describes it,
> and what model classes should that fingerprint recommend?

### Planning principles

| Principle | Implication |
|---|---|
| Additive, not disruptive | Stable public univariate/covariant imports remain valid |
| Hexagonal + SOLID | Scorers compute signals; fingerprint services summarize; routing services recommend |
| AMI-first identity | Fingerprint is derived primarily from horizon-wise AMI behavior |
| Clear semantics | Directness is not nonlinearity; keep `directness_ratio` separate from `nonlinear_share` |
| Product maturation | `0.3.1` should improve the user decision story, not merely add outputs |
| One facade, many engines | Users call a dedicated fingerprint use case or opt into fingerprint inside existing bundle flows |

---

## 2. Theory-to-code map — mathematical foundations

> [!IMPORTANT]
> Every junior developer MUST read this section before writing any code.
> The release is small in surface area but high in semantic risk.

### 2.1. Forecastability profile recap

Let the univariate forecastability profile be the horizon-wise AMI curve:

$$AMI(h) = I(X_t ; X_{t+h})$$

for horizons $h = 1, \dots, H$.

The package already treats forecastability as **horizon-dependent**, not as a
single global scalar. That is the correct base for the fingerprint.

### 2.2. `information_mass`

`information_mass` is the normalized area under the informative portion of the
AMI profile.

Recommended implementation:

$$M = \frac{\sum_{h \in \mathcal{H}_{info}} AMI(h)}{\max(1, |\mathcal{H}_{info}|)}$$

where $\mathcal{H}_{info}$ is the set of informative horizons under the existing
significance / thresholding logic.

Alternate equivalent implementation is acceptable if and only if:

- it is monotone in the total informative AMI signal,
- it does not inflate long noisy tails,
- it is documented consistently in code, docs, and notebook outputs.

Interpretation:

- low mass → weak overall forecastability
- high mass → rich usable predictive information

### 2.3. `information_horizon`

`information_horizon` is the latest horizon that remains informative.

Recommended implementation:

$$H_{info} = \max(\mathcal{H}_{info})$$

with the convention that if $\mathcal{H}_{info} = \varnothing$, the result is `0`.

Interpretation:

- short horizon → prediction decays quickly
- long horizon → information persists farther into the future

### 2.4. `information_structure`

`information_structure` is a categorical label on the shape of the AMI profile.

Initial taxonomy for `0.3.1`:

- `none`
- `monotonic`
- `periodic`
- `mixed`

Recommended rule system:

1. `none` if no informative horizons exist
2. `monotonic` if informative AMI decays broadly with horizon and no stable
   secondary peaks pass the prominence threshold
3. `periodic` if significant repeated peaks occur near a dominant spacing
4. `mixed` for everything else

This must be a **domain service**, not plotting logic.

### 2.5. `nonlinear_share`

`nonlinear_share` must compare AMI against a **linear Gaussian-information baseline**.

For each horizon $h$, define a Gaussian-information proxy from Pearson autocorrelation:

$$I_G(h) = -\frac{1}{2}\log(1 - \rho(h)^2)$$

when $|\rho(h)| < 1$, with numerically safe clipping.

Then define the nonlinear excess:

$$E(h) = \max(AMI(h) - I_G(h), 0)$$

and aggregate over informative horizons:

$$N = \frac{\sum_{h \in \mathcal{H}_{info}} E(h)}{\sum_{h \in \mathcal{H}_{info}} AMI(h) + \epsilon}$$

Interpretation:

- low share → mostly linear dependence story
- high share → substantial dependence beyond linear autocorrelation structure

> [!WARNING]
> `nonlinear_share` is NOT `1 - directness_ratio`.
> `directness_ratio` measures direct vs mediated lag structure.
> `nonlinear_share` measures nonlinear excess over a linear baseline.

### 2.6. `directness_ratio` stays separate

The repo already has the idea of directness / mediated structure.
That is useful and should remain part of routing, but as a separate field.

The routing object for `0.3.1` should therefore contain at least:

- `information_mass`
- `information_horizon`
- `information_structure`
- `nonlinear_share`
- `directness_ratio`

### 2.7. Model-family routing

The goal is not to pick a single exact model. The goal is to route toward
**model families**.

Initial mapping policy:

| Fingerprint pattern | Recommended families |
|---|---|
| low mass, `none` | naïve, seasonal naïve, stop / downscope effort |
| high mass, monotonic, low nonlinear share, high directness | ARIMA / ETS / linear state-space / dynamic regression |
| high mass, periodic | seasonal naïve / harmonic regression / TBATS / seasonal state-space |
| mixed structure or high nonlinear share | tree-on-lags / TCN / N-BEATS / NHITS / nonlinear tabular baselines |
| high mass but low directness | increase lookback, inspect mediated structure, prefer richer state representation |

This routing policy must be explicit and versioned. It is a product rule, not an
implicit interpretation hidden in notebooks.

---

## 3. Repo baseline — what already exists

| Layer | Module | What it provides | Status |
|---|---|---|---|
| **Scorers** | `src/forecastability/metrics/scorers.py` | dependence scorers and registry pattern | Stable |
| **Services** | `src/forecastability/services/forecastability_profile_service.py` | profile-oriented interpretation surface | Stable |
| **Services** | `src/forecastability/services/recommendation_service.py` | recommendation/routing precedent | Stable |
| **Diagnostics** | current AMI / pAMI / directness logic | horizon-wise dependence and shape evidence | Stable |
| **Pipeline** | `src/forecastability/pipeline/analyzer.py` | existing orchestration pattern | Stable |
| **Use cases** | `src/forecastability/use_cases/` | existing facade/use-case conventions | Stable |
| **Utils** | `src/forecastability/utils/types.py` | typed-result pattern | Stable |
| **Examples** | univariate walkthrough + showcase | user-facing evidence surface | Stable |
| **CI** | existing matrix, smoke, notebook contract, release checklist | release hygiene baseline | Stable |

---

## 4. Feature inventory and overlap assessment

| ID | Feature | Phase | Overlap with existing | Genuine new work | Status |
|---|---|---:|---|---|---|
| V3_1-F00 | Typed fingerprint result models | 0 | Extends `utils/types.py` patterns | `ForecastabilityFingerprint`, `RoutingRecommendation`, `FingerprintBundle` | Proposed |
| V3_1-F01 | Linear Gaussian-information baseline | 1 | Reuses Pearson / autocorrelation logic | per-horizon `I_G(h)` service with stable clipping and aggregation | Proposed |
| V3_1-F02 | Fingerprint builder service | 1 | Builds on AMI/profile outputs | `information_mass`, `information_horizon`, `information_structure`, `nonlinear_share` | Proposed |
| V3_1-F03 | Routing policy service | 1 | Extends current recommendation logic | explicit model-family policy keyed by fingerprint buckets | Proposed |
| V3_1-F04 | Fingerprint orchestration use case | 2 | Follows existing use-case / facade pattern | `run_forecastability_fingerprint()` and optional bundle integration | Proposed |
| V3_1-F05 | Unified summary rendering | 2 | Extends current reporting helpers | compact summary row / markdown / JSON surface for fingerprint + routing | Proposed |
| V3_1-F06 | Tests and regression fixtures | 3 | Follows current deterministic regression pattern | synthetic archetypes, threshold tests, routing invariants | Proposed |
| V3_1-F07 | Showcase script and notebook | 4 | Follows existing walkthrough / showcase pattern | canonical four-series fingerprint demo | Proposed |
| V3_1-CI-01 | Routing smoke test in CI | 5 | Extends smoke workflow | import + run on canonical synthetic panel | Proposed |
| V3_1-CI-02 | Notebook contract extension | 5 | Extends notebook contract checks | fingerprint notebook included | Proposed |
| V3_1-CI-03 | Release checklist update | 5 | Extends release template | versioned routing / fingerprint checks | Proposed |
| V3_1-D01 | README + quickstart routing section | 6 | Extends docs | fingerprint concept and example snippets | Proposed |
| V3_1-D02 | Theory doc | 6 | New theory page | fingerprint definitions and routing semantics | Proposed |
| V3_1-D03 | Changelog + migration note | 6 | Release docs | additive feature surface and policy notes | Proposed |

---

## 5. Domain contracts — MANDATORY FIRST STEP

### 5.1. Typed result models

**File:** `src/forecastability/utils/types.py`

```python
class ForecastabilityFingerprint(BaseModel, frozen=True):
    """Compact summary of forecastability profile semantics."""

    information_mass: float
    information_horizon: int
    information_structure: str
    nonlinear_share: float
    directness_ratio: float | None = None
    informative_horizons: list[int] = Field(default_factory=list)
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class RoutingRecommendation(BaseModel, frozen=True):
    """Model-family recommendation driven by a fingerprint."""

    primary_families: list[str]
    secondary_families: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    caution_flags: list[str] = Field(default_factory=list)
    confidence_label: str = "medium"
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class FingerprintBundle(BaseModel, frozen=True):
    """Composite output from the forecastability fingerprint use case."""

    target_name: str
    fingerprint: ForecastabilityFingerprint
    recommendation: RoutingRecommendation
    profile_summary: dict[str, str | int | float]
    metadata: dict[str, str | int | float] = Field(default_factory=dict)
```

### 5.2. Port / service boundary rules

- scorers do not emit model recommendations
- routing policy is a service, not a plotting helper
- fingerprint building can depend on profile outputs, but not on dashboard code
- the use case composes services and formats typed results; adapters only render

### 5.3. Acceptance criteria

- all new types are importable from the typed surface
- no route recommendation logic is embedded in notebook cells
- no existing analyzer public interface is broken

---

## 6. Synthetic benchmark panel — MANDATORY BEFORE ROUTING

> [!IMPORTANT]
> Routing logic without archetypal benchmark series becomes opinionated guesswork.

### 6.1. Required synthetic families

Create a deterministic benchmark generator module for four canonical classes:

1. `white_noise`
2. `ar1_monotonic`
3. `seasonal_periodic`
4. `nonlinear_mixed`

Optional fifth class for stronger mediated structure:

5. `mediated_directness_drop`

### 6.2. Expected fingerprint behavior

| Series archetype | Expected structure | Expected mass | Expected nonlinear share | Expected routing |
|---|---|---|---|---|
| white noise | `none` | low | low | naïve / stop |
| AR(1) | `monotonic` | medium/high | low | ARIMA / ETS |
| seasonal | `periodic` | medium/high | low/medium | seasonal families |
| nonlinear synthetic | `mixed` | medium/high | high | nonlinear model families |
| mediated lag process | `monotonic` or `mixed` | medium | variable | caution on directness / state representation |

### 6.3. Acceptance criteria

- deterministic by seed
- used in tests, showcase, and notebook
- each archetype has docstring-grounded expected behavior
- at least one regression asserts routing family output, not only raw metric values

---

## 7. Phased delivery

### Phase 0 — Domain contracts and benchmark panel

**Goal:** define typed outputs, benchmark generators, and hard semantic constraints.

#### V3_1-F00 — Typed fingerprint result models

**File targets**

- `src/forecastability/utils/types.py`
- export surfaces if applicable

**Acceptance criteria**

- frozen typed models added
- JSON serialization is stable
- no existing type contracts regress

#### V3_1-F00.1 — Synthetic fingerprint archetype generators

**File targets**

- `src/forecastability/utils/synthetic.py` or dedicated companion module
- tests + example helpers

**Acceptance criteria**

- deterministic by seed
- benchmark families documented and reusable
- no notebook reimplements generation ad hoc

---

### Phase 1 — Core services

**Goal:** implement fingerprint semantics and routing behind clean service boundaries.

#### V3_1-F01 — Linear Gaussian-information baseline

**Goal.** Compute a per-horizon linear benchmark.

**File targets**

- `src/forecastability/services/linear_information_baseline_service.py` — new
- tests

**Acceptance criteria**

- uses autocorrelation / Pearson-derived information proxy
- clips safely near `|rho| = 1`
- returns horizon-wise and aggregate outputs
- documented as linear baseline, not as AMI replacement

#### V3_1-F02 — Fingerprint builder service

**Goal.** Build the fingerprint from profile outputs.

**File targets**

- `src/forecastability/services/fingerprint_service.py` — new
- `src/forecastability/services/forecastability_profile_service.py` — if helper reuse is warranted
- tests

**Acceptance criteria**

- computes `information_mass`
- computes `information_horizon`
- assigns `information_structure`
- computes `nonlinear_share`
- preserves `directness_ratio` as separate input/output
- does not require plotting adapter code

#### V3_1-F03 — Routing policy service

**Goal.** Map fingerprints to model families.

**File targets**

- `src/forecastability/services/routing_policy_service.py` — new
- tests

**Acceptance criteria**

- explicit, versioned bucket rules
- returns primary + secondary families
- returns rationale and caution flags
- confidence label is deterministic and rule-based
- no single exact-model promise is made

---

### Phase 2 — Use case and facade integration

**Goal:** expose the new capability cleanly.

#### V3_1-F04 — Forecastability fingerprint use case

**Goal.** Create a dedicated orchestration function.

**File targets**

- `src/forecastability/use_cases/run_forecastability_fingerprint.py` — new
- optional additive export surface
- optional integration hook in existing triage/use-case bundles

**Acceptance criteria**

- accepts series plus existing AMI/profile settings
- returns `FingerprintBundle`
- uses only domain/application services
- stable additive API; no breaking import changes

#### V3_1-F05 — Unified summary rendering

**Goal.** Make the output easy to consume in scripts, agents, and docs.

**File targets**

- reporting helper / markdown rendering utilities
- optional CLI adapter integration
- example JSON artifact builder

**Acceptance criteria**

- fingerprint summary is visible in one compact object
- recommendation rationale is human-readable
- output is stable enough for regression tests

---

### Phase 3 — Tests and regression

**Goal:** lock the semantics before publicizing the feature.

#### V3_1-F06 — Fingerprint tests

**Required test classes**

- `test_information_horizon_zero_when_no_signal`
- `test_monotonic_structure_on_ar1`
- `test_periodic_structure_on_seasonal_series`
- `test_nonlinear_share_rises_above_linear_baseline`
- `test_directness_ratio_not_used_as_nonlinear_share`
- `test_routing_white_noise_to_naive_family`
- `test_routing_periodic_to_seasonal_family`
- `test_routing_nonlinear_to_nonlinear_family`

**Acceptance criteria**

- deterministic by seed
- no fragile exact floating-point thresholds without tolerance
- routing tests assert family inclusion, not exact full prose strings

#### V3_1-F06.1 — Regression fixtures

**Goal.** Freeze representative fingerprint bundles for canonical examples.

**Acceptance criteria**

- fixture rebuild script exists
- drift is visible in CI
- policy changes require intentional fixture refresh

---

### Phase 4 — Showcase and notebook

**Goal:** make the product story obvious.

#### V3_1-F07 — Showcase script

**File targets**

- `scripts/run_showcase_fingerprint.py` — new

**Acceptance criteria**

- runs four canonical series
- emits fingerprint JSON / markdown / figures
- can be used in CI smoke mode

#### V3_1-F07.1 — Walkthrough notebook

**File targets**

- `notebooks/walkthroughs/02_forecastability_fingerprint_showcase.ipynb`

**Acceptance criteria**

- explains the fingerprint concept
- shows four canonical archetypes
- shows recommended families and caution notes
- no logic divergence from reusable services

---

### Phase 5 — CI / release hygiene

#### V3_1-CI-01 — Routing smoke test

- add quick fingerprint run to smoke workflow

#### V3_1-CI-02 — Notebook contract extension

- include fingerprint notebook in contract checker

#### V3_1-CI-03 — Release checklist update

- add fingerprint artifact / fixture / docs checks

**Acceptance criteria**

- smoke path completes on CI-supported Python versions
- notebook contract passes
- release checklist mentions routing semantics explicitly

---

### Phase 6 — Documentation

#### V3_1-D01 — README + quickstart update

Add a new section:

- what the fingerprint is
- how it differs from raw metrics
- how to call it in three to eight lines

#### V3_1-D02 — Theory doc

**File targets**

- `docs/theory/forecastability_fingerprint.md`

Must document:

- formula definitions
- shape taxonomy
- routing semantics
- caveats and non-goals

#### V3_1-D03 — Changelog

Document additive capability, no breaking API, and routing caveat.

---

## 8. Out of scope for v0.3.1

- automatic exact-model selection
- hyperparameter optimization
- exogenous lag selection and tensor construction
- replacing current covariant workflows
- hiding routing uncertainty behind overconfident labels
- using pAMI/directness as a proxy for nonlinearity

---

## 9. Exit criteria

- [ ] Every ticket V3_1-F00 through V3_1-F07.1 is either **Done** or explicitly **Deferred** in §4.
- [ ] Every ticket V3_1-CI-01 through V3_1-CI-03 is **Done**.
- [ ] Every ticket V3_1-D01 through V3_1-D03 is **Done**.
- [ ] `ForecastabilityFingerprint`, `RoutingRecommendation`, and `FingerprintBundle` exist as typed outputs.
- [ ] `nonlinear_share` is documented and tested against a linear information baseline.
- [ ] `directness_ratio` is kept semantically separate from `nonlinear_share` in code, docs, and examples.
- [ ] The canonical showcase runs on at least four archetypal series.
- [ ] At least one regression fixture protects routing behavior from silent drift.
- [ ] No doc, notebook, or bundle string claims the package selects the one true optimal model.

---

## 10. Recommended implementation order

```text
1. Phase 0 models + synthetic archetypes
2. Linear baseline service
3. Fingerprint service
4. Routing service
5. Use case / facade
6. Tests + fixtures
7. Showcase + notebook
8. CI + docs + changelog
```
