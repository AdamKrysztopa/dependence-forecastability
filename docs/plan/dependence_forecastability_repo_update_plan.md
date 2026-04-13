<!-- type: reference -->
# Post-Cleanup Docs, Adoption, and Public Surface Plan

**Companion to:** [../cleaning_plan.md](../cleaning_plan.md), [../pypi_release_plan.md](../pypi_release_plan.md)  
**Builds on:** [../acceptance_criteria.md](../acceptance_criteria.md)  
**Status:** Deferred follow-on plan  
**Last reviewed:** 2026-04-13

> **Activation rule:** keep this plan deferred until the cleanup work that changes public paths, stable facades, and statistical guardrails is complete or explicitly frozen.
>
> **Verification snapshot on 2026-04-13:** `uv run pytest -q -ra` passed, `uv run ruff check .` passed, `uv run ty check` failed with 67 diagnostics. This plan assumes activation only after all three gates are green and repo-shape churn is over.

---

## Why this plan exists

The repo no longer needs another broad "repo update" memo.

What it needs after cleanup is a narrower follow-on plan that makes the cleaned repository:

- easier to adopt,
- easier to evaluate,
- easier to navigate,
- easier to integrate against,
- and less likely to overclaim what is stable or scientific.

This plan is therefore **not** an architecture plan and **not** a release-mechanics plan.

It is a **post-cleanup docs and public-surface plan** for discoverability, evaluator guidance, integrator guidance, and release-facing wording alignment.

---

## Scope boundary with adjacent plans

| Plan | Owns | Does not own |
|---|---|---|
| **This plan** | docs landing page, diagnostics index, surface guide, golden path, implementation status, limitations, public API guidance, wording consistency across docs | notebook migration, adapter extraction, import relocation, boundary enforcement, build/upload automation |
| [cleaning_plan.md](../cleaning_plan.md) | notebook taxonomy and migration, hexagonal realignment, typed ports, ingress guardrails, docs truth-sync to the cleaned structure, architecture enforcement, `ty` recovery | post-cleanup evaluator guidance and integrator-facing docs polish |
| [pypi_release_plan.md](../pypi_release_plan.md) | distribution name, `pyproject.toml` metadata, release-scope freeze, PyPI landing/install flow, artifact validation, TestPyPI/PyPI, Trusted Publishing | non-release docs IA and evaluator guidance |

---

## Entry criteria

Do not activate this plan until the following are true:

- `cleaning_plan.md` work that changes public notebook paths, stable facades, or docs references is complete or explicitly frozen.
- `cleaning_plan.md` statistical guardrails and surface caveats are already settled, especially ingress validation and significance policy.
- Preferred public entry points are stable enough that `run_triage()`-level guidance will not be rewritten again immediately.
- PyPI release Phase 1 identity decisions are complete or frozen:
  - distribution name,
  - first-release scope,
  - canonical metadata wording.
- If this plan is allowed to touch the first screen of `README.md`, the PyPI release work that owns install-flow hardening must already be done.
- `uv run pytest -q -ra`
- `uv run ruff check .`
- `uv run ty check`

---

## Messaging guardrails

All outputs from this plan must preserve the wording constraints below.

- Deterministic outputs are authoritative. CLI, API, notebooks, MCP, and agents are access or narration layers around the same numeric core.
- AMI remains the paper-aligned, horizon-specific foundation. Do not collapse horizons before triage or interpretation.
- pAMI remains a project extension and approximate direct-dependence diagnostic. Do not describe it as exact conditional mutual information or a causal proof.
- In rolling-origin evaluation, diagnostics are computed on train windows only and forecast scoring on post-origin holdout only. The same leakage boundary applies to exogenous workflows.
- Surrogate significance uses phase-randomized surrogates, requires `n_surrogates >= 99`, and may be unavailable when the series is too short for stable bands.
- "Surrogates not computed" is different from "computed, none significant".
- Largest Lyapunov exponent remains experimental, numerically fragile, and excluded from automated triage or ranking decisions.
- `directness_ratio > 1.0` remains a warning or anomaly boundary, not positive evidence.
- Stability claims must stay surface-specific:
  - deterministic core stable,
  - CLI/API beta unless promoted elsewhere,
  - MCP experimental unless promoted elsewhere,
  - agent runtime experimental unless promoted elsewhere.

Do not introduce wording that implies:

- agents or MCP compute or validate the science,
- pAMI proves direct causality,
- F5 is production-ready,
- or the whole repo is uniformly stable.

---

## Target outcome

After this plan is complete:

- a first-time user can identify the deterministic starting path quickly,
- a reviewer can scan what exists, what is stable, and what the caveats are,
- an integrator can tell what to import without guessing,
- the docs feel like one product surface rather than a loose collection of pages,
- and release-facing wording no longer drifts away from the actual support contract.

---

## Follow-on inventory

| # | Follow-on item | Phase | Primary outputs | Status |
|---|---|---|---|---|
| D1 | Canonical wording freeze | 1 | wording rules reused across docs and public surfaces | ✅ Completed (2026-04-13) |
| D2 | Docs landing page | 1 | `docs/README.md` | ✅ Completed (2026-04-13) |
| D3 | Golden path | 1 | `docs/golden_path.md` | ✅ Completed (2026-04-13) |
| D4 | Diagnostics matrix | 2 | `docs/diagnostics_matrix.md` | ✅ Completed (2026-04-13) |
| D5 | Surface guide | 2 | `docs/surface_guide.md` | ✅ Completed (2026-04-13) |
| D6 | Evidence scan and limitations | 2 | `docs/implementation_status.md`, `docs/limitations.md` | ✅ Completed (2026-04-13) |
| D7 | Public API and release-facing docs sync | 3 | `docs/public_api.md`, aligned docs wording | ✅ Completed (2026-04-13) |

---

## Phased delivery

### Phase 1 - Docs front door and adoption path

> Highest leverage after cleanup. Start only when public surface churn is low.

| Item | Type | Effort |
|---|---|---|
| **D1 - Canonical wording freeze** | Docs policy | S |
| **D2 - Docs landing page** | Docs IA | S |
| **D3 - Golden path** | Onboarding | S-M |

#### D1 - Canonical wording freeze

**Current state.** The project story is broadly correct, but wording still risks drifting between README, docs, release-facing text, and public-surface explanations.

**What to build:**

- Freeze the canonical product line:
  - "A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension."
- Freeze the canonical surface line:
  - "CLI, API, notebooks, MCP, and agents are optional access or narration layers around the same deterministic outputs."
- Freeze the experimental line:
  - "Largest Lyapunov exponent is experimental and excluded from automated triage decisions."
- Freeze the leakage line:
  - "In rolling-origin evaluation, diagnostics are computed on train windows only and scoring on post-origin holdout only."
- Freeze the significance line:
  - "Surrogate significance is optional, conditional on feasible sample size, and requires at least 99 surrogates."

**Where it goes:**

- `docs/README.md`
- `docs/golden_path.md`
- `docs/versioning.md`
- `docs/public_api.md`
- README wording only if the PyPI plan has already frozen the top-level install and landing-page contract

**Acceptance criteria:**

- [ ] touched docs use one product identity
- [ ] touched docs preserve deterministic-first wording
- [ ] touched docs do not overclaim pAMI, F5, or agent/MCP behavior

---

#### D2 - Docs landing page

**Current state.** The docs surface is rich, but there is not yet one short evaluator-friendly landing page that cleanly separates methods, surfaces, and policy docs.

**What to build:**

- Rewrite `docs/README.md` into four explicit zones:
  - start here,
  - scientific methods,
  - operational surfaces,
  - policy / release / architecture
- Link to the canonical diagnostics and surface guides created later in this plan.
- Keep the landing page short enough to scan quickly.

**Acceptance criteria:**

- [ ] a new reader can find the right docs zone in under 30 seconds
- [ ] the page does not mix architecture cleanup details with evaluator guidance
- [ ] the page remains valid after cleanup without transitional caveats

---

#### D3 - Golden path

**Current state.** The repo has many entry points, but the opinionated adoption path is still broader than it should be.

**What to build:**

- Create `docs/golden_path.md`.
- Show the recommended path:
  - run one deterministic example,
  - inspect one triage result,
  - read one interpretation,
  - decide whether to continue into notebooks or API,
  - consider MCP or agent layers only after the deterministic path is clear.
- Reuse the install and package-name decisions already frozen by the PyPI release plan. Do not redefine them here.

**Acceptance criteria:**

- [ ] a serious user can reach first trustworthy output without choosing among many interfaces
- [ ] optional integrations are positioned as later steps, not the default path
- [ ] the page does not invent a second install or release contract

---

#### Phase 1 gate

- `docs/README.md` is a usable landing page
- `docs/golden_path.md` exists
- wording is frozen for the docs touched in this phase
- no banned scientific or stability claims appear in the new pages

---

### Phase 2 - Diagnostics, surfaces, and evaluator scanability

> Focus on discoverability and caveat visibility, not feature changes.

| Item | Type | Effort |
|---|---|---|
| **D4 - Diagnostics matrix** | Docs index | S |
| **D5 - Surface guide** | Surface model explainer | S |
| **D6 - Evidence scan and limitations** | Evaluator guidance | M |

#### D4 - Diagnostics matrix

**What to build:**

- Create `docs/diagnostics_matrix.md` as the single evaluator-facing index for F1-F8.
- For each diagnostic include:
  - feature code,
  - question answered,
  - output shape,
  - stability,
  - caveats,
  - where documented,
  - where demonstrated,
  - when to avoid it.

**Acceptance criteria:**

- [ ] a reviewer can identify the role of every implemented diagnostic from one page
- [ ] experimental diagnostics are visible as experimental
- [ ] the matrix points to both docs and evidence

---

#### D5 - Surface guide

**What to build:**

- Create `docs/surface_guide.md`.
- Explain the already-decided surface model:
  - deterministic core,
  - notebooks,
  - CLI/API,
  - MCP/agents,
  - what most users can safely ignore.
- Keep this as an explanation page, not a promotion-criteria page.

**Acceptance criteria:**

- [ ] one page explains core vs optional vs experimental surfaces
- [ ] the guide matches the current stability policy without redefining it
- [ ] agents and MCP remain clearly downstream of deterministic analysis

---

#### D6 - Evidence scan and limitations

**What to build:**

- Create `docs/implementation_status.md`.
- Create `docs/limitations.md`.
- Add an evidence map that links:
  - theory docs,
  - method docs,
  - examples,
  - notebooks,
  - tests,
  - results summaries where relevant.
- Keep limitations explicit:
  - finite-sample MI caveats,
  - pAMI interpretation limits,
  - predictive-information reliability constraints,
  - LLE instability,
  - adapter/runtime caveats,
  - non-goals.

**Acceptance criteria:**

- [ ] a reviewer can assess maturity without reading source code
- [ ] caveats are easy to find from one limitations page
- [ ] evidence and caveats can be scanned together rather than hunted across the repo

---

#### Phase 2 gate

- `docs/diagnostics_matrix.md` exists
- `docs/surface_guide.md` exists
- `docs/implementation_status.md` exists
- `docs/limitations.md` exists
- diagnostics, caveats, and surface tiers are discoverable from the docs alone

---

### Phase 3 - Public API and release-facing docs sync

> Start only after cleanup has stabilized facades and the PyPI plan has frozen the support contract.

| Item | Type | Effort |
|---|---|---|
| **D7 - Public API and release-facing docs sync** | Integrator guidance | M |

#### D7 - Public API and release-facing docs sync

**Current state.** Integrators still need clearer guidance on which imports are supported, which facades are stable, and which internals should not be pinned against.

**What to build:**

- Create `docs/public_api.md`.
- Define:
  - stable top-level import paths,
  - preferred entry points,
  - discouraged internal imports,
  - adapter boundaries,
  - payload/schema stability notes where relevant.
- Align wording in:
  - `docs/versioning.md`,
  - `docs/code/module_map.md`,
  - `docs/README.md`,
  - README sections that are not owned by the PyPI landing-page flow.
- If the PyPI plan has already frozen release naming and scope, propagate those decisions into docs. Do not decide them here.

**Acceptance criteria:**

- [ ] integrators know what to import without guessing
- [ ] stable facades and unstable internals are clearly separated
- [ ] docs wording matches the frozen support contract
- [ ] no build/upload/release-mechanics work is pulled into this plan

---

#### Phase 3 gate

- `docs/public_api.md` exists
- versioning and public-surface wording are aligned
- the docs tell users what is supported without overclaiming maturity

---

## Exit criteria

This follow-on plan is complete only when:

- [ ] docs have one clear landing page
- [ ] docs have one deterministic golden path
- [ ] docs have one diagnostics matrix
- [ ] docs have one surface guide
- [ ] docs have one implementation-status view
- [ ] docs have one limitations page
- [ ] docs have one public API page
- [ ] touched docs reuse one deterministic-first wording policy
- [ ] evaluator guidance, caveats, and public-surface guidance can be found without reading source code

---

## What this plan explicitly does not cover

- notebook renumbering, migration, or compatibility shims
- adapter extraction, `use_cases/` relocation, or other hexagonal cleanup
- statistical ingress fixes or `ty` debt recovery
- release mechanics: build, check, TestPyPI, PyPI, Trusted Publishing
- choosing the PyPI distribution name or first-release scope
- badge strategy, screenshots, or release-note templates unless a later plan explicitly reactivates them

---

## Recommended activation sequence

1. Finish the structural cleanup and docs truth-sync in `cleaning_plan.md`.
2. Freeze package identity and first-release support language in `pypi_release_plan.md`.
3. Activate this plan for docs landing, evaluator guidance, and integrator guidance.

This plan should own **discoverability, evaluator guidance, and integrator guidance** only.
It should not own **repo-shape truth** or **release mechanics**.
