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

### Reviewer acceptance block

For reviewer sign-off, `0.3.1` is successful only if Peter Catt's four requested
summary metrics are implemented as **stable typed outputs** and exposed
consistently across all intended user surfaces.

Required reviewer-visible outcomes:

- `information_mass`, `information_horizon`, `information_structure`, and
  `nonlinear_share` exist on a typed Python result object
- the same four fields appear in the CLI / JSON summary surface
- the same four fields appear in the walkthrough notebook and public example surfaces
  without notebook-only logic
- docs define the semantics, caveats, and routing interpretation for the same fields
- routing guidance consumes these fields through versioned deterministic rules

Reviewer comment crosswalk for this update:

- comment 2 (`Catt alignment`) → this block, §5.3, §9
- comment 3 (thresholding / significance semantics) → §2.2, §2.3, Phase 1
  acceptance criteria, Phase 3 threshold tests
- comment 4 (`information_structure` classifier rules) → §2.4, Phase 1
  acceptance criteria, Phase 3 classifier tests
- comment 5 (no-overclaim routing rule) → §2.7, §8, §9
- comment 6 (routing-quality validation task) → V3_1-F06.2, §9
- comment 7 (`nonlinear_share` calibration) → §6.2, Phase 3 tests
- comment 8 (routing confidence semantics) → §2.7, V3_1-F03
- comment 9 (mandatory public-surface examples) → V3_1-F05, V3_1-F08, V3_1-D01, §9
- comment 10 (univariate-first scope boundary) → planning principles, V3_1-D02,
  §8, §9

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

`information_mass` is the normalized masked area under the informative portion
of the AMI profile.

For `0.3.1`, define the informative horizon set as:

$$\mathcal{H}_{info} = \{h \in \{1, \dots, H\} : AMI(h) \ge \tau_{AMI} \ \land \ p_{sur}(h) \le \alpha \}$$

where:

- $p_{sur}(h)$ is the per-horizon surrogate-significance p-value already derived
  from the package's AMI significance machinery
- $\alpha$ is the configured significance level used by the profile computation
- $\tau_{AMI}$ is a minimum AMI floor applied after significance to reject
  numerically tiny but formally significant values

Required `0.3.1` semantics:

- `information_mass` and `information_horizon` MUST share the exact same
  $\mathcal{H}_{info}$ definition
- routing logic MUST consume the same informative-horizon mask rather than
  redefining thresholding locally
- $\mathcal{H}_{info}$ is an operational screening mask, not a claim of
  simultaneous family-wise significance across all tested horizons
- if multiple horizons satisfy the conditions, all of them contribute to
  `information_mass`
- if no horizons satisfy the conditions, `information_mass = 0.0` and
  `information_horizon = 0`
- tie handling is inclusive at the threshold boundary:
  `AMI(h) == \tau_{AMI}` and `p_{sur}(h) == \alpha` both count as informative
- edge behavior for invalid or truncated horizons is conservative: horizons
  lacking a valid AMI estimate or surrogate test result are excluded from
  $\mathcal{H}_{info}$ rather than imputed as informative

Required implementation on the discrete horizon grid:

$$M = \frac{1}{\max(1, H)} \sum_{h=1}^{H} AMI(h)\,\mathbf{1}[h \in \mathcal{H}_{info}]$$

This is intentionally **not** the mean AMI over informative horizons. It is the
masked area over the evaluated horizon grid, normalized by the full horizon
range so that both strength and extent contribute to the final value.

Interpretation:

- low mass → weak overall forecastability
- high mass → rich usable predictive information

### 2.3. `information_horizon`

`information_horizon` is the latest horizon that remains informative.

Required implementation:

$$H_{info} = \max(\mathcal{H}_{info})$$

with the convention that if $\mathcal{H}_{info} = \varnothing$, the result is `0`.

Additional required semantics:

- if the final informative horizons are non-contiguous, `information_horizon`
  still reports the latest informative horizon, not the count of informative
  horizons
- if several late horizons tie for the same AMI value, the latest informative
  horizon still wins because the metric is horizon-index based, not amplitude based
- routing rules that refer to "short" or "long" horizon MUST use this exact
  `H_info` output rather than a separate horizon summary

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

Required `0.3.1` classifier contract:

- peak detection operates only on informative horizons or on horizons with
  informative local maxima; non-informative peaks cannot trigger `periodic`
- a secondary peak counts only if its prominence is at least
  `max(peak_prominence_abs, peak_prominence_rel * max_informative_ami)`, with
  both thresholds fixed in the service configuration and documented
- repeated-peak spacing is considered stable if successive accepted peaks fall
  within `spacing_tolerance` horizons of the dominant spacing
- monotonicity is considered satisfied when informative AMI is non-increasing
  up to a `monotonicity_tolerance`; small local reversals within tolerance do
  not force `mixed`
- tie-breaking priority is deterministic:
  `none` > `periodic` > `monotonic` > `mixed`
- abstention / edge behavior is explicit:
  if there are too few informative horizons to support either repeated-peak or
  monotonic checks robustly, classify as `mixed` and emit a caution rather than
  inferring `periodic`

Practical interpretation of the tie-breaking rule:

- `none` wins whenever `\mathcal{H}_{info}` is empty
- `periodic` wins over `monotonic` when both rules appear plausible but the
  repeated-peak rule passes the documented prominence and spacing checks
- `monotonic` wins over `mixed` only when no qualifying periodic structure exists
  and the profile stays within the monotonicity tolerance band

### 2.5. `nonlinear_share`

`nonlinear_share` must compare AMI against a **linear Gaussian-information baseline**.

For each horizon $h$, define a Gaussian-information proxy from Pearson autocorrelation:

$$I_G(h) = -\frac{1}{2}\log(1 - \rho(h)^2)$$

when $|\rho(h)| < 1$, with numerically safe clipping.

Then define the nonlinear excess:

$$E(h) = \max(AMI(h) - I_G(h), 0)$$

and aggregate over informative horizons:

$$N = \frac{\sum_{h \in \mathcal{H}_{info}} E(h)}{\sum_{h \in \mathcal{H}_{info}} AMI(h) + \epsilon}$$

Required `0.3.1` edge behavior:

- if $\mathcal{H}_{info} = \varnothing$, return `nonlinear_share = 0.0`
- if the informative-horizon AMI denominator is `<= epsilon`, return
  `nonlinear_share = 0.0` rather than a noisy tiny ratio
- if `rho(h)` is invalid or undefined after safe clipping, exclude that horizon
  from the nonlinear-baseline aggregation and emit a caution rather than treating
  the horizon as evidence for strong nonlinearity

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

> [!IMPORTANT]
> Routing in `0.3.1` is heuristic product guidance. It is not empirical model
> selection, not a ranking guarantee, and not a promise that a recommended family
> will outperform all alternatives on a given series.

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

Required confidence semantics for `0.3.1`:

- confidence is derived from three deterministic binary penalties:
  `threshold_margin_penalty`, `taxonomy_uncertainty_penalty`, and
  `signal_conflict_penalty`
- `threshold_margin_penalty = 1` if any routing-defining scalar falls within a
  versioned margin band around its decision threshold
- `taxonomy_uncertainty_penalty = 1` if `information_structure == "mixed"`, if
  the classifier relied on a tie-break, or if informative support is below a
  versioned `min_confident_horizons`
- `signal_conflict_penalty = 1` if the primary route is supported by one signal
  but contradicted by another according to a versioned rule table, for example
  high nonlinear share paired with strongly linear routing or periodic routing
  with insufficient horizon support
- map penalty counts deterministically:
  `0 -> high`, `1 -> medium`, `2 or 3 -> low`
- confidence is derived from deterministic rule evaluation only; `0.3.1` does not
  claim benchmark-calibrated probabilities

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
| V3_1-F08 | Public examples and notebook extensions | 5 | Extends examples taxonomy and walkthrough surfaces | minimal Python example, CLI example, notebook cross-links, and reusable example artifacts | Proposed |
| V3_1-D01 | README + quickstart routing section | 5 | Extends docs | fingerprint concept and example snippets | Proposed |
| V3_1-D02 | Theory doc | 5 | New theory page | fingerprint definitions and routing semantics | Proposed |
| V3_1-D03 | Changelog + migration note | 5 | Release docs | additive feature surface and policy notes | Proposed |
| V3_1-CI-01 | Routing smoke test in CI | 6 | Extends smoke workflow | import + run on canonical synthetic panel | Proposed |
| V3_1-CI-02 | Notebook contract extension | 6 | Extends notebook contract checks | fingerprint notebook included | Proposed |
| V3_1-CI-03 | Release checklist update | 6 | Extends release template | versioned routing / fingerprint checks | Proposed |

---

## 5. Domain contracts — MANDATORY FIRST STEP

### 5.1. Typed result models

**File:** `src/forecastability/utils/types.py`

```python
FingerprintStructure = Literal["none", "monotonic", "periodic", "mixed"]
RoutingConfidenceLabel = Literal["low", "medium", "high"]
ModelFamilyLabel = Literal[
    "naive",
    "seasonal_naive",
    "downscope",
    "arima",
    "ets",
    "linear_state_space",
    "dynamic_regression",
    "harmonic_regression",
    "tbats",
    "seasonal_state_space",
    "tree_on_lags",
    "tcn",
    "nbeats",
    "nhits",
    "nonlinear_tabular",
]
RoutingCautionFlag = Literal[
    "near_threshold",
    "mixed_structure",
    "low_directness",
    "high_nonlinear_share",
    "short_information_horizon",
    "weak_informative_support",
    "signal_conflict",
]


class ForecastabilityFingerprint(BaseModel, frozen=True):
    """Compact summary of forecastability profile semantics."""

    information_mass: float
    information_horizon: int
    information_structure: FingerprintStructure
    nonlinear_share: float
    directness_ratio: float | None = None
    informative_horizons: list[int] = Field(default_factory=list)
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class RoutingRecommendation(BaseModel, frozen=True):
    """Model-family recommendation driven by a fingerprint."""

    primary_families: list[ModelFamilyLabel]
    secondary_families: list[ModelFamilyLabel] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    caution_flags: list[RoutingCautionFlag] = Field(default_factory=list)
    confidence_label: RoutingConfidenceLabel = "medium"
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
- categorical fingerprint / routing fields use closed literal labels or enums,
  not free-form strings
- no route recommendation logic is embedded in notebook cells
- no existing analyzer public interface is broken
- reviewer can verify that Peter Catt's four metrics appear unchanged in typed
  Python output, CLI / JSON summary output, example output, notebook output, and docs

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

Calibration / sanity-check expectations for `nonlinear_share`:

- white noise: near `0`, with no spurious high-share route caused by estimation noise
- AR(1): low and near `0` within tolerance because the dependence is primarily linear
- seasonal linear process: low to low / medium at most; periodic linear structure
  alone must not be mislabeled as strongly nonlinear
- nonlinear synthetic process: materially above the linear cases and high enough
  to activate the nonlinear-routing branch in at least one canonical example

### 6.3. Acceptance criteria

- deterministic by seed
- used in tests, showcase, examples, and notebooks
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
- uses one shared informative-horizon mask for metrics and routing
- documents the precise `H_info` thresholding semantics, including surrogate
  significance, AMI floor, tie handling, and invalid-horizon behavior
- applies deterministic classifier tolerances for prominence, spacing, and monotonicity

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
- includes an explicit non-goal statement that routing is heuristic product
  guidance, not empirical ranking or performance guarantee
- confidence label is derived from deterministic margins, taxonomy certainty,
  and signal consistency rather than prose judgment

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
- CLI / JSON summary adapter integration
- example JSON artifact builder

**Acceptance criteria**

- fingerprint summary is visible in one compact object
- CLI / JSON summary surface exposes the same four fingerprint fields plus routing output
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
- classifier tests cover tie-breaking, spacing tolerance, and monotonicity tolerance
- threshold tests cover significance boundary, AMI-floor boundary, and empty-set behavior

#### V3_1-F06.1 — Regression fixtures

**Goal.** Freeze representative fingerprint bundles for canonical examples.

**Acceptance criteria**

- fixture rebuild script exists
- drift is visible in CI
- policy changes require intentional fixture refresh

#### V3_1-F06.2 — Small curated routing-quality panel

**Goal.** Sanity-check routing quality on a small curated real or semi-real panel.

**Acceptance criteria**

- at least a small curated panel of real or semi-real series is evaluated before release
- expected broad family tags are documented for each case
- mismatches between expected and observed routing are recorded in docs or release notes
- the task is explicitly framed as a lightweight `0.3.1` sanity check, with broader
  calibration and hardening deferred to `0.3.4`

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
- shows the four Peter Catt metrics directly in notebook outputs

---

### Phase 5 — Examples, notebooks, and documentation

**Goal:** turn the feature into a complete public surface before CI freezes it.

#### V3_1-F08 — Public examples and notebook extensions

**Goal.** Create or extend example and notebook artifacts beyond the canonical showcase.

**File targets**

- `examples/` additions or refresh for fingerprint-facing usage
- `notebooks/walkthroughs/02_forecastability_fingerprint_showcase.ipynb`
- optional extension or cross-link in existing walkthrough / quickstart notebooks

**Acceptance criteria**

- at least one minimal Python example exists in `examples/` or the repo's equivalent
  example surface
- at least one CLI example is present in example artifacts, not only in README prose
- the fingerprint notebook is cross-linked from examples and docs surfaces
- at least one existing user-facing notebook or walkthrough is extended or linked so
  the fingerprint surface is discoverable outside the dedicated showcase
- examples and notebooks consume reusable services and do not introduce notebook-only
  logic divergence

#### V3_1-D01 — README + quickstart update

Add a new section:

- what the fingerprint is
- how it differs from raw metrics
- one mandatory short Python snippet showing fingerprint + routing output
- one mandatory CLI example showing fingerprint + routing output
- links to the example and notebook surfaces added in `V3_1-F08`

These examples are required release artifacts, not optional nice-to-haves.

#### V3_1-D02 — Theory doc

**File targets**

- `docs/theory/forecastability_fingerprint.md`

Must document:

- formula definitions
- the screening-mask meaning of per-horizon surrogate significance
- shape taxonomy
- routing semantics
- confidence penalty rules and their versioned thresholds / tolerances
- caveats and non-goals
- univariate-first / AMI-first scope boundary
- where users can find the public examples and notebook walkthroughs

#### V3_1-D03 — Changelog

Document additive capability, no breaking API, routing caveat, and the new
public example / notebook surfaces.

---

### Phase 6 — CI / release hygiene

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
- CI checks run only after example, notebook, and docs surfaces are in place

---

## 8. Out of scope for v0.3.1

- automatic exact-model selection
- hyperparameter optimization
- exogenous lag selection and tensor construction
- replacing current covariant workflows
- hiding routing uncertainty behind overconfident labels
- using pAMI/directness as a proxy for nonlinearity
- multivariate or conditional-MI fingerprint extensions
- benchmark-calibrated routing confidence probabilities

Scope statement for reviewers:

- `0.3.1` is intentionally univariate-first and AMI-first
- multivariate, conditional-MI, or broader empirical routing validation work belongs
  to follow-up releases, especially `0.3.4`, and is not part of this release

---

## 9. Exit criteria

- [ ] Every ticket V3_1-F00 through V3_1-F08, including sub-items such as V3_1-F00.1, V3_1-F06.1, V3_1-F06.2, and V3_1-F07.1, is either **Done** or explicitly **Deferred** in §4.
- [ ] Every ticket V3_1-D01 through V3_1-D03 is **Done** before CI / release sign-off.
- [ ] Every ticket V3_1-CI-01 through V3_1-CI-03 is **Done**.
- [ ] `ForecastabilityFingerprint`, `RoutingRecommendation`, and `FingerprintBundle` exist as typed outputs.
- [ ] `nonlinear_share` is documented and tested against a linear information baseline.
- [ ] `directness_ratio` is kept semantically separate from `nonlinear_share` in code, docs, and examples.
- [ ] The canonical showcase runs on at least four archetypal series.
- [ ] Public example surfaces under `examples/` or equivalent are created or extended for the fingerprint release.
- [ ] Notebook surfaces are created or extended beyond the single showcase and are cross-linked from docs.
- [ ] At least one regression fixture protects routing behavior from silent drift.
- [ ] A small curated real or semi-real routing-quality panel is run and mismatches are documented.
- [ ] README / quickstart includes one Python and one CLI fingerprint-routing example.
- [ ] The release docs state that `0.3.1` is univariate-first / AMI-first and does not include multivariate or conditional-MI extensions.
- [ ] Reviewer comments 2-10 are each traceable to concrete sections in the plan or explicitly deferred.
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
8. Examples + docs + changelog
9. CI + release hygiene
```
