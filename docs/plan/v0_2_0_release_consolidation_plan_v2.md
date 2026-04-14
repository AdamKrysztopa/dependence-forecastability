<!-- type: reference -->
# dependence-forecastability — Release 0.2.0 Consolidation Plan v2

**Plan Type:** Actionable release plan  
**Audience:** Maintainer, reviewer, Jr. developer  
**Target Release:** `0.2.0`  
**Status:** Proposed  
**Target Window:** 2–3 weeks from now, aim for **mid-May 2026**  
**Primary Goal:** Fix structure, examples, docs, packaging, and release engineering so the package feels production-ready, maintainable, and professional.  
**Non-Goal:** No new mathematical features or new diagnostic families in this release.  

---

## 1. Release intent

This release is a **consolidation release**, not a feature release.

The package already exists on PyPI and publishing is already automated. The real gaps are:
- source layout clarity
- duplication across examples, scripts, and notebooks
- documentation drift
- root README positioning
- standard CI for PRs and pushes
- stronger release validation and artifact hygiene

This plan keeps the project aligned with the current multi-paper triage direction while preserving the useful deterministic core and minimizing unnecessary public breakage.

---

## 2. Release decision

### Recommended version
- Preferred: **`0.2.0`**
- Fallback: **`0.1.1`** only if all public imports, CLI behavior, and documented usage remain backward-compatible

### Recommendation rationale
Use `0.2.0` if the internal reorganization causes any of the following:
- public import path changes
- changed CLI output or options
- renamed scripts referenced in docs
- notebook updates that require users to follow a new primary path

---

## 3. Scope boundaries

### In scope
- Source tree cleanup
- Examples/scripts/notebooks cleanup
- Documentation sync
- README rewrite
- CI/CD hardening
- Release validation
- Packaging hygiene
- Templates and repository professionalism upgrades

### Out of scope
- New diagnostics
- New mathematical methods
- New agent features
- New API surfaces beyond what is required for cleanup and consistency
- Deep performance optimization unless needed to stabilize CI or examples

---

## 4. Current-state summary

### Already implemented
- PyPI package exists
- Trusted publishing exists
- release/publish workflows exist
- typed package marker exists (`py.typed`)
- deterministic triage core exists
- docs/plan structure already exists and should remain the planning style baseline

### Partially implemented / inconsistent
- multi-paper positioning in README exists, but is not yet sharp enough
- docs coverage is broad, but not consistently aligned with the current code structure
- examples and scripts contain overlap
- notebooks are useful, but there is no single obvious canonical walkthrough path

### Missing or weak
- standard CI workflow for PRs/pushes
- artifact smoke tests from built distributions
- clean module map documentation
- clear maintenance guide
- issue/PR templates and dependency hygiene automation

---

## 5. Definition of done for 0.2.0

Release `0.2.0` only when all conditions below are true:

- `import forecastability` works
- documented public imports still work or are explicitly deprecated and documented
- canonical CLI smoke test passes from installed wheel
- examples/scripts/notebooks each have a clear role
- a single canonical walkthrough path exists
- README clearly presents the package as a **multi-paper deterministic triage and analytical toolkit**
- docs match the actual code structure and current API
- PR CI exists and is required
- build, test, lint, type-check, and wheel smoke all pass before release
- release notes and changelog are updated

---

## 6. Phase plan overview

| Phase | Title | Duration | Status |
|---|---:|---:|---|
| 0 | Preparation | 1 day | In progress |
| 1 | Source layout cleanup | 2–3 days | Completed |
| 1.5 | Remove compatibility shims | 0.5–1 day | Completed |
| 2 | Examples and scripts cleanup | 1–2 days | Completed |
| 3 | Notebook rationalization | 0.5 day | Completed |
| 4 | Documentation-code alignment | 2 days | Completed |
| 5 | README total renovation | 1 day | Completed |
| 6 | CI/CD and repository infrastructure | 1–2 days | Completed |
| 7 | Testing and final validation | 1 day | In progress |
| 7.5 | Unified showcase runner follow-on | 1–2 days | Completed |
| 8 | Release execution | 0.5 day | Proposed |

---

## Phase 0 — Preparation

**Objective:** Freeze release intent, create branch, and establish the release baseline.

**Status:** In progress

### Tasks
- [x] Create release branch:
  ```bash
  git checkout -b release-0.2.0-cleanup
  ```
- [x] Update `CHANGELOG.md` at the top:
  ```markdown
  ## [0.2.0] - YYYY-MM-DD
  ### Changed
  - Major source layout cleanup (hexagonal architecture preserved)
  - Examples/scripts/notebooks reorganized and de-duplicated
  - Full documentation sync with current code
  - README total renovation (multi-paper triage focus)
  - CI/CD hardened for PyPI releases
  ```
- [x] Run dependency sync and confirm the repo installs cleanly:
  ```bash
  uv sync --dev
  ```
- [x] Create a release tracker document:
  - `docs/plan/release_0_2_0_tracking.md`
- [x] Add a section in the tracker with three buckets:
  - Implemented
  - In progress
  - Not started
- [x] Freeze the supported product surfaces for this release:
  - deterministic core
  - CLI
  - HTTP API
  - agent layer
  - dashboard
  - transport/MCP layer
- [x] Define public-surface compatibility expectations in the tracker.

### Acceptance criteria
- [x] Branch exists
- [x] Changelog scaffold exists
- [x] `uv sync --dev` completes cleanly
- [x] Release tracker exists and includes implementation status buckets
- [ ] Maintainer approves the public-surface freeze

---

## Phase 1 — Fix “Mess in SRC”

**Objective:** Reorganize `src/forecastability/` into a cleaner internal layout without unnecessary public breakage.

**Status:** Completed

### Architectural intent
Preserve the hexagonal direction already present in the repo, but reduce the flat-root sprawl. Keep re-export compatibility where needed.

### Target root contents
Keep only these modules at `src/forecastability/` root, plus existing subpackages that are still valid:
- `__init__.py`
- `extensions.py`
- `models.py`
- `exog_benchmark.py`

### File moves
#### Create `src/forecastability/utils/` and move:
- [x] `aggregation.py`
- [x] `config.py`
- [x] `datasets.py`
- [x] `io_models.py`
- [x] `plots.py`
- [x] `reproducibility.py`
- [x] `robustness.py`
- [x] `state.py`
- [x] `types.py`
- [x] `validation.py`

#### Move into `src/forecastability/diagnostics/`
- [x] `diagnostic_regression.py`
- [x] `spectral_utils.py`
- [x] `cmi.py`
- [x] `surrogates.py`

#### Move into `src/forecastability/metrics/`
- [x] `metrics.py`
- [x] `scorers.py`

#### Move into `src/forecastability/pipeline/`
- [x] `pipeline.py`
- [x] `analyzer.py`
- [x] `rolling_origin.py`

#### Move into `src/forecastability/reporting/`
- [x] `reporting.py`
- [x] `interpretation.py`

### Public API step
- [x] Update `src/forecastability/__init__.py` to expose only the public API:
  ```python
  from .triage import run_triage, run_batch_triage, TriageRequest

  __version__ = "0.2.0"
  __all__ = ["run_triage", "run_batch_triage", "TriageRequest"]
  ```
- [x] If existing documented public imports must remain available, add thin compatibility re-exports.
- [x] Do **not** delete old import paths immediately if they are used in notebooks, docs, or tests.
- [x] Add deprecation comments only where intentionally planned.

### Refactor mechanics
- [x] Update all imports across `src/`, `tests/`, `examples/`, `scripts/`, `docs/`, and notebooks where needed.
- [x] Use:
  ```bash
  ruff check --fix .
  ruff format .
  ```
- [x] Run manual verification on imports not auto-fixed.
- [x] Add `# TODO: 0.3.0` comments only where future work is explicitly intended.

### Suggested Jr. developer workflow
For each move:
- [x] move implementation
- [x] add compatibility shim if required
- [x] run focused tests
- [x] update docs/import examples
- [x] only then remove dead references

### Acceptance criteria
- [x] `import forecastability` works
- [x] no broken tests caused by module moves
- [x] documented public imports still work, or deprecations are explicit
- [x] package root is materially cleaner
- [x] architectural intent is clearer than before

---

## Phase 1.5 — Remove compatibility shims

**Objective:** Retire root-level shim modules after migration is stable.

**Status:** Completed

**Scope:** Remove shim files in `src/forecastability/` that only re-export moved modules.

**Preconditions:**
- docs/scripts/tests/notebooks import paths are migrated
- full verification is green

### Tasks
- [x] inventory shim modules
- [x] migrate remaining imports to new package paths
- [x] delete shim files
- [x] update `__init__` exports only if needed
- [x] update `docs/code/module_map.md`
- [x] run verification (`ruff`, `ty`, `pytest`)

### Acceptance criteria
- [x] no root-level shim modules remain
- [x] `import forecastability` works
- [x] no broken tests/docs references
- [x] module map reflects shim-free layout

---

## Phase 2 — Clean “Mess in examples and scripts”

**Objective:** Give each repo surface one clear purpose.

**Status:** Completed

### Rules
- `examples/` = minimal user-facing runnable examples
- `scripts/` = maintainer/development utilities
- `notebooks/` = narrative tutorials and walkthroughs

### Examples
- [x] Keep only `examples/triage/` as the curated user-facing example family
- [x] Review for duplication against canonical runners
- [x] Delete or move duplicates into `examples/archive/` (none found; no archive move required)
- [x] If archiving, decide whether archive should remain tracked or be ignored (N/A for examples in this phase)
- [x] Add short purpose statements at the top of each kept example

### Scripts
Keep these as development tools:
- [x] `run_canonical_triage.py`
- [x] `run_benchmark_panel.py`
- [x] `run_exog_analysis.py`
- [x] `rebuild_*_fixtures.py` (both)
- [x] `build_report_artifacts.py`

### Rename for consistency
- [x] Rename:
  - canonical examples runner → `run_canonical_triage.py`

### Archive or remove the rest
- [x] Move obsolete or redundant `run_*` scripts into `scripts/archive/` (tracked)
- [x] Update all references in docs and README
- [x] Update tool/docs command references affected by script renames and moves

### Acceptance criteria
- [x] examples are concise and non-duplicative
- [x] scripts folder has a clear maintainer-only identity
- [x] no broken documentation links after renames
- [x] there is one obvious canonical runner for triage examples

---

## Phase 3 — Handle the extra notebook (“all papers methods for one curve”)

**Objective:** Use notebooks as deliberate showcase surfaces that present the package clearly, promote breadth, and inspire users without turning notebooks into runtime ownership paths.

**Status:** Completed

### Tasks
- [x] Create a **single-curve showcase notebook** anchored on Air Passengers
- [x] Suggested name:
  - `notebooks/walkthroughs/00_air_passengers_showcase.ipynb`
- [x] Make the notebook story-first rather than notebook-as-tooling:
  - one memorable series
  - multiple package surfaces shown from that same series
  - strong visuals, short explanations, clear “why this matters” framing
- [x] Ensure the notebook promotes breadth without becoming the source of truth:
  - `run_triage()`
  - scorer comparison via `ForecastabilityAnalyzer`
  - `run_canonical_example()` plus reporting surface
  - `run_rolling_origin_evaluation()`
  - `run_batch_triage()` for portfolio context
- [x] Add a short “where to go next” section for CLI, API, dashboard, MCP, and agent surfaces
- [x] Update `docs/notebooks/README.md` and README notebook references so the showcase notebook is the first-stop entry point

### Additional required notebook work
- [x] Keep the two-family notebook taxonomy (`walkthroughs/`, `triage/`)
- [x] Do **not** introduce notebook-local runtime logic or a third long-lived archive family unless a real historical notebook must be preserved verbatim
- [x] Make the showcase notebook the notebook referenced from README and quickstart docs

### Acceptance criteria
- [x] one obvious showcase notebook exists for first-time users
- [x] notebook index clearly explains showcase vs deep-dive roles
- [x] Air Passengers notebook reads like a product demonstration, not a maintenance artifact

---

## Phase 4 — Make documentation follow the code

**Objective:** Align docs with the cleaned source layout and actual API.

**Status:** Completed

### Tasks
- [x] Audit `docs/` for pages that describe obsolete single-paper AMI-only API paths
- [x] Move stale pages into `docs/archive/` or delete when safe
- [x] In `docs/triage_methods/*.md` and `docs/theory/*.md`, replace outdated references to individual `fX_*` function entry points with the unified API where appropriate
- [x] Update `docs/code/module_map.md` to reflect the new `src/` layout
- [x] Add:
  - `docs/maintenance/developer_guide.md`
- [x] Seed `developer_guide.md` from existing acceptance/planning docs and current repo practices
- [x] Add a doc coverage matrix:
  - `docs/maintenance/doc_coverage_matrix.md`
- [x] For major docs, add a small line such as:
  - `Last verified for release 0.2.0`

### Required search sweep
- [x] Use grep or equivalent to catch stale names and paths:
  ```bash
  grep -R "old_function_name" docs/
  grep -R "run_canonical_triage" docs/
  grep -R "examples/archive" docs/
  ```

### Documentation hierarchy target
- README = landing page
- quickstart = first practical path
- public API docs = authoritative public contract
- theory docs = math and interpretation
- notebooks = tutorial narrative layer
- archive docs = retained historical material only

### Acceptance criteria
- [x] docs point to real modules, real scripts, and real notebooks
- [x] no dead links in key docs
- [x] module map matches the actual source layout
- [x] developer guide exists and is useful for a new contributor

---

## Phase 5 — Total README renovation

**Objective:** Turn the root README into a sharp, professional landing page.

**Status:** Completed

### README direction
The README should present the package as:

> **Deterministic pre-model triage toolkit for time series**

It should clearly say that the project started from Catt’s AMI paper, but has become a broader **multi-paper triage and analytical toolkit**.

### Replace the README with this structure
- [x] Title and one-line positioning
- [x] Short mission paragraph
- [x] Key features list
- [x] Quick install
- [x] Quickstart code block
- [x] Link row:
  - Installation
  - Quickstart
  - All diagnostics
  - Architecture
  - Papers
- [x] “Why this instead of just Catt’s AMI?” section
- [x] Support-surface matrix
- [x] Short docs map
- [x] badges

### Required content elements
- [x] Keep or improve the good quickstart block already present
- [x] Remove or shorten the long paper-baseline explanation from the root page and move detail to `docs/theory/`
- [x] Fix markdown and LaTeX rendering issues
- [x] Add badges:
  - PyPI
  - Python version
  - License
  - CI status
- [x] Explicitly state the pivot to multi-paper triage
- [x] Keep agent layer, HTTP API, and CLI framed as optional surfaces over the deterministic core

### Acceptance criteria
- [x] a first-time visitor understands the package within one minute
- [x] README no longer feels like an internal memo
- [x] README clearly distinguishes foundation vs extensions
- [x] README links send users into one canonical learning path

---

## Phase 6 — CI/CD for releases + repository infrastructure

**Objective:** Add the missing standard CI and complete the release engineering story.

**Status:** In progress

### Important clarification
PyPI publishing is **already implemented**. This phase is about what is still missing:
- standard CI for PRs/pushes
- pre-commit hygiene
- config completeness
- templates and automation around repository maintenance

### Standard CI
- [x] Create `.github/workflows/ci.yml`
- [x] Trigger on push and PR to `main`
- [x] Run:
  - tests
  - ruff
  - mypy or current type-check command
  - build

### Release workflow tightening
- [x] Update `publish-pypi.yml` to trigger only from a release tag such as `v0.2.0`
- [x] Use the preferred build path consistently:
  - `uv build` + trusted publishing, or
  - current equivalent if already aligned
- [x] Ensure release job depends on green CI where possible

### Pre-commit
- [x] Add `.pre-commit-config.yaml`
- [x] Install locally:
  ```bash
  pre-commit install
  ```
- [x] Include hooks such as:
  - ruff
  - black if still used, otherwise do not duplicate formatter responsibility
  - mypy if practical
  - check-toml
  - end-of-file-fixer
  - trailing-whitespace

### Project config hardening
- [x] Review and complete config sections in `pyproject.toml`:
  - `[tool.ruff]`
  - `[tool.mypy]`
  - `[tool.pytest.ini_options]`
- [x] Add `[project.urls]` if incomplete:
  - GitHub
  - Issues
  - Documentation
  - PyPI

### Repository professionalism
- [x] Add Dependabot config
- [x] Add issue templates
- [x] Add PR template
- [ ] Add GitHub topics (GitHub UI only — cannot be automated via files):
  - `time-series`
  - `forecasting`
  - `mutual-information`
  - `triage`
  - `diagnostics`

### Acceptance criteria
- [x] PR CI exists and runs on every push/PR to `main`
- [x] release workflow is more explicit and safer
- [x] pre-commit exists and is usable
- [x] project metadata feels complete and professional
- [x] `docs/releases/automated_release_pipeline.md` written — documents how to use the full pipeline

---

## Phase 7 — Testing and final validation

**Objective:** Validate the hardened canonical runner and close the remaining repo-level release gate.

**Status:** In progress

The recent canonical runner hardening is implemented and validated. The full repo-wide release gate is not yet closed.

### Tasks
- [x] Parallelize the canonical runner at dataset level while preserving deterministic artifact write order
- [x] Validate the default mixed mode: bands for core canonical examples, descriptive mode for extended financial series
- [x] Keep an explicit `--full-bands` option for all-dataset significance runs
- [x] Emit the merged panel summary figure and deterministic human-readable summary/recommendation output
- [x] Validate a default canonical run in about 100s on the recent release-check pass
- [ ] Run the full test suite
- [x] Run the hardened canonical runner on the default path
- [x] Build package locally:
  ```bash
  uv build
  ```
- [ ] Create a clean environment and install from `dist/`
- [ ] Smoke-test:
  - package import
  - `run_triage`
  - CLI help
- [ ] Update `docs/quickstart.md` and `README.md` if any API details changed during cleanup
- [ ] Run a release checklist against the built wheel and sdist
- [ ] Confirm no debug `print()` statements or obsolete `.env` assumptions remain in production code

### Recommended smoke commands
```bash
python -c "import forecastability; print(forecastability.__all__)"
forecastability --help
```

### Acceptance criteria
- [x] canonical runner hardening is validated for the default path and the explicit full-bands control surface
- [x] merged panel summary artifacts and deterministic recommendation output exist
- [x] recent validation shows the default canonical run completing in about 100s
- [ ] full test suite passes
- [ ] built artifacts install cleanly
- [ ] smoke tests pass from installed artifacts
- [ ] quickstart instructions are verified, not theoretical
- [ ] repo-wide Phase 7 release gate is explicitly closed

---

## Phase 7.5 — Unified showcase runner follow-on

**Objective:** Scope the next step toward a single showcase runner without expanding the immediate Phase 7 hardening change set.

**Status:** Completed

This phase delivers a single showcase runner that applies every diagnostic surface the package exposes to the Air Passengers series and summarises all results with a holistic LLM narrative. Full notebook parity remains out of scope for Phase 7 hardening.

### Tasks
- [x] Design a unified showcase/all-method runner that can execute the methods surfaced in the Air Passengers showcase notebook from one entry point
- [x] Produce separate per-method figures as well as merged comparison figures across methods
- [x] Add a deterministic but human-sounding summary/recommendation surface across methods
- [x] Run agentic interpretation and expose it - show it as bonus - translation of hard topics to human language. We must show-off a little with agentic part.
- [x] Define notebook-parity acceptance criteria explicitly instead of treating parity as already covered by Phase 7
- [x] Document

### Acceptance criteria
- [x] one showcase runner covers the intended multi-method surface
- [x] both separate and merged method-comparison figures are generated
- [x] summary and recommendation output reads like a human-facing showcase while remaining deterministic
- [x] full notebook parity is tracked as follow-on scope, not implied by Phase 7 hardening

---

## Phase 8 — Release

**Objective:** Execute the release in a repeatable, low-risk manner.

**Status:** Proposed

### Tasks
- [ ] Update version in `pyproject.toml`
- [ ] Update version in `src/forecastability/__init__.py`
- [ ] Finalize `CHANGELOG.md`
- [ ] Tag and push:
  ```bash
  git tag v0.2.0
  git push --tags
  ```
- [ ] Let CI publish to PyPI
- [ ] Create GitHub release using changelog excerpt
- [ ] Verify PyPI page rendering after publish
- [ ] Verify install commands from a fresh environment
- [ ] Announce through selected channels

### Acceptance criteria
- [ ] tag exists
- [ ] release workflow completes successfully
- [ ] PyPI page renders correctly
- [ ] GitHub release notes are clear and useful

---

## 7. Bonus quick wins for 0.2.0

These are small but high-value polish items.

- [ ] Confirm `py.typed` remains included
- [ ] Add or complete `[project.urls]` in `pyproject.toml`
- [ ] Add GitHub topics
- [ ] remove stray debug output from production paths
- [ ] remove obsolete `.env` references from production-facing code or docs
- [ ] review Python classifiers and add 3.13 only if verified
- [ ] add or verify branch protection rules
- [ ] add CI status badge after `ci.yml` is live

---

## 8. Jr. developer execution order

The Jr. developer should implement in this order:

1. [x] Phase 0 — Preparation
2. [x] Phase 6 — CI/CD baseline first
3. [x] Phase 1 — Source layout cleanup
4. [x] Phase 2 — Examples and scripts cleanup
5. [x] Phase 3 — Notebook rationalization
6. [x] Phase 4 — Documentation sync
7. [x] Phase 5 — README renovation
8. [ ] Phase 7 — Final validation
9. [x] Phase 7.5 — Unified showcase runner follow-on
10. [ ] Phase 8 — Release

### Why this order
- CI should exist before major refactors land
- source cleanup should happen before docs rewrite
- docs and README should reflect final structure, not intermediate structure

---

## 9. Maintainer review checkpoints

The maintainer should review at these gates:

### Gate A — After Phase 0
- [ ] confirm scope
- [ ] confirm version target
- [ ] confirm compatibility expectations

### Gate B — After Phase 1
- [ ] confirm module layout
- [ ] approve compatibility shims
- [ ] reject unnecessary public changes

### Gate C — After Phases 2–4
- [ ] confirm the canonical learning path
- [ ] confirm docs hierarchy
- [ ] confirm archive decisions

### Gate D — Before release
- [ ] confirm README messaging
- [ ] confirm release notes
- [ ] confirm CI and artifact smoke quality

---

## 10. Explicit implementation status section

This section is intentionally included so it can be copied into a tracking file and updated during execution.

### Implemented
- [x] Package published to PyPI
- [x] Trusted publishing exists
- [x] release/publish workflow exists
- [x] deterministic core exists
- [x] typed package marker exists
- [x] standard CI workflow for PRs/pushes
- [x] issue/PR templates and Dependabot
- [x] source-layout cleanup (Phase 1 + 1.5)
- [x] examples and scripts de-duplicated (Phase 2)
- [x] canonical showcase notebook validated end-to-end (Phase 3)
- [x] documentation aligned to live package, script, notebook, and artifact surfaces (Phase 4)
- [x] README rewritten to separate package quickstart from repository workflow (Phase 5)
- [x] docs maintenance guide and doc coverage matrix added
- [x] canonical runner hardening validated: dataset-level parallel execution, mixed default mode, merged panel summary artifacts, deterministic recommendation output, and explicit `--full-bands` support

### Partially implemented
- [ ] repo-wide release artifact smoke validation and installed-wheel smoke checks (Phase 7)

### Not started
- [ ] Phase 8 release execution

### Completed in Phase 7.5
- [x] `scripts/run_showcase.py` — unified showcase runner for Air Passengers covering **all ten** diagnostic surfaces:
  - M1 `run_triage` — deterministic fast triage with classification
  - M2 `run_canonical_example` — full AMI/pAMI pipeline with significance bands
  - M3 `ForecastabilityAnalyzer` — multi-scorer AMI vs pAMI comparison
  - M4 `run_rolling_origin_evaluation` — rolling-origin benchmark (skippable)
  - F1 `ForecastabilityProfile` — informative horizons, peak horizon, model-now guidance
  - F2 `TheoreticalLimitDiagnostics` — theoretical ceiling vs achieved performance
  - F3 `PredictiveInfoLearningCurve` — predictive information learning curve, plateau detection
  - F4 `SpectralPredictabilityResult` — spectral entropy, PSD-based predictability score
  - F5 `LargestLyapunovExponentResult` — experimental LLE, chaos indicator (EXPERIMENTAL)
  - F6 `ComplexityBandResult` — permutation entropy, spectral entropy, complexity band
- [x] Per-method figures for all 10 surfaces saved to `outputs/figures/showcase/`
- [x] Merged 4×3 comparison figure: `showcase_merged.png`
- [x] Human-readable markdown report with sections for all 10 methods: `outputs/reports/showcase/showcase_report.md`
- [x] `ShowcaseExplanation` — holistic LLM interpretation of ALL diagnostics via `--agent` flag with `key_findings`, `unified_recommendation`, `narrative`, `caveats`; graceful fallback when API key absent

---

## 11. Final recommendation

Ship this as **0.2.0** and treat it as the release that makes the project look deliberate.

The core mathematical value is already strong enough. The main bottleneck is not another method. It is repository shape, user path, and release confidence.

That is exactly what this plan addresses.
