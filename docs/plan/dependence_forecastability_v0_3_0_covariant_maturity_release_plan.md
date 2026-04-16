# Release Plan v0.3.0 — Covariant Maturity Release

**Target version:** v0.3.0  
**Current released version:** v0.2.0  
**Primary release goal:** raise the **covariant workflow** to a maturity level closer to the current univariate path, while preserving the project’s deterministic, paper-aligned identity.

## Executive thesis

This release should not be framed as “we added three new methods.”

It should be framed as:

> **v0.3.0 makes covariant analysis a first-class workflow, with TE + GCMI + PCMCI+ integrated as richer analytical layers, and with the necessary DevOps/release hardening to ship it credibly.**

That means:

- **Univariate remains the mature reference path**
- **Covariant becomes the next serious workflow**
- **TE + GCMI + PCMCI+ are extensions inside covariant analysis**
- **CI/CD and release quality are mandatory scope, not polish**

This release is about **project maturation**, not just feature accumulation.

---

## Tracking table

| ID | Item | Priority | Scope | Why it is in v0.3.0 | Acceptance signal |
|---|---|---:|---|---|---|
| V3-01 | Isolate covariant F(x) methods | P0 | Domain/service | Covariant logic must become testable, composable, and architecture-clean | Each covariant family runs independently through typed contracts |
| V3-02 | Build canonical covariant facade | P0 | Application layer | Covariant must be a first-class user workflow, not a secondary utility | One orchestration entry point powers notebook, script, and tests |
| V3-03 | Integrate Transfer Entropy | P0 | Covariant enrichment | Add directional information flow beyond pairwise dependence | TE results appear in unified covariant report |
| V3-04 | Integrate GCMI | P0 | Covariant enrichment | Add robust rank/copula-based nonlinear dependence layer | GCMI results appear in unified covariant report |
| V3-05 | Integrate PCMCI+ adapter | P0 | Covariant enrichment | Add causal filtering/graph discovery to reduce spurious drivers | Covariant output includes graph/parent summary |
| V3-06 | Unified covariant summary table | P0 | Outputs/interp | User must see one coherent view, not fragmented methods | CrossAMI/CrosspAMI/TE/GCMI/PCMCI+ summarized together |
| V3-07 | Full covariant walkthrough notebook | P0 | Docs/notebooks | Covariant needs parity in pedagogy with the main univariate notebook | One canonical notebook runs end-to-end |
| V3-08 | Full covariant showcase runner | P0 | Scripts | Covariant needs one reproducible demo command | One stable script emits artifacts and summary |
| V3-09 | Strengthen covariant tests | P0 | QA | New workflow must be product-grade, not demo-grade | Unit, integration, and regression checks pass |
| V3-10 | Release pipeline hardening | P0 | CI/CD | Package must fail fast if covariant surface breaks | Pre-publish gates validate package + covariant examples |
| V3-11 | README/API/status refresh | P1 | Docs | Repo messaging should reflect actual surface maturity | README clearly separates univariate vs covariant |
| V3-12 | PyPI metadata and release-note polish | P1 | Packaging/docs | Publish story should match the real product evolution | Changelog and long description read coherently |

---

## Why this release is needed now

The repo already presents a clear and fairly mature univariate surface through the stable Python facade, while the scripts section still lists `run_exog_analysis.py` as a secondary utility and `run_canonical_triage.py` as the canonical single-series workflow. The notebook path also starts from `00_air_passengers_showcase.ipynb`, reinforcing univariate as the primary teaching path. Meanwhile PyPI is already live at `0.2.0`, published on April 14, 2026, with Trusted Publishing and provenance attached. That means the next step should be **covariant maturity**, not another round of purely internal cleanup.

---

## Architecture mandate

### 1. Preserve hexagonal boundaries
- Domain math and statistical logic must not depend on CLI parsing, notebook code, filesystem details, or plotting.
- New TE/GCMI/PCMCI+ work must enter through ports/adapters or clearly separated internal service interfaces.

### 2. Preserve the user-facing mental model
Top-level workflow language should be:
- **Univariate**
- **Covariant**

Not:
- CrossAMI
- CrosspAMI
- TE
- GCMI
- PCMCI+

Those are internal engines or advanced method layers within covariant analysis.

### 3. Avoid notebook-driven architecture
- Notebook code must consume the package workflow
- It must not become the source of truth
- No logic should exist only inside the notebook

### 4. Keep additive changes safer than disruptive rewrites
- Preserve current stable univariate imports and behavior
- Promote covariant without destabilizing the existing package facade

---

# Phase 1 — Covariant domain isolation

## Goal
Refactor the current covariant/exogenous analysis path into isolated, typed, reusable method families and a clean orchestration layer.

## Required deliverables
- typed result models for covariant analysis
- isolated F(x) family methods
- clean separation of compute vs presentation
- one high-level covariant orchestration facade

## Ticket V3-01.1 — Define typed result contracts
Create or refine models for:
- per-driver dependence metrics
- directionality metrics
- causal-graph outputs
- significance/correction outputs
- final unified covariant summary rows
- artifact bundle / report bundle metadata

**Done when:** notebook, script, and tests all read the same result models.

## Ticket V3-01.2 — Split compute from presentation
Move plotting, markdown formatting, filesystem output, and notebook convenience logic out of computational methods.

**Done when:** core covariant methods return pure typed outputs.

## Ticket V3-01.3 — Isolate F(x) method families
Refactor covariant logic into separate modules/services for:
- data/target/driver alignment
- baseline cross dependence
- partial/directness-aware dependence
- significance/correction layer
- ranking/normalization
- unified summary assembly

**Done when:** each family can be unit-tested independently.

## Ticket V3-01.4 — Add covariant orchestration facade
Add one high-level orchestration entry point, for example:
- `run_covariant_analysis(...)`
or
- `ForecastabilityAnalyzerCovariant`

This facade should:
- validate inputs
- run baseline covariant methods
- optionally run TE/GCMI/PCMCI+
- assemble one unified typed output bundle

**Done when:** notebook, showcase runner, and regression tests all use the same facade.

---

# Phase 2 — Rich covariant analysis layers

## Goal
Add TE + GCMI + PCMCI+ as integrated extensions inside the covariant workflow so covariant analysis reaches a more serious analytical level.

---

## Ticket V3-02.1 — Transfer Entropy integration

### Role in the release
Transfer Entropy should enrich covariant analysis with **directional information flow**, not replace the project’s existing dependence-based logic.

### Implementation direction
- define or reuse a clean interface for conditional mutual information estimation
- implement TE in a way that plugs into the covariant facade
- support deterministic synthetic fixtures for known directional relations
- expose TE results in the unified covariant table

### Acceptance criteria
- TE can be run per driver-target pair
- lag assumptions are explicit
- tests show higher TE in known directional synthetic examples than in null/noise controls
- TE output is visible in notebook + script + summary table

---

## Ticket V3-02.2 — GCMI integration

### Role in the release
GCMI should provide a robust rank/copula-based nonlinear dependence layer that complements CrossAMI/CrosspAMI rather than competes with them.

### Implementation direction
- isolate Gaussian copula transformation utilities
- implement GCMI scorer/service with strong numerical safeguards
- expose both raw score and any interpretation metadata needed downstream
- keep computation pure and reusable

### Acceptance criteria
- monotonic transforms preserve the dependence signal qualitatively
- synthetic tests verify robustness relative to difficult marginals
- GCMI appears in the unified covariant report
- notebook explains when GCMI agrees or disagrees with other metrics

---

## Ticket V3-02.3 — PCMCI+ adapter integration

### Role in the release
PCMCI+ should act as the **causal filtering/discovery layer** in covariant analysis, helping distinguish direct parents from spurious or redundant relationships.

### Implementation direction
- implement as an adapter, not a domain rewrite
- use an external backend where practical
- map outputs into internal graph/result models
- keep the backend behind a clean abstraction

### Acceptance criteria
- adapter produces stable output for deterministic synthetic fixtures
- covariant report can summarize parents/links/lag structure
- the notebook shows cases where pairwise dependence is strong but causal evidence is weaker
- integration does not contaminate the core deterministic package surface

---

## Ticket V3-02.4 — Unified covariant summary table

## Goal
Create one coherent table so users do not need to mentally join five separate outputs.

### Required columns
At minimum:
- target
- driver
- lag or lag summary
- CrossAMI
- CrosspAMI
- TE
- GCMI
- significance / correction result
- PCMCI+ relationship summary
- rank / action priority
- short interpretation tag

### Acceptance criteria
- one table is produced by the facade
- one table is used in the notebook
- one table is exported by the showcase script
- future interpretation layers can consume this table directly

---

# Phase 3 — Canonical covariant notebook

## Goal
Create a covariant notebook with pedagogical quality comparable to the current univariate main walkthrough.

## Recommended file
- `notebooks/walkthroughs/01_covariant_analysis_showcase.ipynb`

If numbering changes for consistency, keep it within the same canonical walkthrough path.

## Required notebook sections

### Section A — Why covariant analysis exists
Explain:
- what “covariant” means in this repo
- when to choose it over univariate
- what target vs driver means
- how this release changes the maturity of the workflow

### Section B — Data setup
Use:
- synthetic data with known direct, indirect, and noise drivers
- optional stable real-data example if suitable
- explicit lag, missing-data, and alignment choices

### Section C — Baseline covariant workflow
Run the high-level facade and show:
- CrossAMI
- CrosspAMI
- significance / ranking
- initial interpretation

### Section D — Rich layers
Show:
- TE results
- GCMI results
- PCMCI+ results
- how they enrich or prune the baseline view

### Section E — Unified interpretation
Show how to read:
- strong direct drivers
- mediated drivers
- redundant drivers
- spurious pairwise associations
- causal candidates deserving modeling attention

### Section F — Reproducible artifacts
Show:
- saved JSON summary
- saved table
- plots
- where artifacts go
- how to rerun

### Acceptance criteria
- top-to-bottom runnable
- comparable instructional quality to the univariate notebook
- no hidden notebook-only logic
- clearly demonstrates why covariant is now a first-class workflow

---

# Phase 4 — Canonical covariant showcase runner

## Goal
Provide one reproducible script that demonstrates the full covariant workflow outside notebooks and is usable in CI smoke tests.

## Recommended file
- `scripts/run_showcase_covariant.py`

Keep `run_exog_analysis.py` for compatibility if needed, but make the new script the canonical covariant entry point.

## Required behavior
The script should:
1. load or generate deterministic example data
2. run the covariant facade
3. emit a concise console summary
4. save unified machine-readable outputs
5. save figures/tables in stable paths
6. exit non-zero on failure

## Required outputs
- unified JSON bundle
- unified CSV/parquet table
- graph or plot artifacts where relevant
- CI-friendly console summary

## Acceptance criteria
- one command demonstrates the full covariant workflow
- stable artifact paths exist
- CI can smoke-test it headlessly
- README can point to exactly one covariant demo command

---

# Phase 5 — Tests and regression quality

## Goal
Treat covariant as product code.

## Unit tests
Add direct tests for:
- target/driver validation
- lag alignment
- isolated F(x) family methods
- TE basic directional behavior
- GCMI invariance/robustness expectations
- unified table assembly
- graph/result model serialization

## Integration tests
Add end-to-end checks for:
- covariant facade
- covariant showcase script
- adapter wiring
- artifact schema contracts

## Regression fixtures
Use deterministic synthetic structures with:
- one strong direct lagged driver
- one mediated driver
- one redundant correlated driver
- one pure noise driver
- one spurious pairwise but filtered-by-causal-layer candidate if possible

## Acceptance criteria
- CI fails on material drift
- covariant outputs have contract-level validation
- rich-layer methods are not only tested indirectly

---

# Phase 6 — README, docs, and status maturity

## Goal
Make the repository messaging reflect the real product shape after v0.3.0.

## README changes
Update the README so the repo is clearly organized around:

1. **Univariate**
2. **Covariant**

Then show that covariant includes:
- baseline cross dependence
- directional layer
- robust nonlinear layer
- causal filtering layer

## Recommended status table after v0.3.0

| Surface | Status |
|---|---|
| Univariate deterministic triage | Stable |
| Covariant deterministic workflow | Beta |
| TE/GCMI/PCMCI+ within covariant workflow | Beta |
| CLI | Beta |
| HTTP API | Beta |
| Dashboard | Beta or Optional, depending on active maintenance |
| Agent narration | Experimental |
| MCP server | Experimental |

## Also update
- quickstart section
- notebook path guidance
- canonical script references
- changelog headline
- docs index “start here” map

### Important packaging note
The project metadata still declares `Development Status :: 3 - Alpha`. Revisit whether that classifier should remain after the v0.3.0 maturity pass, or whether surface-level maturity messaging in docs is enough for now.

---

# Phase 7 — DevOps, CI/CD, and PyPI hardening

## Goal
The release must fail before publication if the new covariant surface is broken.

## Ticket V3-07.1 — Release preflight
Before publish:
- build sdist and wheel
- install from built wheel in a clean environment
- run import smoke tests
- run covariant showcase smoke test
- validate package metadata

## Ticket V3-07.2 — Example contract validation
Extend CI so canonical notebooks and canonical showcase scripts are checked in release-oriented branches.

## Ticket V3-07.3 — Matrix policy
Recommended:
- Python 3.11 required
- Python 3.12 required
- Python 3.13 optional canary if useful, but not a blocker unless support is officially expanded

## Ticket V3-07.4 — Artifact upload on CI
Upload:
- unified covariant JSON
- unified covariant summary table
- selected figures/graph artifacts

## Ticket V3-07.5 — Release checklist automation
Automate checks for:
- changelog entry present
- version/tag consistency
- README quickstart commands still valid
- script/notebook references still exist
- optional dependency group guidance still renders correctly

## Acceptance criteria
- publish pipeline remains trusted-publishing based
- package install is validated, not assumed
- covariant regressions are caught before tag publish

---

# In scope

- isolated covariant F(x) methods
- covariant orchestration facade
- TE integration
- GCMI integration
- PCMCI+ adapter integration
- unified covariant summary table
- canonical covariant notebook
- canonical covariant showcase script
- covariant tests and regression fixtures
- README/status/docs refresh
- CI/CD and PyPI release hardening

# Out of scope

- destabilizing stable univariate imports
- turning the whole project into a generic causal-discovery framework
- broad agentic redesign as the release centerpiece
- large unrelated UI/platform work
- shipping notebook-only logic as package behavior

---

# Branch and milestone proposal

## Branch
- `release/v0.3.0-covariant-maturity`

## Milestones
1. covariant contracts and F(x) isolation
2. TE/GCMI implementation
3. PCMCI+ adapter integration
4. unified covariant table
5. canonical notebook
6. canonical showcase script
7. tests and regression fixtures
8. docs/status refresh
9. release hardening
10. tag and publish

---

# Junior-developer backlog

## Epic A — Covariant core
- [ ] define/refine typed covariant result models
- [ ] isolate target/driver alignment logic
- [ ] isolate baseline covariant metric families
- [ ] isolate ranking/significance logic
- [ ] build one covariant orchestration facade
- [ ] preserve stable univariate behavior

## Epic B — Rich covariant methods
- [ ] implement TE integration behind clean interfaces
- [ ] implement GCMI integration behind clean interfaces
- [ ] implement PCMCI+ adapter integration
- [ ] map rich-layer outputs into shared internal result models
- [ ] add deterministic fixtures

## Epic C — Unified outputs
- [ ] design unified covariant table schema
- [ ] export JSON/table artifacts
- [ ] add short interpretation tags
- [ ] ensure notebook and script use identical output schema

## Epic D — Notebook and showcase
- [ ] create canonical covariant notebook
- [ ] create canonical covariant showcase script
- [ ] add plots/graph outputs
- [ ] validate notebook/script contracts

## Epic E — Release quality
- [ ] add build/install smoke checks
- [ ] add covariant showcase smoke test in CI
- [ ] add release preflight
- [ ] update changelog and README
- [ ] review PyPI metadata/classifiers

---

# Final recommendation

This is the stronger version of the plan.

It does not dilute the project into “just another bag of methods.”  
It matures the product shape:

- univariate remains the stable reference path
- covariant becomes a serious second workflow
- TE + GCMI + PCMCI+ enrich covariant instead of fragmenting it
- DevOps and release discipline make the new surface trustworthy

That is a believable v0.3.0 story and a real maturity step for the project.
