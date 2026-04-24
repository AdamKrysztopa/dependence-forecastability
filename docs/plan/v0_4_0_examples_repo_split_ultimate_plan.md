<!-- type: reference -->
# v0.4.0 — Examples Repository Split: Ultimate Release Plan

**Plan type:** Actionable release plan — repository slimming, sibling examples repo bootstrap, notebook migration
**Audience:** Maintainer, reviewer, documentation contributor, examples-repo maintainer, Jr. developer
**Target release:** `0.4.0` — **library-first slim release**, ships fourth in the 0.3.3 → 0.3.4 → 0.3.5 → 0.4.0 chain
**Current released version:** `0.3.5` (after the docs hardening pass)
**Branch:** `feat/v0.4.0-examples-split`
**Status:** Draft / Proposed
**Last reviewed:** 2026-04-24

**Driver documents:**

- [aux_documents/developer_instruction_repo_scope.md](aux_documents/developer_instruction_repo_scope.md) — primary scope directive
- [v0.3.4 Forecast Prep Contract: Scope Revision (2026-04-24)](v0_3_4_forecast_prep_contract_revision_2026_04_24.md)
- [v0.3.5 Documentation Quality Improvement: Scope Revision (2026-04-24)](v0_3_5_documentation_quality_improvement_revision_2026_04_24.md)

**Companion refs:**

- [v0.3.3 Routing Validation & Benchmark Hardening: Ultimate Release Plan](v0_3_3_routing_validation_benchmark_hardening_plan.md)
- [v0.3.4 Forecast Prep Contract: Ultimate Release Plan](v0_3_4_forecast_prep_contract_ultimate_plan.md) (original; superseded in scope by the v0.3.4 revision)
- [v0.3.5 Documentation Quality Improvement: Ultimate Release Plan](v0_3_5_documentation_quality_improvement_ultimate_plan.md) (original; superseded in scope by the v0.3.5 revision)

---

## 1. Why this plan exists

After v0.3.5 the documentation contract is mechanical, the forecast-prep
contract is stable, and the public API is framework-agnostic. The remaining
piece of the
[reviewer scope directive](aux_documents/developer_instruction_repo_scope.md)
is structural:

> The core repository should avoid becoming notebook-centric. […] Move heavy
> walkthrough notebooks, executed notebook outputs, framework-specific demos,
> benchmark notebooks, and tutorial notebooks that mainly explain downstream
> usage out of the core repo.

v0.4.0 performs that move. It is a **library-first slim release**:

- Every walkthrough and tutorial notebook is migrated to a sibling
  `forecastability-examples` repository.
- The core repository drops the `notebooks/` directory, executed-notebook
  outputs, and notebook-CI plumbing.
- A short forwarding section in `README.md` and a placeholder
  `docs/examples_index.md` page point users at the sibling repo.
- The minor version bumps from `0.3.x` to `0.4.0` to signal the surface
  change. The Python API is **unchanged**.

> [!IMPORTANT]
> v0.4.0 ships **no new statistical methods**, **no new public symbols**,
> and **no new optional dependencies**. Any PR submitted under this plan
> that adds runtime behavior or new science is out of scope and must be
> moved to a separate plan.

### Planning principles

| Principle | Implication |
| --- | --- |
| Library-first surface | Core repo ships package code, scripts, docs, recipes, minimal examples. Notebooks live elsewhere. |
| Framework-agnostic core | The sibling examples repo may pin and use `darts`, `mlforecast`, `statsforecast`, `nixtla`. The core repo continues to forbid them (Invariant E from v0.3.5). |
| Two-repo, one-product | Sibling repo declares `dependence-forecastability` as a runtime dependency from PyPI; it never imports internals. |
| No history loss | Migration preserves notebook git history via `git filter-repo` (or `git subtree split`); the path-rewrite recipe is documented in this plan. |
| Additive Python API | No public symbol is removed or renamed in v0.4.0. The minor bump signals the surface change, not an API break. |
| Mechanical CI | Notebook contract checks in core CI are removed; sibling repo gets its own nbconvert-based CI. |

### Reviewer acceptance block

`v0.4.0` is successful only if all of the following are visible together:

1. **Sibling repo bootstrapped.**
   - A new repository (working name `forecastability-examples`, final name
     decided in EX-D01) exists with its own `README.md`, license,
     `pyproject.toml` (or `requirements.txt`), CI workflow, and a notebook
     index.
   - The sibling repo declares `dependence-forecastability >= 0.4.0` as a
     runtime dependency and pins the framework-side dependencies (`darts`,
     `mlforecast`, optionally `statsforecast`) under its own dev/extras
     groups.
2. **Notebook migration complete.**
   - Every `*.ipynb` formerly under `notebooks/walkthroughs/` and
     `notebooks/triage/` exists in the sibling repo with executed outputs.
   - The migration commit history preserves authorship and dates.
   - The transition banner introduced in v0.3.5 is replaced in the sibling
     copies with a normal landing intro.
3. **Core repo slimmed.**
   - `notebooks/` directory and `outputs/notebook_runs/` directory are
     removed from the core repo.
   - `scripts/check_notebook_contract.py` is removed.
   - The notebook-related CI job (or step) is removed from
     `.github/workflows/ci.yml` and from any other workflow that references it.
   - `pyproject.toml` no longer references notebooks in its sdist/wheel
     include lists.
4. **Minimal showcase decision.**
   - Decision (EX-D02) recorded explicitly in this plan: ship **zero
     notebooks** in the core repo at v0.4.0. The minimal teaching surface is
     `examples/` scripts and `docs/recipes/`.
5. **Forwarding documentation.**
   - `README.md` has a "Tutorials, walkthroughs, and integrations" section
     pointing at the sibling repo URL.
   - New `docs/examples_index.md` lists every migrated notebook with the
     destination URL.
   - `llms.txt` is updated to reflect the new locations.
   - `AGENTS.md` and `.github/copilot-instructions.md` "Start Here" anchors
     drop the notebook entry and add the recipes / examples-index entry.
6. **Public API unchanged.**
   - `git diff v0.3.5..v0.4.0 -- src/forecastability/__init__.py
     src/forecastability/triage/__init__.py docs/public_api.md` shows zero
     functional removals or renames; only additions allowed.
   - Smoke tests in core CI continue to pass with no source changes outside
     packaging and docs.
7. **Versioning.**
   - `pyproject.toml`, `src/forecastability/__init__.py`, README badge, and
     `CHANGELOG.md` agree on `0.4.0`.
   - Tag `v0.4.0` is created and pushed.
8. **Changelog clarity.**
   - `CHANGELOG.md` `0.4.0` entry explicitly labels the release as a
     **library-first slim release** with a short migration note pointing
     users at the sibling repo. The entry includes the rationale link to
     `docs/plan/aux_documents/developer_instruction_repo_scope.md`.

---

## 2. Scope split — what stays, what moves

### 2.1. Stays in the core repo

| Surface | Reason |
| --- | --- |
| `src/forecastability/**` | Library code (unchanged). |
| `tests/**` | Unit, integration, regression tests (unchanged). |
| `scripts/run_*.py`, `scripts/rebuild_*.py` | Deterministic scripts; CI-friendly. |
| `examples/**/*.py`, `examples/**/*.sh`, `examples/**/*.md` | Compact, framework-agnostic examples. |
| `docs/**` (excluding archived notebook entries) | Reference docs, theory, plans, recipes. |
| `docs/recipes/**` | Illustrative external-framework recipes (text only). |
| `configs/**`, `data/**` (raw and processed) | Deterministic-input fixtures and configs. |
| `outputs/{ami_geometry_csv_script,examples,figures,json,reports,tables}/` | Deterministic outputs from `scripts/`. |

### 2.2. Moves to the sibling repo

| Surface | Destination shape |
| --- | --- |
| `notebooks/walkthroughs/*.ipynb` | `walkthroughs/` |
| `notebooks/triage/*.ipynb` | `triage_walkthroughs/` (renamed for clarity) |
| `outputs/notebook_runs/**` | `outputs/notebook_runs/` |
| Any framework-fitting demo | `recipes/{darts,mlforecast,nixtla}/` |
| The originally-planned `05_forecast_prep_to_models.ipynb` (never landed in core) | `walkthroughs/05_forecast_prep_to_models.ipynb` (created fresh in the sibling repo) |

### 2.3. Boundary contracts between the two repos

- The sibling repo `import`s only from `forecastability` and
  `forecastability.triage`. It never reaches into `forecastability.services`,
  `forecastability.use_cases`, `forecastability.utils`,
  `forecastability.adapters`, or `forecastability.diagnostics`.
- The sibling repo CI installs `dependence-forecastability` from PyPI, never
  via path or git URL except for pre-release smoke tests on a feature branch.
- The core repo never depends on the sibling repo, runtime or otherwise.

---

## 3. Repo baseline — what already exists

| Layer | Path | Note |
| --- | --- | --- |
| Walkthroughs | `notebooks/walkthroughs/{00..04}_*.ipynb` (multiple variants) | Migrated in EX-MIG-01 |
| Triage walkthroughs | `notebooks/triage/{01..06}_*.ipynb` | Migrated in EX-MIG-01 |
| Notebook outputs | `outputs/notebook_runs/**` | Migrated then removed |
| Notebook contract | `scripts/check_notebook_contract.py` | Removed in EX-CR-04 |
| Notebook CI | step in `.github/workflows/ci.yml` (and possibly `smoke.yml`) | Removed in EX-CI-01 |
| Notebook references in docs | `docs/notebooks/`, `docs/quickstart.md`, `README.md` | Rewritten in EX-D02 / EX-D03 |
| Pyproject include rules | `pyproject.toml` `[tool.hatch.build.targets.{sdist,wheel}]` | Updated in EX-PKG-01 |

---

## 4. Feature inventory

| ID | Feature | Phase | Description | Status |
| --- | --- | ---: | --- | --- |
| EX-D01 | Sibling repo naming and bootstrap | 1 | Decide repo name (`forecastability-examples` recommended), create the repo, add license, README, CI scaffolding | Proposed |
| EX-D02 | Decide minimum notebook count in core | 1 | Recorded decision: zero notebooks in core at v0.4.0 | Proposed |
| EX-MIG-01 | Notebook migration with history | 2 | Use `git filter-repo` or `git subtree split` to migrate `notebooks/` and `outputs/notebook_runs/` to the sibling repo with history preserved | Proposed |
| EX-MIG-02 | Sibling repo nbconvert CI | 2 | Add a workflow that executes notebooks against PyPI-installed `dependence-forecastability >= 0.4.0` | Proposed |
| EX-MIG-03 | Pin framework deps in sibling repo | 2 | Sibling repo `pyproject.toml` declares `darts`, `mlforecast`, optionally `statsforecast`, `nixtla` under dev/extras | Proposed |
| EX-CR-01 | Remove `notebooks/` | 3 | Delete the directory in the core repo on the v0.4.0 branch | Proposed |
| EX-CR-02 | Remove `outputs/notebook_runs/` | 3 | Delete the directory and verify no script writes there | Proposed |
| EX-CR-03 | Remove notebook references from docs | 3 | Drop notebook callouts from `README.md`, `docs/quickstart.md`, `docs/notebooks/`, `llms.txt`, `AGENTS.md`, `.github/copilot-instructions.md` | Proposed |
| EX-CR-04 | Remove `scripts/check_notebook_contract.py` | 3 | Delete the script and any tests referencing it | Proposed |
| EX-CI-01 | Remove notebook CI plumbing | 3 | Drop notebook steps/jobs from `.github/workflows/{ci,smoke}.yml`; verify green | Proposed |
| EX-PKG-01 | Update packaging metadata | 3 | Update `pyproject.toml` sdist/wheel include lists to drop `notebooks/`; verify with `uv build` | Proposed |
| EX-D03 | Forwarding section in README and `docs/examples_index.md` | 4 | New section in README; new index page listing every migrated notebook with destination URL | Proposed |
| EX-D04 | Update llms.txt and start-here anchors | 4 | Drop notebook anchor; add recipes/examples-index anchor | Proposed |
| EX-D05 | Refresh `docs/implementation_status.md` and `docs/surface_guide.md` | 4 | Reflect the new repo split | Proposed |
| EX-D06 | Update `.github/copilot-instructions.md` and `AGENTS.md` "Start Here" lists | 4 | Replace `notebooks/walkthroughs/...` anchor with `docs/recipes/` and `docs/examples_index.md` | Proposed |
| EX-CHG-01 | CHANGELOG entry for `0.4.0` | 5 | "Library-first slim release" entry with the migration note and rationale link | Proposed |
| EX-R01 | Version bump and tag | 5 | `0.4.0` across `pyproject.toml`, `__init__.py`, README, `CHANGELOG.md`; tag `v0.4.0` | Proposed |
| EX-R02 | PyPI publish | 5 | Trusted Publishing flow as in `docs/plan/pypi_release_plan.md` | Proposed |
| EX-R03 | Sibling repo first release | 5 | Cut `examples-repo` first release pinning `dependence-forecastability == 0.4.0` | Proposed |

---

## 5. Phased delivery

### Phase 1 — Decisions and bootstrap

#### EX-D01 — Sibling repo naming and bootstrap

**Recommended name:** `forecastability-examples`.

**Alternatives considered:**

- `dependence-forecastability-recipes` — verbose, but mirrors the PyPI name.
- `forecastability-integrations` — implies first-class adapters; rejected to
  avoid the framework-adapter expectation called out in the
  [reviewer scope directive](aux_documents/developer_instruction_repo_scope.md).
- `forecastability-notebooks` — too narrow; the repo will host markdown
  recipes and scripts as well.

**Decision rule.** If the maintainer or org owner objects to
`forecastability-examples`, fall back to `dependence-forecastability-recipes`.
Record the final choice in `CHANGELOG.md` `0.4.0` "Notes" subsection.

**Scaffolding shipped:**

- `README.md` with installation, quick links, and notebook index.
- `LICENSE` matching the core repo.
- `pyproject.toml` declaring `dependence-forecastability >= 0.4.0` as a
  runtime dependency and `darts`, `mlforecast` as `[project.optional-dependencies]`
  groups (`darts`, `mlforecast`).
- `.github/workflows/notebooks.yml` running `jupyter nbconvert --to notebook
  --execute` over every notebook on each push, against a Python 3.11/3.12
  matrix.
- `walkthroughs/`, `triage_walkthroughs/`, and `recipes/` directory skeletons
  with placeholder `README.md` files.

**Acceptance criteria:**

- The sibling repo exists and is publicly visible.
- Its initial CI run is green (no notebooks present yet — only scaffolding).
- The sibling repo's `pyproject.toml` does not reference any path or git
  install of `dependence-forecastability`.

#### EX-D02 — Minimum notebook count in core

**Decision.** Zero notebooks ship in the core repo at v0.4.0.

**Rationale.** §5 of the reviewer scope directive recommends "at most one
minimal showcase notebook, or no notebooks at all". The core repo already
ships:

- `examples/minimal_python.py`
- `examples/minimal_covariant.py`
- `examples/forecasting_triage_first.py`
- `examples/minimal_cli.sh`
- the showcase scripts under `scripts/`
- `docs/quickstart.md`
- `docs/recipes/forecast_prep_to_external_frameworks.md` (added in v0.3.4)

Together these cover the teaching surface that one minimal notebook would
have covered, while remaining diff-friendly and CI-friendly.

**Acceptance criteria:** `find . -name '*.ipynb' -not -path './.venv/*'`
returns the empty set on the v0.4.0 release tag.

### Phase 2 — Migration

#### EX-MIG-01 — Notebook migration with history

**Recipe (recommended — `git filter-repo`):**

```bash
# In a fresh clone of the core repo
git clone https://github.com/<owner>/dependence-forecastability.git \
  forecastability-examples-migration
cd forecastability-examples-migration
git filter-repo \
  --path notebooks/ \
  --path outputs/notebook_runs/ \
  --path-rename notebooks/walkthroughs/:walkthroughs/ \
  --path-rename notebooks/triage/:triage_walkthroughs/
git remote add examples git@github.com:<owner>/forecastability-examples.git
git push examples main
```

**Recipe (alternative — `git subtree split`):** documented in the
sibling repo's `CONTRIBUTING.md`. Less precise on path renames; reserved
for environments where `git filter-repo` is unavailable.

**Acceptance criteria:**

- `git log --follow walkthroughs/00_air_passengers_showcase.ipynb` in the
  sibling repo shows the original commit history with original authors and
  dates.
- The core repo on `main` is **not** modified by this migration step. The
  core-side deletion happens later in EX-CR-01 on the `feat/v0.4.0-examples-split`
  branch.

#### EX-MIG-02 — Sibling repo nbconvert CI

**File:** `.github/workflows/notebooks.yml` (in the sibling repo).

**Job:** install `dependence-forecastability` and the `[darts]` /
`[mlforecast]` extras (defined in the sibling repo's `pyproject.toml`),
then `jupyter nbconvert --to notebook --execute --inplace` every notebook,
fail on any cell error.

**Acceptance criteria:**

- The job runs green on PR and on push to main.
- Notebook execution time is bounded by a per-notebook 15-minute timeout
  (override in the workflow as needed).

#### EX-MIG-03 — Pin framework deps in sibling repo

The sibling repo pins compatible major-version ranges for `darts`,
`mlforecast`, and (optionally) `statsforecast` and `nixtla`. The core repo
remains framework-free.

**Acceptance criteria:**

- `grep -r "darts\|mlforecast\|statsforecast\|nixtla" sibling-repo/pyproject.toml`
  returns hits.
- `grep -rn "darts\|mlforecast\|statsforecast\|nixtla" core-repo/{src,examples,scripts,tests}`
  returns nothing (Invariant E from v0.3.5 still holds).

### Phase 3 — Core repo slimming

#### EX-CR-01 — Remove `notebooks/`

```bash
git rm -r notebooks/
```

**Acceptance criteria:** the directory is gone; `pytest -q` and the
docs-contract job both pass.

#### EX-CR-02 — Remove `outputs/notebook_runs/`

```bash
git rm -r outputs/notebook_runs/
```

Verify no script under `scripts/` writes into that path.

#### EX-CR-03 — Remove notebook references from docs

Update at minimum:

- `README.md` — remove "Notebooks" section and any walkthrough callout.
- `docs/quickstart.md` — drop notebook links.
- `docs/notebooks/` — delete or repurpose to "Notebooks moved" stub.
- `llms.txt` — drop notebook anchor; add recipes anchor.
- `AGENTS.md` — drop the notebook entry from "Navigation Order".
- `.github/copilot-instructions.md` — drop the notebook entry from
  "Start Here".

#### EX-CR-04 — Remove `scripts/check_notebook_contract.py`

Also drop tests that import it and any docs (`docs/maintenance/`) that
describe it. Update `docs/plan/v0_3_5_documentation_quality_improvement_revision_2026_04_24.md`
to note that the transition-banner sub-check is retired in v0.4.0 (no
notebooks remain).

#### EX-CI-01 — Remove notebook CI plumbing

Drop the notebook steps from `.github/workflows/ci.yml` and `.github/workflows/smoke.yml`.
Verify the `docs-contract` job retains its five sub-checks (the
`--no-framework-imports` rule still applies and continues to forbid framework
imports inside the core repo).

#### EX-PKG-01 — Update packaging metadata

Update `pyproject.toml` `[tool.hatch.build.targets.sdist]` and
`[tool.hatch.build.targets.wheel]` exclude/include lists so that the sdist
and wheel artifacts no longer reference `notebooks/`. Run
`uv build && tar -tzf dist/dependence_forecastability-0.4.0.tar.gz | grep -i notebook`
and confirm zero hits.

### Phase 4 — Forwarding documentation

#### EX-D03 — Forwarding section and examples index

Add to `README.md` a "Tutorials, walkthroughs, and integrations" section
pointing at the sibling repo URL. Create `docs/examples_index.md` listing
every migrated notebook with its destination URL.

#### EX-D04 — `llms.txt` and start-here anchors

Update `llms.txt`, `AGENTS.md` "Navigation Order", and
`.github/copilot-instructions.md` "Start Here" so that the canonical entry
points are now:

- `README.md`
- `docs/quickstart.md`
- `docs/public_api.md`
- `docs/recipes/forecast_prep_to_external_frameworks.md`
- `docs/examples_index.md`
- `examples/minimal_python.py`
- `examples/minimal_covariant.py`

(The `notebooks/walkthroughs/00_*.ipynb` anchor is removed.)

#### EX-D05 — Refresh status and surface docs

Update `docs/implementation_status.md` and `docs/surface_guide.md` to reflect
the new two-repo shape. Both files end with a one-line statement: "Tutorials
and integrations live in the [forecastability-examples](https://github.com/example/forecastability-examples)
repository."

#### EX-D06 — Agent surfaces

The `.github/copilot-instructions.md` and `AGENTS.md` updates land here
(see also the corresponding repo-rules patches landed alongside the v0.3.4
revision).

### Phase 5 — Release

#### EX-CHG-01 — `CHANGELOG.md` entry

```markdown
## [0.4.0] - 2026-XX-XX

### Changed

- **Library-first slim release.** All walkthrough and tutorial notebooks have
  moved to the dedicated [forecastability-examples](https://github.com/example/forecastability-examples)
  sibling repository. The Python API is unchanged; the minor version bump
  signals the surface change. Rationale: see
  [docs/plan/aux_documents/developer_instruction_repo_scope.md](docs/plan/aux_documents/developer_instruction_repo_scope.md).

### Removed

- `notebooks/` directory.
- `outputs/notebook_runs/` directory.
- `scripts/check_notebook_contract.py` and the corresponding CI step.
- All notebook anchors from `README.md`, `llms.txt`, `AGENTS.md`, and
  `.github/copilot-instructions.md`.

### Added

- `docs/examples_index.md` listing the migrated notebooks with destination URLs.
- "Tutorials, walkthroughs, and integrations" section in `README.md` pointing
  at the sibling repo.
```

#### EX-R01..R03 — Versioning, publish, sibling release

Standard release flow per `docs/plan/pypi_release_plan.md`. The sibling repo
cuts its first release immediately after PyPI publication, pinning
`dependence-forecastability == 0.4.0`.

---

## 6. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Notebook history loss during migration | Use `git filter-repo` with `--path-rename` and verify with `git log --follow` before the core-side deletion. |
| Sibling repo CI flakiness due to framework version churn | Pin `darts` and `mlforecast` to compatible major-version ranges in the sibling repo; refresh on a quarterly cadence in the sibling repo, never in core. |
| Users following stale README links | Keep `docs/notebooks/` as a one-page stub for at least one release after v0.4.0, with a single-line "moved to [URL]" note. |
| `git filter-repo` unavailable in maintainer environment | Document the `git subtree split` fallback in the sibling repo `CONTRIBUTING.md`. |
| Sibling repo accidentally importing core internals | Add a small CI lint in the sibling repo: `grep -rn "from forecastability\.\(services\|use_cases\|utils\|adapters\|diagnostics\)"` returns zero hits. |

---

## 7. Out of scope

- Any change to the public Python API of `dependence-forecastability`.
- Adding any new optional extra to the core repo.
- Adding any new notebook to the core repo.
- Maintenance of the framework-side (`darts`, `mlforecast`, …) versions
  beyond what the sibling repo declares.

---

## 8. Cross-references

- [aux_documents/developer_instruction_repo_scope.md](aux_documents/developer_instruction_repo_scope.md) — driver document.
- [v0.3.4 Forecast Prep Contract: Scope Revision (2026-04-24)](v0_3_4_forecast_prep_contract_revision_2026_04_24.md).
- [v0.3.5 Documentation Quality Improvement: Scope Revision (2026-04-24)](v0_3_5_documentation_quality_improvement_revision_2026_04_24.md).
- [pypi_release_plan.md](pypi_release_plan.md).
