<!-- type: reference -->
# v0.3.3 — Documentation Quality Improvement: Ultimate Release Plan

**Plan type:** Actionable release plan — documentation contract and quality hardening  
**Audience:** Maintainer, reviewer, documentation contributor, Jr. developer  
**Target release:** `0.3.3`  
**Current released version:** `0.3.2`  
**Branch:** `feat/v0.3.3-docs-quality-hardening`  
**Status:** Draft / Proposed  
**Last reviewed:** 2026-04-18  

**Companion refs:**

- [prior draft: v0.3.2 Documentation Quality Improvement Plan](v0_3_2_documentation_quality_improvement_plan.md)
- [v0.3.0 Covariant Informative: Ultimate Release Plan](v0_3_0_covariant_informative_ultimate_plan.md)

**Builds on:**

- implemented `0.3.0` public docs and release notes
- `0.3.1` fingerprint docs additions
- `0.3.2` lagged-exogenous docs additions
- current README / quickstart / public API / implementation-status / theory pages
- existing release-checklist, smoke workflows, and notebook contract discipline

---

## 1. Why this plan exists

After `0.3.0` and the next feature follow-ups, the documentation surface becomes
an actual product interface. It must therefore obey the same discipline as code:

- stable API examples
- version-consistent release narrative
- terminology consistency
- realistic local validation instructions
- no stale status statements or half-closed caveats

The earlier doc plan already identified the correct narrow scope. This ultimate
version brings it to the same execution standard as the implemented `0.3.0` plan.

### Planning principles

| Principle | Implication |
|---|---|
| Docs are part of the contract | Quickstarts and API examples must run against the documented surface |
| Small-scope cleanup release | No new mathematics or feature creep |
| Hexagonal + SOLID respect | Docs must describe the actual boundaries, not hidden shortcuts |
| Single source of truth | version, terminology, and shipped-vs-proposal semantics must not drift |
| Minimum viable QA first | local checks must be usable even without full docs tooling |
| Product professionalism | the repo should read like a maintained package, not an evolving draft |

---

## 2. Repo baseline — what already exists

| Layer | Module / Area | What it provides | Status |
|---|---|---|---|
| **README** | `README.md` | public landing surface | Stable, needs freshness checks |
| **Quickstart / API** | `docs/quickstart.md`, `docs/public_api.md` | user-facing usage contract | Stable, needs sync checks |
| **Status docs** | `docs/implementation_status.md` | implementation-state narrative | Stable, drift-prone |
| **Theory docs** | `docs/theory/**` | mathematical positioning | Stable, terminology-sensitive |
| **Plans** | `docs/plan/**` | roadmap / proposal references | Stable, needs lifecycle clarity |
| **Release metadata** | `pyproject.toml`, `src/forecastability/__init__.py`, `CHANGELOG.md` | version/runtime story | Stable, must stay aligned |
| **Validation tooling** | smoke, notebook contract, CI, release checklist | lightweight QA precedent | Stable |

---

## 3. Work inventory and overlap assessment

| ID | Item | Phase | Overlap with existing | Genuine new work | Status |
|---|---|---:|---|---|---|
| V3_3-DQ-01 | Public API example contract cleanup | 1 | Extends current docs | ensure all user-facing examples import from real supported surfaces | Proposed |
| V3_3-DQ-02 | Release/version narrative alignment | 1 | Extends release-checklist and version docs | unify README, CHANGELOG, runtime metadata, verification banners | Proposed |
| V3_3-DQ-03 | Implementation-status freshness pass | 1 | Extends current status docs | remove stale caveats and intermediate-state text | Proposed |
| V3_3-DQ-04 | Cross-doc terminology normalization | 1 | Extends theory + quickstart docs | one canonical naming policy across repo | Proposed |
| V3_3-DQ-05 | Docs QA baseline | 2 | Builds on existing smoke/check scripts | lightweight repeatable validation path | Proposed |
| V3_3-DQ-06 | Tooling enablement follow-up | 2 | Extends contributor docs | install guidance or explicit optionality for docs tools | Proposed |
| V3_3-DQ-07 | Notebook/doc index hygiene | 2 | Extends docs indexes | ensure walkthrough and example references stay current | Proposed |
| V3_3-DQ-08 | Plan lifecycle labeling | 2 | Extends `docs/plan/**` discipline | distinguish draft / implemented / superseded documents consistently | Proposed |
| V3_3-CI-01 | Docs contract check in CI | 3 | Extends smoke/release checks | rg-based and import-contract validation | Proposed |
| V3_3-CI-02 | Release checklist hardening | 3 | Extends issue template | doc drift assertions before publish | Proposed |
| V3_3-D01 | README / quickstart refresh | 4 | Extends public docs | current examples and routing / lagged-exog surfaces | Proposed |
| V3_3-D02 | Contributor docs refresh | 4 | Extends dev docs | docs QA commands, optional tools, maintenance policy | Proposed |
| V3_3-D03 | Changelog / migration notes | 4 | Release docs | declare docs hardening release cleanly | Proposed |

---

## 4. Current tooling constraint

The earlier draft correctly observed that full docs tooling may be unavailable in a
fresh environment. This plan preserves that reality.

If the environment still lacks tools such as `mkdocs`, `vale`, or `markdownlint`,
this release must not pretend otherwise. It must either:

- document installation clearly, or
- declare the tools optional and provide a lighter viable check path

No contributor-facing doc may prescribe commands that most maintainers cannot run.

---

## 5. Phased delivery

### Phase 1 — Content correctness and contract alignment

#### V3_3-DQ-01 — Public API example contract cleanup

**Goal.** Ensure user-facing examples match the real supported package surface.

**File targets**

- `README.md`
- `docs/public_api.md`
- `docs/quickstart.md`

**Acceptance criteria**

- every import in public docs resolves from the documented stable surface
- no example relies on hidden fallback knowledge
- if helper generators are intentionally not top-level exports, docs say so once and clearly

#### V3_3-DQ-02 — Release/version narrative alignment

**Goal.** Remove version drift and stale verification text.

**File targets**

- `README.md`
- `CHANGELOG.md`
- `docs/public_api.md`
- release banners / verification notes
- `pyproject.toml` and runtime metadata references where relevant

**Acceptance criteria**

- no page claims a version state that conflicts with runtime/package metadata
- "last verified" style wording is intentional and current
- release-checklist references match the actual release target

#### V3_3-DQ-03 — Implementation-status freshness pass

**Goal.** Remove stale "mid-review" wording.

**File targets**

- `docs/implementation_status.md`
- docs indexes
- walkthrough references
- any covariant/fingerprint/lagged-exog status summaries

**Acceptance criteria**

- shipped features are described as shipped
- deferred items are described as deferred, not half-shipped
- no stale caveat survives after it has been resolved or superseded

#### V3_3-DQ-04 — Cross-doc terminology normalization

**Goal.** Enforce one naming policy.

**Canonical policy should include at minimum**

- `cross_ami` as token / code path
- `CrossAMI` in prose when referring to the mathematical idea
- `cross_pami` as shipped method token
- `CrosspAMI` / `pCrossAMI` policy stated once and reused consistently
- `target_only`, `full_mci`, `none`
- `PCMCI-AMI-Hybrid`
- `Forecastability Fingerprint`
- `information_mass`, `information_horizon`, `information_structure`, `nonlinear_share`

**Acceptance criteria**

- terminology policy is documented once and followed repo-wide
- shipped-vs-proposal semantics use the same explanation everywhere

---

### Phase 2 — Docs QA infrastructure

#### V3_3-DQ-05 — Docs QA baseline

**Goal.** Create a lightweight, repeatable docs-validation path.

**File targets**

- contributor docs or dedicated docs QA note
- optional helper script if warranted

**Acceptance criteria**

- includes rg-based broken-term scans
- includes version-string checks
- includes spot verification of documented imports against actual package facade
- is runnable in a normal maintainer environment without special hidden setup

#### V3_3-DQ-06 — Tooling enablement follow-up

**Goal.** Either enable or de-emphasize full docs tooling honestly.

**Acceptance criteria**

- install steps exist for missing tools, or
- docs explicitly state those tools are optional
- no contradiction remains between expected workflow and actual environment

#### V3_3-DQ-07 — Notebook/doc index hygiene

**Goal.** Keep walkthrough and example references current.

**Acceptance criteria**

- walkthrough indexes reference actual notebooks
- example directories and docs cross-links use the real taxonomy
- no orphaned or renamed example paths remain in public docs

#### V3_3-DQ-08 — Plan lifecycle labeling

**Goal.** Make the roadmap readable.

**Acceptance criteria**

- draft / proposed / implemented / superseded labels are consistent
- old plan links are not presented as current implementation truth
- implemented plans are clearly separated from active drafts

---

### Phase 3 — CI / release hygiene

#### V3_3-CI-01 — Docs contract check in CI

**Goal.** Add at least one lightweight docs-quality check to CI.

**Acceptance criteria**

- broken-term and version-drift checks run automatically, or equivalent
- import-contract checks cover public examples
- failures are actionable and low-noise

#### V3_3-CI-02 — Release checklist hardening

**Goal.** Add doc-drift checks to the release path.

**Acceptance criteria**

- release checklist includes version and import-contract checks
- release cannot proceed casually with stale docs state

---

### Phase 4 — Public and contributor doc refresh

#### V3_3-D01 — README / quickstart refresh

**Goal.** Make the public surface read coherently after `0.3.1` and `0.3.2`.

**Acceptance criteria**

- examples reflect current stable flows
- fingerprint and lagged-exogenous surfaces are described consistently
- no outdated caveat shadows the new releases

#### V3_3-D02 — Contributor docs refresh

**Goal.** Make maintenance of docs realistic.

**Acceptance criteria**

- contributor docs include the viable docs QA path
- optional tooling is labeled clearly
- terminology policy and plan lifecycle policy are discoverable

#### V3_3-D03 — Changelog / migration notes

**Goal.** Publish the release as a docs-contract hardening release.

**Acceptance criteria**

- changelog explains that this is a documentation-quality release
- no functional behavior changes are implied unless explicitly true

---

## 6. Non-goals

- adding new statistical methods
- rewriting theory docs for new math
- creating a hosted docs platform
- changing package runtime behavior except where doc contracts expose real bugs
- reopening feature scope from `0.3.0` / `0.3.1` / `0.3.2`

---

## 7. Exit criteria

- [ ] Every ticket V3_3-DQ-01 through V3_3-DQ-08 is either **Done** or explicitly **Deferred** in §3.
- [ ] Every ticket V3_3-CI-01 through V3_3-CI-02 is **Done**.
- [ ] Every ticket V3_3-D01 through V3_3-D03 is **Done**.
- [ ] All user-facing examples import symbols from genuinely supported locations.
- [ ] No documentation page claims a version state that conflicts with runtime/package metadata.
- [ ] `docs/implementation_status.md` is consistent with the current repo.
- [ ] At least one lightweight docs validation path is written down and usable.
- [ ] Missing docs tooling is either installable from project guidance or explicitly documented as optional.
- [ ] Terminology policy is consistent across README, quickstart, public API, theory docs, and plans.

---

## 8. Recommended implementation order

```text
1. Public API contract cleanup
2. Version narrative alignment
3. Implementation-status freshness
4. Terminology normalization
5. Lightweight docs QA path
6. Tooling enablement or de-emphasis
7. Notebook/index/path hygiene
8. CI + release checklist
9. README / contributor docs / changelog refresh
```
