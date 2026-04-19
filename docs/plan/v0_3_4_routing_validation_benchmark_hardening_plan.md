<!-- type: reference -->
# v0.3.4 — Routing Validation & Benchmark Hardening: Ultimate Release Plan

**Plan type:** Actionable release plan — validation and calibration hardening for routing surfaces  
**Audience:** Maintainer, reviewer, Jr. developer  
**Target release:** `0.3.4`  
**Current released version:** `0.3.3`  
**Branch:** `feat/v0.3.4-routing-validation-hardening`  
**Status:** Draft / Proposed  
**Last reviewed:** 2026-04-18  

**Companion refs:**

- [v0.3.1 Forecastability Fingerprint & Model Routing: Ultimate Release Plan](v0_3_1_forecastability_fingerprint_model_routing_plan.md)
- [v0.3.2 Lagged-Exogenous Triage: Ultimate Release Plan](v0_3_2_lagged_exogenous_triage_ultimate_plan.md)
- [v0.3.3 Documentation Quality Improvement: Ultimate Release Plan](v0_3_3_documentation_quality_improvement_ultimate_plan.md)

**Builds on:**

- implemented `0.3.0` triage surfaces
- `0.3.1` fingerprint and routing policy layer
- `0.3.2` lagged-exogenous sparse lag hand-off
- `0.3.3` cleaned docs contract
- current regression-fixture and smoke-test discipline

---

## 1. Why this plan exists

Once the package starts recommending model families from fingerprints, the next risk is
not architectural — it is **overconfidence**.

A routing layer that looks elegant but is weakly benchmarked can quietly become the least
trustworthy part of the repo. This release therefore hardens the decision policy with:

- broader synthetic panels
- curated real-series archetypes
- threshold calibration
- confidence labeling
- regression protection against silent routing drift

This is not new theory. It is **evidence and policy hardening**.

### Planning principles

| Principle | Implication |
|---|---|
| Validation before expansion | Better-calibrated routing beats more routing rules |
| Hexagonal + SOLID | benchmark generation, policy evaluation, and rendering stay separated |
| Family-level humility | recommendations are model-family guidance, not one-true-model claims |
| Confidence must be earned | labels should come from rule stability and benchmark evidence |
| Regression visibility | routing drift must be intentional, not accidental |
| Product trust | this release strengthens credibility more than feature count |

---

## 2. Validation design — what must be tested

### 2.1. Synthetic archetype expansion

The four canonical `0.3.1` classes are necessary but not sufficient.
Add harder classes:

- strong seasonality with noise
- weak seasonality near threshold
- nonlinear but low-mass signal
- structural-break process
- long-memory / slow-decay process
- mediated-structure process with low directness
- exogenous-driven process consuming sparse lag map from `0.3.2`

### 2.2. Real-series archetype panel

Curate a small, version-controlled set of real-world series archetypes, for example:

- classical monthly seasonal demand
- trend + holiday-style periodicity
- noisy industrial signal with weak persistence
- nonlinear or regime-like series if available under suitable licensing

This release does not need huge data coverage. It needs **representative archetypes**.

### 2.3. Policy calibration

Routing policies from `0.3.1` should be tested against expected family suitability.
This is not full model benchmarking across the universe; it is sanity calibration.

### 2.4. Confidence labels

Confidence labels should depend on evidence such as:

- separation from thresholds
- consistency across nearby parameter settings
- agreement between profile shape and routing policy
- benchmark stability

### 2.5. Failure surface analysis

Define where routing should abstain or downgrade confidence:

- near-threshold mass
- unstable structure label
- contradictory directness / nonlinearity signals
- conflicting exogenous and univariate stories
- short samples or insufficient informative horizons

---

## 3. Repo baseline — what already exists

| Layer | Module / Area | What it provides | Status |
|---|---|---|---|
| **Fingerprint outputs** | `0.3.1` typed fingerprint + routing bundle | routing-ready summary | Assumed stable |
| **Lagged-exog outputs** | `0.3.2` sparse lag map | exogenous hand-off surface | Assumed stable |
| **Synthetic helpers** | existing benchmark generators | deterministic test data precedent | Stable |
| **Regression discipline** | frozen fixtures and rebuild scripts | drift visibility precedent | Stable |
| **Examples / notebooks** | showcase pattern | user-facing validation stories | Stable |
| **CI / release** | smoke + notebook contract + release checklist | hygiene baseline | Stable |

---

## 4. Feature inventory and overlap assessment

| ID | Feature | Phase | Overlap with existing | Genuine new work | Status |
|---|---|---:|---|---|---|
| V3_4-F00 | Validation result models | 0 | Extends typed-result patterns | `RoutingValidationCase`, `RoutingValidationBundle`, `RoutingPolicyAudit` | Proposed |
| V3_4-F01 | Expanded synthetic benchmark panel | 1 | Builds on existing synthetic generators | harder archetypes and expected-family metadata | Proposed |
| V3_4-F02 | Real-series validation panel | 1 | New small curated dataset layer | lightweight representative real-series panel | Proposed |
| V3_4-F03 | Policy audit service | 1 | Builds on `0.3.1` routing service | benchmark evaluation, threshold stress checks, abstention checks | Proposed |
| V3_4-F04 | Confidence calibration service | 1 | Extends routing semantics | deterministic confidence scoring / downgrade rules | Proposed |
| V3_4-F05 | Validation orchestration use case | 2 | Follows existing use-case pattern | `run_routing_validation()` | Proposed |
| V3_4-F06 | Regression fixtures and drift protection | 3 | Extends current fixture discipline | routing policy audit fixtures | Proposed |
| V3_4-F07 | Benchmark report generation | 4 | Extends showcase/reporting pattern | markdown / JSON validation report and summary plots | Proposed |
| V3_4-CI-01 | Validation smoke test | 5 | Extends smoke workflow | quick policy audit run | Proposed |
| V3_4-CI-02 | Release checklist hardening | 5 | Extends release template | routing validation pass required before policy changes | Proposed |
| V3_4-D01 | Validation theory / policy doc | 6 | New docs | how routing confidence is earned and when it abstains | Proposed |
| V3_4-D02 | Changelog and policy notes | 6 | Release docs | evidence-hardened routing release narrative | Proposed |

---

## 5. Domain contracts — MANDATORY FIRST STEP

### 5.1. Typed result models

**File:** `src/forecastability/utils/types.py`

```python
class RoutingValidationCase(BaseModel, frozen=True):
    """One benchmark validation case for routing policy."""

    case_name: str
    source_kind: str
    expected_primary_families: list[str]
    observed_primary_families: list[str]
    confidence_label: str
    passed: bool
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class RoutingPolicyAudit(BaseModel, frozen=True):
    """Aggregate audit of routing policy over a panel."""

    total_cases: int
    passed_cases: int
    downgraded_cases: int
    abstained_cases: int
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class RoutingValidationBundle(BaseModel, frozen=True):
    """Composite output from routing validation orchestration."""

    cases: list[RoutingValidationCase]
    audit: RoutingPolicyAudit
    metadata: dict[str, str | int | float] = Field(default_factory=dict)
```

### 5.2. Acceptance criteria

- validation outputs are typed and serializable
- confidence labels and abstentions are explicit
- benchmark evidence can be reported without notebook-specific logic

---

## 6. Benchmark panels — MANDATORY BEFORE CALIBRATION

### 6.1. Expanded synthetic panel

Required families:

- white noise
- AR(1)
- seasonal
- nonlinear mixed
- weak seasonal near threshold
- structural break
- long-memory decay
- mediated / low-directness
- exogenous-driven sparse-lag process

### 6.2. Real-series panel

Requirements:

- small
- legally usable
- version-controlled or reproducibly downloadable
- each case tagged with expected broad routing family, not a single exact model

### 6.3. Acceptance criteria

- every case has an expected-family metadata tag
- every case has documented caveats
- synthetic and real panels are both used in validation

---

## 7. Phased delivery

### Phase 0 — Validation contracts and panels

#### V3_4-F00 — Validation result models

**Acceptance criteria**

- additive typed outputs exist
- no coupling to plotting or notebook code

#### V3_4-F01 — Expanded synthetic panel

**Acceptance criteria**

- deterministic by seed
- expected-family metadata defined
- harder edge cases included

#### V3_4-F02 — Real-series panel

**Acceptance criteria**

- curated and documented
- small enough for CI-adjacent smoke subsets
- representative enough to challenge routing rules

---

### Phase 1 — Policy hardening services

#### V3_4-F03 — Policy audit service

**Goal.** Evaluate routing policy over benchmark panels.

**Acceptance criteria**

- compares expected vs observed family sets
- records passes, failures, abstentions, downgrades
- exposes policy brittleness near thresholds

#### V3_4-F04 — Confidence calibration service

**Goal.** Make confidence labels evidence-based.

**Acceptance criteria**

- deterministic downgrade rules exist
- abstention conditions are explicit
- contradictory signal patterns reduce confidence rather than being ignored

---

### Phase 2 — Orchestration

#### V3_4-F05 — `run_routing_validation()`

**Goal.** Provide a clean validation use case.

**Acceptance criteria**

- returns `RoutingValidationBundle`
- can run on synthetic-only or mixed panels
- can emit summary artifacts for release review

---

### Phase 3 — Regression and drift protection

#### V3_4-F06 — Validation regression fixtures

**Acceptance criteria**

- fixture rebuild script exists
- routing policy drift is visible
- intentional policy changes require fixture refresh + changelog note

---

### Phase 4 — Reports and showcases

#### V3_4-F07 — Benchmark report generation

**File targets**

- `scripts/run_routing_validation_report.py` — new
- optional markdown/JSON outputs
- optional summary plots

**Acceptance criteria**

- produces a compact report
- highlights failures, abstentions, low-confidence cases
- suitable for release review and LinkedIn-quality repo communication

---

### Phase 5 — CI / release hygiene

#### V3_4-CI-01 — Validation smoke test

- quick synthetic policy audit in CI

#### V3_4-CI-02 — Release checklist hardening

- any routing policy change requires validation report review

**Acceptance criteria**

- validation smoke path stays lightweight
- release checklist prevents silent routing-policy drift

---

### Phase 6 — Documentation

#### V3_4-D01 — Validation / confidence doc

Must explain:

- how routing confidence is computed
- when the system abstains or downgrades
- why family-level humility is intentional

#### V3_4-D02 — Changelog and policy notes

Document the evidence-hardened routing semantics.

---

## 8. Non-goals

- exhaustive benchmarking across all model libraries
- automatic hyperparameter tuning tournaments
- replacing model evaluation with routing policy
- overclaiming benchmark evidence as universal truth
- adding brand-new dependence metrics in this release

---

## 9. Exit criteria

- [ ] Every ticket V3_4-F00 through V3_4-F07 is either **Done** or explicitly **Deferred** in §4.
- [ ] Every ticket V3_4-CI-01 through V3_4-CI-02 is **Done**.
- [ ] Every ticket V3_4-D01 through V3_4-D02 is **Done**.
- [ ] synthetic and real validation panels both exist and are documented.
- [ ] confidence labels are evidence-based and regression-protected.
- [ ] abstention / downgrade conditions are explicit in code and docs.
- [ ] at least one compact validation report is generated for release review.
- [ ] no public docs claim routing is universally correct or equivalent to full benchmarking.

---

## 10. Recommended implementation order

```text
1. Validation result types
2. Expanded synthetic panel
3. Real-series panel
4. Policy audit service
5. Confidence calibration rules
6. Validation use case
7. Regression fixtures
8. Report generation
9. CI + release checklist
10. Docs + changelog
```
