<!-- type: reference -->
# v0.4.0 — Examples Repository Split: Ultimate Release Plan

**Plan type:** Actionable release plan — repository slimming, sibling examples repo bootstrap, notebook migration
**Audience:** Maintainer, reviewer, documentation contributor, examples-repo maintainer, Jr. developer
**Target release:** `0.4.0` — **library-first slim release**, ships fourth in the 0.3.3 → 0.3.4 → 0.3.5 → 0.4.0 chain
**Current released version:** `0.3.6` (after the docs hardening pass)
**Branch:** `feat/v0.4.0-examples-split`
**Status:** Draft / Proposed
**Last reviewed:** 2026-04-28
**Batch 1a landed:** 2026-04-28 — EX-D01 (sibling repo bootstrap at https://github.com/AdamKrysztopa/forecastability-examples), EX-D02 (zero-notebook decision recorded)
**Batch 1b landed:** 2026-04-28 — EX-CPL-02 (`RELEASES.md` index), EX-LOCAL-01 (bootstrap script, code-workspace, `docs/development/local_workspace.md`, `forbid-cross-repo-staging` pre-commit hook)
**Batch 2a landed:** 2026-04-28 — EX-MIG-01 (15 notebooks migrated with `git filter-repo`, history preserved), EX-MIG-02 (nbconvert CI in `notebooks.yml` + `release.yml`), EX-MIG-03 (darts, mlforecast, statsforecast, causal/tigramite, agent/pydantic-ai pinned in sibling `pyproject.toml`), EX-NB-LOCK-01 (`uv.lock` committed, CI uses `--frozen`), EX-NB-MATRIX-01 (python × source two-axis matrix in CI), EX-NB-EXEC-01 (cleared outputs committed; executed notebooks uploaded as CI artifacts), EX-NB-DATA-01 (sibling `data/` populated with vendored CSVs and regression fixtures; `data/README.md` origin table)
**Batch 3a landed:** 2026-04-29 — EX-CR-01 (`notebooks/` removed from core repo), EX-CR-02 (`outputs/notebook_runs/` removed), EX-CR-03 (notebook refs scrubbed from `README.md`, `docs/quickstart.md`, `docs/notebooks/`, `llms.txt`, `AGENTS.md`, `.github/copilot-instructions.md`), EX-CR-04 (`scripts/check_notebook_contract.py` and two notebook contract test files removed; transition-banner sub-check retired)
**Batch 3b landed:** 2026-04-29 — EX-CR-05 (redirect stubs already absent — deleted in the v0.3.5 squash merge `c1890f1`; no inbound links remain; gate satisfied)
**Batch 3c landed:** 2026-04-29 — EX-CI-01 (no notebook steps existed in any workflow; docs-contract five sub-checks intact), EX-PKG-01 (`notebooks/` removed from sdist exclude and stale ruff/ty excludes; `uv build` verified — zero `.ipynb` files in sdist and wheel)

**Driver documents:**

- [aux_documents/developer_instruction_repo_scope.md](../plan/aux_documents/developer_instruction_repo_scope.md) — primary scope directive
- [v0.3.4 Forecast Prep Contract: Ultimate Release Plan](v0_3_4_forecast_prep_contract_ultimate_plan.md) — v0.3.4 shipped; the standalone revision overlay was folded into this ultimate plan and is intentionally absent
- [v0.3.5 Documentation Quality Improvement: Scope Revision (2026-04-24)](v0_3_5_documentation_quality_improvement_revision_2026_04_24.md) — includes the docs reorganization that v0.4.0 inherits and the redirect-stub deletion item (V3_5-DOC-RE-10 → EX-CR-05 below)

**Companion refs:**

- [v0.3.3 Routing Validation & Benchmark Hardening: Ultimate Release Plan](v0_3_3_routing_validation_benchmark_hardening_plan.md)
- [v0.3.4 Forecast Prep Contract: Ultimate Release Plan](v0_3_4_forecast_prep_contract_ultimate_plan.md)
- [v0.3.5 Documentation Quality Improvement: Scope Revision (2026-04-24)](v0_3_5_documentation_quality_improvement_revision_2026_04_24.md)

---

## 1. Why this plan exists

After v0.3.5 the documentation contract is mechanical, the forecast-prep
contract is stable, and the public API is framework-agnostic. The remaining
piece of the
[reviewer scope directive](../plan/aux_documents/developer_instruction_repo_scope.md)
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
| Two-repo, **one-product** UX | Sibling repo declares `dependence-forecastability` as a runtime dependency from PyPI; it never imports internals. **A cross-repo CI handshake (EX-CPL-01) and a shared GitHub Project / `RELEASES.md` index (EX-CPL-02)** keep the two halves coupled at the verification and planning surfaces so the user-visible product still reads as one project. |
| One local checkout, two remotes | The maintainer works in a single parent workspace folder containing both repos as sibling subdirectories. A VS Code multi-root workspace (`forecastability.code-workspace`) opens both at once; an editable install (`uv pip install -e ../dependence-forecastability`) wires the sibling against the local core. CI on the sibling still resolves `dependence-forecastability` from PyPI, so the editable install is a **dev-only** convenience and never leaks into release artifacts (EX-LOCAL-01). |
| Standalone notebook execution | Every migrated notebook executes end-to-end against a freshly cloned sibling repo via `uv sync --frozen && uv run jupyter nbconvert --execute`. Data dependencies, framework version pins, and lockfile reproducibility are explicit (EX-NB-DATA-01, EX-NB-LOCK-01, EX-NB-MATRIX-01). |
| v0.3.4 sprint visibility at launch | The sibling repo's v0.4.0 launch ships at least three notebooks that exercise the just-shipped `ForecastPrepContract` surface (EX-NB-01..03) so the work done in v0.3.4 is visibly demonstrated, not just documented. |
| No history loss | Migration preserves notebook git history via `git filter-repo` (or `git subtree split`); the path-rewrite recipe is documented in this plan. |
| Additive Python API | No public symbol is removed or renamed in v0.4.0. The minor bump signals the surface change, not an API break. |
| Mechanical CI | Notebook contract checks in core CI are removed; sibling repo gets its own nbconvert-based CI matrix on a `(python, source)` cross-product. |

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
     `docs/plan/aux_documents/developer_instruction_repo_scope.md` **and**
     a forward link to the sibling repo's `walkthroughs/05_forecast_prep_to_models.ipynb`
     (EX-NB-01) so the v0.3.4 sprint is visibly cited at v0.4.0 launch.
9. **Cross-repo coupling visible.**
   - The cross-repo CI handshake (EX-CPL-01) is wired and green: the
     sibling repo's `release` workflow runs the full notebook matrix on
     every core release tag and posts a comment on the core release page.
   - A shared GitHub Project / milestone (`v0.4.0 across both repos`) and
     a top-level `RELEASES.md` index in core list paired sibling release
     tags alongside core release tags (EX-CPL-02).
10. **Standalone notebook execution proven.**
    - On a fresh clone of the sibling repo, the documented sequence
      (`uv sync --frozen && uv run jupyter nbconvert --to notebook --execute walkthroughs/*.ipynb triage_walkthroughs/*.ipynb`)
      completes without manual intervention against the pinned core release.
11. **v0.3.4 sprint demonstrated in the sibling repo.**
    - The sibling repo at v0.4.0 launch contains executable notebooks
      `walkthroughs/05_forecast_prep_to_models.ipynb` (EX-NB-01),
      `recipes/contract_roundtrip.ipynb` (EX-NB-02), and
      `walkthroughs/06_triage_driven_vs_naive_on_m4.ipynb` (EX-NB-03).
      All three exercise `forecastability.build_forecast_prep_contract`
      and the `ForecastPrepContract` surface introduced in v0.3.4.
12. **Rich-exogenous causal-rivers showcase landed.**
    - **Framing.** Causal-rivers serves two narrowly scoped purposes in v0.4.0,
      and nothing more:
      1. a **public, citable benchmark dataset** with a graph-verified
         ground-truth causal structure, used as a hand-off-friendly
         multi-driver fixture; and
      2. a **capability demonstration** that the toolkit's deterministic
         lag-and-feature selection (self-lags via `run_triage`; exogenous
         lags and per-driver sparse selection via `run_lagged_exogenous_triage`;
         hand-off via `build_forecast_prep_contract`) recovers the
         graph-verified positives and rejects the negative controls.
      Causal-rivers is **not** a forecasting benchmark in this release, **not**
      a hydrology study, and **not** a paper artefact. The notebook ends at
      the contract; downstream model fitting is illustrative only and
      lives in recipe sub-cells.
    - The core repo ships the framework-agnostic causal-rivers analysis surface
      promoted from the `feat/casual-rivers` branch (EX-CR-CR-01): the new
      `forecastability.extensions` module (`TargetBaselineCurves`,
      `compute_target_baseline_by_horizon`), the deterministic script
      `scripts/run_causal_rivers_analysis.py`, and the YAML config
      `configs/causal_rivers_analysis.yaml`. The two notebooks from that
      branch (`notebooks/03_causal_rivers.ipynb` and the updated
      `notebooks/02_exogenous_analysis.ipynb`) move to the sibling repo as
      `walkthroughs/07_causal_rivers_lag_and_feature_selection.ipynb` (EX-NB-05) and
      `walkthroughs/02_exogenous_analysis.ipynb` respectively.
    - The sibling notebook EX-NB-05 evaluates one downstream target station
      (Unstrut @ 978) against five graph-verified upstream tributaries
      (positives) and three unrelated-basin stations (negative controls),
      using rolling-origin CrossAMI + pCrossAMI at horizons {1, 2, 3, 4, 6, 8, 12}
      on 6-hour resampled data, and ends with a `build_forecast_prep_contract`
      hand-off populated from the per-driver sparse selected lags. The
      notebook's pass/fail assertions test **selection quality** (positives
      recovered, negatives rejected, sparse lag sets non-empty for positives
      only), not forecasting accuracy.
13. **Local two-repo dev workflow proven (EX-LOCAL-01).**
    - A documented `forecastability.code-workspace` multi-root file at the
      parent directory level opens both repos. The sibling repo's
      `pyproject.toml` declares an `[tool.uv.sources]` override that resolves
      `dependence-forecastability` to a local path **only when the
      `FORECASTABILITY_LOCAL_DEV=1` environment variable is set**, and to PyPI
      otherwise. A bootstrap script `scripts/bootstrap_local_workspace.sh` in
      core clones the sibling at the correct relative path, sets up the
      editable install, and verifies that the sibling import surface stays
      within the public API (zero hits for
      `from forecastability\.\(services\|use_cases\|utils\|adapters\|diagnostics\)`).

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
| `notebooks/03_causal_rivers.ipynb` (from `feat/casual-rivers`) | `walkthroughs/07_causal_rivers_lag_and_feature_selection.ipynb` (EX-NB-05) |
| Updated `notebooks/02_exogenous_analysis.ipynb` (from `feat/casual-rivers`) | `walkthroughs/02_exogenous_analysis.ipynb` (replaces any earlier copy) |
| `notebooks/01_canonical_forecastability.ipynb` (from `feat/casual-rivers`) | `walkthroughs/01_canonical_forecastability.ipynb` |

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
| Causal-rivers core surface | `feat/casual-rivers` branch: `src/forecastability/extensions.py` (`TargetBaselineCurves`, `compute_target_baseline_by_horizon`, `compute_k_sensitivity`), `scripts/run_causal_rivers_analysis.py`, `configs/causal_rivers_analysis.yaml`, `tests/test_extensions.py` | Promoted to `main` via EX-CR-CR-01 before any sibling notebook references it |
| Causal-rivers raw data | `data/raw/causal_rivers/product/{rivers_ts_east_germany.csv, rivers_east_germany.p, rivers_meta_east_germany.csv}` (CausalRivers benchmark, dl-de/by-2-0) | Stays in core repo; sibling fetches a deterministic subset via the ported `download_data.py` per EX-NB-DATA-02 |

---

## 4. Feature inventory

Rows are ordered top-to-bottom by `Phase` (0 → 5), then by `Batch`, then by
dependency order within each batch. New rows added during plan revisions are
inserted in their correct phase and batch position rather than appended.

| ID | Feature | Phase | Batch | Description | Status |
| --- | --- | ---: | --- | --- | --- |
| **EX-CR-CR-01** | **Land causal-rivers core surface to `chore/0-4-0-repos-split`** | 0 | 0a | Cherry-pick / rebase the framework-agnostic portion of `feat/casual-rivers` (`src/forecastability/extensions.py`, `tests/test_extensions.py`, `scripts/run_causal_rivers_analysis.py`, `configs/causal_rivers_analysis.yaml`, additive re-exports of `TargetBaselineCurves` and `compute_target_baseline_by_horizon` from `forecastability.__init__`, and the `data/raw/causal_rivers/` raw subset) into `main` **before** any sibling notebook references the new symbols. The notebooks themselves are excluded from this cherry-pick — they migrate via EX-NB-05. Adds the rebuild script `scripts/rebuild_causal_rivers_fixtures.py` and a deterministic regression fixture under `docs/fixtures/extensions/`. | Implemented |
| EX-D01 | Sibling repo naming and bootstrap | 1 | 1a | Decide repo name (`forecastability-examples` recommended), create the repo, add license, README, CI scaffolding | Implemented |
| EX-D02 | Decide minimum notebook count in core | 1 | 1a | Recorded decision: zero notebooks in core at v0.4.0 | Implemented |
| **EX-CPL-02** | **Shared planning surface** | 1 | 1b | GitHub Project board spanning both repos with a `v0.4.0` milestone; new top-level `RELEASES.md` index in core listing sibling release tags alongside core release tags. Fallback when the EX-CPL-01 automated gate is unavailable. | Implemented |
| **EX-LOCAL-01** | **Local two-repo dev workflow** | 1 | 1b | Parent workspace folder layout, `forecastability.code-workspace` multi-root file, `scripts/bootstrap_local_workspace.sh` (clones sibling alongside core and wires the editable install), editable install via `uv pip install -e` (instead of `[tool.uv.sources]` marker — `env_var()` is not a valid PEP 508 marker in this uv version), contributor `docs/development/local_workspace.md` page covering the dual-commit / dual-push loop, and a pre-commit hook in core that warns when changes are staged simultaneously across both repos to prevent accidental cross-repo commits. | Implemented |
| EX-MIG-01 | Notebook migration with history | 2 | 2a | Use `git filter-repo` or `git subtree split` to migrate `notebooks/` and `outputs/notebook_runs/` to the sibling repo with history preserved | Implemented |
| EX-MIG-03 | Pin framework deps in sibling repo | 2 | 2a | Sibling repo `pyproject.toml` declares `darts`, `mlforecast`, optionally `statsforecast`, `nixtla` under dev/extras | Implemented |
| **EX-NB-LOCK-01** | **Lockfile-pinned reproducibility** | 2 | 2a | Commit `uv.lock` in sibling repo; CI uses `uv sync --frozen`; quarterly Dependabot / scheduled refresh PR bumps the lockfile and merges only if the matrix is green. | Implemented |
| **EX-NB-MATRIX-01** | **Two-axis sibling CI matrix** | 2 | 2a | `python ∈ {3.11, 3.12}` × `source ∈ {pinned, unpinned-main}`. `pinned` is a required check (gates merge); `unpinned-main` runs with `continue-on-error: true` to surface upstream framework drift early without blocking PRs. | Implemented |
| EX-MIG-02 | Sibling repo nbconvert CI | 2 | 2a | Add a workflow that executes notebooks against PyPI-installed `dependence-forecastability >= 0.4.0` | Implemented |
| **EX-NB-EXEC-01** | **Execute-on-CI, commit cleared outputs** | 2 | 2a | Sibling `CONTRIBUTING.md` documents: notebooks are committed with cleared outputs; CI runs `nbconvert --to notebook --execute --inplace` and uploads executed notebooks as build artifacts; the sibling `release` workflow publishes executed notebooks as **release assets**. Avoids reintroducing the diff-noise problem that motivated the split. | Implemented |
| **EX-NB-01** | **Sibling notebook `walkthroughs/05_forecast_prep_to_models.ipynb`** | 2 | 2b | Triage → `build_forecast_prep_contract` → hand-off to (a) Darts `LightGBMModel`, (b) MLForecast `LGBMRegressor`, (c) plain sklearn `Ridge` baseline; comparison table on a 12-month tail. Exercises only the public `forecastability` and `forecastability.triage` API on the triage side. Demonstrates the v0.3.4 sprint at v0.4.0 launch. | Implemented |
| **EX-NB-02** | **Sibling recipe `recipes/contract_roundtrip.ipynb`** | 2 | 2b | `ForecastPrepContract.model_dump_json()` → disk → `model_validate_json()` → re-validate against a fresh triage run. Final cell consumes the JSON without importing `forecastability` to demonstrate the framework-agnostic hand-off boundary. | Implemented |
| **EX-NB-03** | **Sibling notebook `walkthroughs/06_triage_driven_vs_naive_on_m4.ipynb`** | 2 | 2b | Comparison study on M4 monthly subset (≤ 200 series): triage-driven `recommended_families` choice vs `SeasonalNaive` baseline. Persists `outputs/m4_routing_comparison.csv`. Comparison studies are explicitly assigned to the sibling repo by [aux_documents/developer_instruction_repo_scope.md §4](../plan/aux_documents/developer_instruction_repo_scope.md). | Implemented |
| **EX-NB-DATA-01** | **Per-notebook data-shipping policy** | 2 | 2c | Sibling `data/README.md` reproduces the per-notebook origin table (§5.4): small public CSVs (Air Passengers, ETTh1 OHT subset) ship in the sibling repo; M4 and causal-rivers fetch via a port of `scripts/download_data.py` cached under `actions/cache@v4`. | Implemented |
| **EX-NB-DATA-02** | **CausalRivers data subsetting policy** | 2 | 2c | Port the causal-rivers fetch path from `scripts/download_data.py` into the sibling repo as `scripts/download_causal_rivers.py`. Subset the released archive to the eight stations enumerated in EX-NB-05, persist a 6h-resampled parquet under `data/causal_rivers/east_germany_8stations_6h.parquet` with a SHA-256 manifest, and cache via `actions/cache@v4` keyed on the manifest hash. The cached parquet is what the notebook loads; the full pickled graph and 15-minute CSV are never shipped or vendored in the sibling repo. License notice (`dl-de/by-2-0`) appears in `data/README.md`. | Implemented |
| **EX-NB-05** | **Sibling notebook `walkthroughs/07_causal_rivers_lag_and_feature_selection.ipynb`** | 2 | 2c | **Capability demo of deterministic lag and feature selection on a public, graph-verified benchmark.** Causal-rivers is treated here strictly as (a) a data source and (b) a multi-driver fixture with ground-truth positives and negatives. Target station: 978 (Unstrut @ Wendelstein). Drivers: five graph-verified upstream tributaries (positives: 979, 1095, 313, 758, 490) and three unrelated-basin stations (negative controls: 67, 71, 99). Pipeline shows the toolkit choosing **self-lags** for the target (via `run_triage`) and **exogenous lags + features** for the drivers (via `run_lagged_exogenous_triage` and `build_forecast_prep_contract`); rolling-origin CrossAMI + pCrossAMI at horizons {1, 2, 3, 4, 6, 8, 12} via `run_exogenous_rolling_origin_evaluation`; horizon-specific target baseline via `compute_target_baseline_by_horizon`. Pass/fail asserts on selection (positives present in `contract.past_covariates`, negatives absent, per-driver `selected_lags` non-empty for positives, empty for negatives). Recipe sub-cells map the resulting contract to Darts `LightGBMModel` and MLForecast `LGBMRegressor` for illustration only — the notebook does **not** report forecast accuracy. | Implemented |
| EX-CR-01 | Remove `notebooks/` | 3 | 3a | Delete the directory in the core repo on the v0.4.0 branch | Implemented |
| EX-CR-02 | Remove `outputs/notebook_runs/` | 3 | 3a | Delete the directory and verify no script writes there | Implemented |
| EX-CR-03 | Remove notebook references from docs | 3 | 3a | Drop notebook callouts from `README.md`, `docs/quickstart.md`, `docs/notebooks/`, `llms.txt`, `AGENTS.md`, `.github/copilot-instructions.md` | Implemented |
| EX-CR-04 | Remove `scripts/check_notebook_contract.py` | 3 | 3a | Delete the script and any tests referencing it | Implemented |
| **EX-CR-05** | **Delete v0.3.5 redirect stubs** | 3 | 3b | Remove the 14 redirect stubs created by V3_5-DOC-RE-04..07. Gated on "no inbound link from any tracked surface remains" (lychee green after stub deletion). Enumerated stub paths: `docs/golden_path.md`, `docs/use_cases_industrial.md`, `docs/architecture.md`, `docs/surface_guide.md`, `docs/results_summary.md`, `docs/limitations.md`, `docs/api_contract.md`, `docs/agent_layer.md`, `docs/observability.md`, `docs/production_readiness.md`, `docs/diagnostics_matrix.md`, `docs/forecast_prep_contract.md`, `docs/implementation_status.md`, `docs/versioning.md`, `docs/wording_policy.md`. | Implemented |
| EX-CI-01 | Remove notebook CI plumbing | 3 | 3c | Drop notebook steps/jobs from `.github/workflows/{ci,smoke}.yml`; verify green | Implemented |
| EX-PKG-01 | Update packaging metadata | 3 | 3c | Update `pyproject.toml` sdist/wheel include lists to drop `notebooks/`; verify with `uv build` | Implemented |
| EX-D03 | Forwarding section in README and `docs/examples_index.md` | 4 | 4a | New section in README; new index page listing every migrated notebook with destination URL | Proposed |
| EX-D04 | Update llms.txt and start-here anchors | 4 | 4a | Drop notebook anchor; add recipes/examples-index anchor | Proposed |
| EX-D06 | Update `.github/copilot-instructions.md` and `AGENTS.md` "Start Here" lists | 4 | 4a | Replace `notebooks/walkthroughs/...` anchor with `docs/recipes/` and `docs/examples_index.md` | Proposed |
| EX-D05 | Refresh `docs/implementation_status.md` and `docs/surface_guide.md` | 4 | 4b | Reflect the new repo split | Proposed |
| **EX-NB-04** | **Bidirectional recipe cross-link** | 4 | 4b | Sibling `recipes/README.md` links forward to executed-notebook release assets and back to the core text recipe at [docs/recipes/forecast_prep_to_external_frameworks.md](../recipes/forecast_prep_to_external_frameworks.md). Core recipe page gains a forward link to EX-NB-01 / EX-NB-02. Mitigates doc-rot risk between the two repos. | Proposed |
| EX-CHG-01 | CHANGELOG entry for `0.4.0` | 5 | 5a | "Library-first slim release" entry with the migration note, rationale link, and a forward link to the sibling repo's v0.3.4 sprint-showcase notebook (EX-NB-01) | Proposed |
| EX-R01 | Version bump and tag | 5 | 5a | `0.4.0` across `pyproject.toml`, `__init__.py`, README, `CHANGELOG.md`; tag `v0.4.0` | Proposed |
| **EX-REL-01** | **Two-repo release dance documented in sibling `RELEASING.md`** | 5 | 5b | Step-by-step: core RC1 → sibling pre-flight against TestPyPI / `git+` source → acceptance gate (sibling matrix green) → core final tag and PyPI publish → sibling pin bump and final tag → cross-repo handshake comment (EX-CPL-01). | Proposed |
| **EX-REL-02** | **TestPyPI / `git+` pre-flight matrix** | 5 | 5b | Sibling pre-flight matrix has a `source` axis with values `testpypi` and `git`. Either green satisfies the EX-REL-01 acceptance gate; both green is preferred. Exercises the actual `pip install` machinery before the irrevocable PyPI publish. | Proposed |
| EX-R02 | PyPI publish | 5 | 5b | Trusted Publishing flow as in `docs/plan/pypi_release_plan.md`; sequenced inside the two-repo release dance (EX-REL-01) | Proposed |
| EX-R03 | Sibling repo first release | 5 | 5b | Cut sibling first release pinning `dependence-forecastability == 0.4.0`; sequenced inside EX-REL-01 | Proposed |
| **EX-CPL-01** | **Cross-repo CI handshake** | 5 | 5b | Sibling repo's `release` workflow listens on `repository_dispatch` (`event_type = core_release`) emitted by core's release workflow. On firing, sibling re-runs the full notebook matrix against the new PyPI artifact and posts a check status / comment back to the core release page. Manual `workflow_dispatch` fallback for outages. | Proposed |

Batches are meant to be implementation handles for later coding-agent requests:
for example, ask to "implement phase 1a" for the naming/bootstrap/minimum-core-notebook
decision batch, "implement phase 1b" for shared planning and the local two-repo
workflow, or "implement phase 4b" for the repo-split status docs and
bidirectional recipe cross-link. Do not start a
later batch until its prerequisite batches are complete, especially when the
work crosses the core/sibling boundary or depends on a released PyPI artifact.

---

## 5. Phased delivery

### Phase 0 — Land causal-rivers core surface to `main`

#### EX-CR-CR-01 — Promote `feat/casual-rivers` framework-agnostic surface

The sibling notebook EX-NB-05 imports two new core symbols
(`TargetBaselineCurves`, `compute_target_baseline_by_horizon`) and runs the
deterministic script `scripts/run_causal_rivers_analysis.py`. Both must exist
on `main` **before** the sibling repo references them. This phase precedes
any migration step.

**Cherry-pick scope** (framework-agnostic, no notebooks):

- `src/forecastability/extensions.py` (whole file).
- `tests/test_extensions.py` (whole file).
- Additive re-export edits in `src/forecastability/__init__.py`:
  `TargetBaselineCurves`, `compute_target_baseline_by_horizon` added to the
  module imports and `__all__` (preserves additive-compatibility invariant).
- `scripts/run_causal_rivers_analysis.py` (whole file).
- `configs/causal_rivers_analysis.yaml` (whole file).
- `data/raw/causal_rivers/product/{rivers_ts_east_germany.csv,
  rivers_east_germany.p, rivers_meta_east_germany.csv}` (raw subset only;
  full benchmark archive is not vendored).
- New rebuild script `scripts/rebuild_causal_rivers_fixtures.py` and a
  deterministic regression fixture under `docs/fixtures/extensions/` covering
  one positive and one negative pair at horizon 4 with `random_state=42`,
  comparing per-horizon AMI / pAMI / CrossAMI floats with `math.isclose`
  (matches the cross-platform-drift convention in user memory).

**Excluded from this cherry-pick** (those move via EX-NB-05):

- `notebooks/01_canonical_forecastability.ipynb`
- `notebooks/02_exogenous_analysis.ipynb`
- `notebooks/03_causal_rivers.ipynb`

**Acceptance criteria:**

- `from forecastability import TargetBaselineCurves, compute_target_baseline_by_horizon`
  resolves on `main`.
- `MPLBACKEND=Agg uv run python scripts/run_causal_rivers_analysis.py` writes
  the documented artifacts under `outputs/{figures,json,tables}/causal_rivers/`
  and exits 0.
- `uv run python scripts/rebuild_causal_rivers_fixtures.py` runs clean and
  the resulting fixture matches the committed snapshot under `math.isclose`.
- `uv run pytest tests/test_extensions.py` is green.
- `docs/public_api.md` gains a one-line entry for the two new symbols under
  the existing extensions block.
- `--no-framework-imports` docs-contract sub-check still passes (no `darts`,
  `mlforecast`, `statsforecast`, `nixtla` import is introduced).

### Phase 1 — Decisions and bootstrap

#### EX-D01 — Sibling repo naming and bootstrap

**Recommended name:** `forecastability-examples`.

**Alternatives considered:**

- `dependence-forecastability-recipes` — verbose, but mirrors the PyPI name.
- `forecastability-integrations` — implies first-class adapters; rejected to
  avoid the framework-adapter expectation called out in the
  [reviewer scope directive](../plan/aux_documents/developer_instruction_repo_scope.md).
- `forecastability-notebooks` — too narrow; the repo will host markdown
  recipes and scripts as well.

**Decision rule.** If the maintainer or org owner objects to
`forecastability-examples`, fall back to `dependence-forecastability-recipes`.
Record the final choice in `CHANGELOG.md` `0.4.0` "Notes" subsection.

**Scaffolding shipped:**

- `README.md` with installation, quick links, notebook index, and an explicit
  "Where to file issues" subsection (mirrored in core `README.md` per
  EX-D03) so contributors know which repo owns which kind of bug.
- `LICENSE` matching the core repo.
- `pyproject.toml` declaring `dependence-forecastability == 0.4.0`
  (exact pin, with an upper bound `< 0.5` on the next development line)
  as a runtime dependency. Framework deps live under
  `[project.optional-dependencies]`:
  - `darts = ["darts>=0.30,<0.36"]`
  - `mlforecast = ["mlforecast>=0.13,<0.16", "lightgbm>=4.3,<5"]`
  - `statsforecast = ["statsforecast>=1.7,<2"]` (optional)
  - `calendar = ["holidays>=0.50,<1"]`
  - `dev = ["jupyter>=1.1", "nbconvert>=7.16", "pytest>=8.4"]`
- **`uv.lock`** committed (EX-NB-LOCK-01).
- `.github/workflows/notebooks.yml` running the EX-NB-MATRIX-01 matrix
  (`python ∈ {3.11, 3.12}` × `source ∈ {pinned, unpinned-main}`) on each
  push, with a per-notebook 15-minute timeout.
- `.github/workflows/release.yml` listening on `repository_dispatch`
  (event_type `core_release`) per EX-CPL-01.
- `walkthroughs/`, `triage_walkthroughs/`, and `recipes/` directory skeletons
  with placeholder `README.md` files (the recipe README implements EX-NB-04).
- `data/` directory with the per-notebook data files from EX-NB-DATA-01
  and a `data/README.md` listing origin and license per file.
- `CONTRIBUTING.md` documenting the execute-on-CI / commit-cleared-outputs
  policy (EX-NB-EXEC-01).
- `RELEASING.md` documenting the two-repo release dance (EX-REL-01).

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

#### EX-LOCAL-01 — Local two-repo development workflow

> [!IMPORTANT]
> Answers the maintainer concern: *"How do I work in one local project but
> commit to two repos?"* The answer is **a parent workspace folder containing
> two sibling git checkouts**, opened together in a VS Code multi-root
> workspace, with a path-based editable install for dev iteration. Each
> commit goes to its own repo's remote; the cross-repo CI handshake
> (EX-CPL-01) and the shared planning surface (EX-CPL-02) keep the two
> halves coordinated. **Submodule, subtree, and workspace-monorepo patterns
> are explicitly rejected** for the reasons recorded in §5 above.

**Filesystem layout (recommended):**

```text
~/projects/papers/forecastability-workspace/   # parent folder, NOT a git repo
├── dependence-forecastability/               # core repo (this one); own .git, own remote
│   └── …
├── forecastability-examples/                 # sibling repo; own .git, own remote
│   └── …
└── forecastability.code-workspace            # VS Code multi-root descriptor
```

A maintainer who already has the core repo cloned at the historical path
(`~/projects/papers/ami`) creates the parent folder, moves the existing
checkout into it, and clones the sibling alongside. The bootstrap script
documented below performs this idempotently.

**Files shipped in the core repo by this item:**

- `scripts/bootstrap_local_workspace.sh` — clones the sibling repo at the
  expected relative path (`../forecastability-examples`), wires the editable
  install (`uv pip install -e .`) inside the sibling's venv, and runs the
  sibling import-surface lint as a smoke test. Idempotent: re-running on an
  already-bootstrapped workspace exits 0 with a "no-op" message.
- `forecastability.code-workspace` (sibling-aware multi-root descriptor) —
  generated next to the core repo and intended to be moved one directory up
  by the bootstrap script. Lists both folders and pre-configures
  `python.analysis.extraPaths` so cross-repo imports resolve in IntelliSense.
- `docs/development/local_workspace.md` — how-to guide covering: (a) initial
  bootstrap, (b) the dual-commit workflow (each `git commit` runs in the
  intended subdirectory; never commit cross-repo from the parent), (c) the
  dual-push workflow (`git push` in each subdirectory hits its own remote),
  (d) when to flip `FORECASTABILITY_LOCAL_DEV` on or off, and (e) the
  pre-commit safeguard described below.
- `.pre-commit-config.yaml` gains a small local hook
  `forbid-cross-repo-staging` that fails when the staging area in the core
  repo simultaneously contains files outside the core repo's tree (paranoia
  catch in case someone runs `git add ../forecastability-examples/...`).

**Files shipped in the sibling repo by this item (specified here, landed in
EX-D01):**

- `pyproject.toml` declares the conditional source override:

  ```toml
  # Default: resolve from PyPI for CI and end users.
  # When FORECASTABILITY_LOCAL_DEV=1, resolve from the sibling path checkout.
  [tool.uv.sources]
  dependence-forecastability = [
      { path = "../dependence-forecastability", editable = true,
        marker = "env_var('FORECASTABILITY_LOCAL_DEV') == '1'" },
  ]
  ```

  This keeps the **release** dependency unchanged
  (`dependence-forecastability == 0.4.0` from PyPI) while letting the
  maintainer flip into editable mode with a single env-var export.
- `CONTRIBUTING.md` documents the same workflow as core's
  `docs/development/local_workspace.md`, mirrored for sibling-side
  contributors.

**Daily dev loop (documented in `docs/development/local_workspace.md`):**

1. `cd ~/projects/papers/forecastability-workspace/dependence-forecastability`
   — make a public-API change, commit, push to core remote.
2. `cd ../forecastability-examples` — `export FORECASTABILITY_LOCAL_DEV=1
   && uv sync` — re-resolves against the local editable core. Update the
   notebook that exercises the new symbol, commit, push to sibling remote.
3. Open a core PR and a sibling PR; link them in each PR description per
   the EX-CPL-02 shared-milestone rule.
4. CI on the sibling re-installs from PyPI (the env-var marker is false on
   GitHub Actions runners by default), so the sibling PR will go red until
   the core release is published. This is by design: it is the same
   chicken-and-egg the EX-REL-01 release dance solves at release time, and
   the local editable install is what unblocks the maintainer in between.

**Acceptance criteria:**

- `bash scripts/bootstrap_local_workspace.sh` run from a freshly cloned
  core repo:
  - clones the sibling at `../forecastability-examples` if absent;
  - generates `forecastability.code-workspace` at the parent level;
  - completes `uv sync` in the sibling with `FORECASTABILITY_LOCAL_DEV=1`
    set, and prints the resolved core install path;
  - runs the sibling import-surface lint
    (`grep -rn "from forecastability\.\(services\|use_cases\|utils\|adapters\|diagnostics\)" walkthroughs triage_walkthroughs recipes`)
    and reports zero hits.
- The pre-commit `forbid-cross-repo-staging` hook fires (and fails) when a
  test commit in the core checkout includes a path outside the core tree.
- Re-running the bootstrap script is a no-op: exit 0, no filesystem changes.

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

**Additional migration steps** (per EX-NB-DATA-01):

- `cp data/raw/air_passengers.csv` into sibling `data/air_passengers.csv`.
- `cp data/raw/etth1_oht_subset.csv` into sibling `data/etth1_oht_subset.csv`.
- Port `scripts/download_data.py` to the sibling repo, scoped to M4 monthly
  and causal-rivers; sibling notebooks `04_routing_validation_showcase.ipynb`,
  `04_screening_end_to_end.ipynb`, `02_exogenous_analysis.ipynb`, and
  `06_triage_driven_vs_naive_on_m4.ipynb` (EX-NB-03) gate on a `_FETCHED`
  marker file.
- For the causal-rivers walkthrough (EX-NB-05): instead of vendoring the full
  `data/raw/causal_rivers/product/` directory in the sibling repo, ship
  `scripts/download_causal_rivers.py` (per EX-NB-DATA-02). The script fetches
  the East Germany subset from the
  [CausalRivers benchmark release](https://github.com/CausalRivers/benchmark/releases/tag/First_release),
  resamples to 6h, restricts to the eight stations enumerated in EX-NB-05,
  and writes a single parquet file `data/causal_rivers/east_germany_8stations_6h.parquet`
  with a SHA-256 manifest. CI caches the parquet via `actions/cache@v4`
  keyed on the manifest hash.

**Acceptance criteria:**

- `git log --follow walkthroughs/00_air_passengers_showcase.ipynb` in the
  sibling repo shows the original commit history with original authors and
  dates.
- The core repo on `main` is **not** modified by this migration step. The
  core-side deletion happens later in EX-CR-01 on the `feat/v0.4.0-examples-split`
  branch.

#### Per-notebook data origin table (consumed by EX-NB-DATA-01)

Reproduced verbatim in sibling `data/README.md` (consumed by EX-NB-DATA-01):

| Notebook | Dataset | Origin | License | Shipped where |
| --- | --- | --- | --- | --- |
| `walkthroughs/00_air_passengers_showcase.ipynb` | Air Passengers (monthly, 1949–1960) | Box & Jenkins | Public domain | Vendored CSV in sibling `data/air_passengers.csv` |
| `walkthroughs/01_canonical_forecastability.ipynb` | Synthetic AR(1) + Lorenz | Generated in-notebook via `forecastability.generate_ar1` and `forecastability.generate_lorenz` | n/a | None |
| `walkthroughs/02_exogenous_analysis.ipynb` | Bike-sharing hourly (UCI), AAPL/SPY log-returns, BTC/ETH log-returns | UCI ML repo + Yahoo Finance + CoinGecko snapshots | UCI: CC BY 4.0; financial snapshots: vendored aggregates only | Vendored aggregates in sibling `data/exogenous_demos/` |
| `walkthroughs/03_etth1_subset.ipynb` | ETTh1 OHT subset | [Informer/ETT release](https://github.com/zhouhaoyi/ETDataset) | CC BY 4.0 | Vendored CSV in sibling `data/etth1_oht_subset.csv` |
| `walkthroughs/04_routing_validation_showcase.ipynb` and `04_screening_end_to_end.ipynb` | M4 monthly subset (≤ 200 series) | [M4 competition](https://github.com/Mcompetitions/M4-methods) | CC BY 4.0 | Fetched + cached via ported `download_data.py` |
| `walkthroughs/05_forecast_prep_to_models.ipynb` (EX-NB-01) | Synthetic via `forecastability.generate_ar1` | n/a | n/a | None |
| `walkthroughs/06_triage_driven_vs_naive_on_m4.ipynb` (EX-NB-03) | M4 monthly subset | as above | CC BY 4.0 | Same cached fetch as row above |
| `walkthroughs/07_causal_rivers_lag_and_feature_selection.ipynb` (EX-NB-05) | CausalRivers East Germany subset (8 stations, 6h-resampled) | [CausalRivers benchmark](https://github.com/CausalRivers/causalrivers), [release](https://github.com/CausalRivers/benchmark/releases/tag/First_release) | dl-de/by-2-0 | Fetched + cached via `scripts/download_causal_rivers.py` (EX-NB-DATA-02) into `data/causal_rivers/east_germany_8stations_6h.parquet` |
| `recipes/contract_roundtrip.ipynb` (EX-NB-02) | Synthetic via `forecastability.generate_ar1` | n/a | n/a | None |

#### EX-NB-05 — CausalRivers as data source + lag/feature-selection capability demo

> [!IMPORTANT]
> **Scope (binding).** Causal-rivers is used here as **(a) a public,
> graph-verified benchmark dataset** and **(b) a fixture for demonstrating
> the toolkit's deterministic self-lag, exogenous-lag, and feature-selection
> capabilities**. It is **not** a forecasting benchmark, **not** a hydrology
> case study, and **not** a paper artefact in this release. The notebook
> ends at the `ForecastPrepContract` hand-off; the two recipe sub-cells
> that follow are illustrative wiring snippets, not an accuracy comparison.

This is the headline capability demo for v0.4.0. It supersedes the
standalone `notebooks/03_causal_rivers.ipynb` from the `feat/casual-rivers`
branch and lifts the analysis on top of the public `forecastability` API.

**Setup cells:**

1. `python scripts/download_causal_rivers.py` (idempotent; cache hit on CI).
2. Load the parquet into a `pandas.DataFrame` indexed by 6h timestamps with
   integer station IDs as columns.

**Pipeline cells (only public API):**

```python
from forecastability import (
    TriageRequest,
    build_forecast_prep_contract,
    compute_target_baseline_by_horizon,
    run_lagged_exogenous_triage,
    run_triage,
)
from forecastability.pipeline import run_exogenous_rolling_origin_evaluation
from forecastability.triage import AnalysisGoal

TARGET_ID = 978
POSITIVES = [979, 1095, 313, 758, 490]   # graph-verified upstream tributaries
NEGATIVES = [67, 71, 99]                  # unrelated Havel basin
HORIZONS = [1, 2, 3, 4, 6, 8, 12]

# 1. Per-pair rolling-origin CrossAMI + pCrossAMI
results = {
    sid: run_exogenous_rolling_origin_evaluation(
        target=ts[TARGET_ID].to_numpy(),
        exog=ts[sid].to_numpy(),
        horizons=HORIZONS,
        n_origins=8,
        n_neighbors=8,
        n_surrogates=99,
        random_state=42,
    )
    for sid in POSITIVES + NEGATIVES
}

# 2. Horizon-specific target baseline (no exogenous)
baseline = compute_target_baseline_by_horizon(
    series_name="unstrut_978",
    target=ts[TARGET_ID].to_numpy(),
    horizons=HORIZONS,
    n_origins=8,
    random_state=42,
    min_pairs_raw=30,
    min_pairs_partial=50,
    n_surrogates=99,
)

# 3. Sparse lagged-exogenous selection across all candidate drivers
lagged_bundle = run_lagged_exogenous_triage(
    target=ts[TARGET_ID].to_numpy(),
    drivers={f"station_{sid}": ts[sid].to_numpy() for sid in POSITIVES + NEGATIVES},
    target_name="unstrut_978",
    max_lag=20,
    n_surrogates=99,
    random_state=42,
)

# 4. Hand-off contract
triage = run_triage(TriageRequest(
    series=ts[TARGET_ID].to_numpy(),
    goal=AnalysisGoal.univariate,
    max_lag=20, n_surrogates=99, random_state=42,
))
contract = build_forecast_prep_contract(
    triage,
    horizon=12,
    target_frequency="6h",
    lagged_exog_bundle=lagged_bundle,
    add_calendar_features=False,
)
```

**Narrative cells must demonstrate:**

- The **two selection capabilities** of the toolkit, side by side:
  - *Self-lag selection* on the target station via `run_triage`: the
    notebook prints `triage.summary.primary_lags` and reports them as the
    AR component the contract will request from any downstream model.
  - *Exogenous lag and feature selection* via `run_lagged_exogenous_triage`
    + `build_forecast_prep_contract`: the notebook prints, per candidate
    driver, the sparse `selected_lags` list and whether the driver landed
    in `contract.past_covariates` or `contract.rejected_covariates`.
- pCrossAMI for the five positive tributaries exceeds the surrogate upper
  band at horizons 1–4 (multi-day routing window).
- pCrossAMI for the three negative-control stations stays within the
  surrogate band at every horizon (no spurious causal hits).
- The resulting `contract.past_covariates` contains only the positive
  station names (stricter check: at least four of the five positives, and
  zero negatives), and the per-driver `selected_lags` lists in
  `bundle.covariate_rows` are non-empty for positives and empty for
  negatives. **These are the success criteria of the capability demo.**
- Two recipe sub-cells then show the contract feeding (a) Darts
  `LightGBMModel` via `lags_past_covariates` populated from
  `bundle.covariate_rows[i].selected_lags`, and (b) MLForecast
  `LGBMRegressor` via `lag_transforms` keyed on the same per-driver lags.
  These cells are **illustrative wiring only**; no forecast-accuracy
  numbers are reported. They mirror the patterns in
  [docs/recipes/forecast_prep_to_external_frameworks.md](../recipes/forecast_prep_to_external_frameworks.md)
  and re-affirm EX-NB-04 cross-link bidirectionality.

**Acceptance criteria:**

- The notebook executes end-to-end via `nbconvert --execute --inplace` on a
  fresh sibling clone with the cached parquet.
- `grep -n "from forecastability\.\(services\|use_cases\|utils\|adapters\|diagnostics\)" walkthroughs/07_causal_rivers_lag_and_feature_selection.ipynb`
  returns zero hits (sibling import-surface lint).
- The selection assertions are present as `assert` cells so CI failure is
  loud:
  - `assert {"station_979", "station_1095", "station_313", "station_758", "station_490"}.intersection(contract.past_covariates)` has size ≥ 4.
  - `assert not {"station_67", "station_71", "station_99"}.intersection(contract.past_covariates)`.
  - For every positive driver row in `bundle.covariate_rows`,
    `selected_lags` is non-empty; for every negative driver row,
    `selected_lags` is empty.
- The notebook reports **no forecast-accuracy metrics**; the recipe
  sub-cells stop after model construction (a comment marks the line where
  a real user would call `.fit()`).
- Per-notebook 15-minute timeout in the sibling notebooks workflow holds:
  on the cached parquet the full notebook runs in under 6 minutes on a
  GitHub-Actions `ubuntu-latest` runner.

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

- `README.md` — remove "Notebooks" section and any walkthrough callout. The
  new "Tutorials, walkthroughs, and integrations" section (EX-D03) points
  at the sibling repo and includes the "Where to file issues" subsection.
- `docs/quickstart.md` — drop notebook links.
- `docs/notebooks/` — delete or repurpose to "Notebooks moved" stub.
- `llms.txt` — drop notebook anchor; add recipes anchor.
- `AGENTS.md` — drop the notebook entry from "Navigation Order".
- `.github/copilot-instructions.md` — drop the notebook entry from
  "Start Here".
- [`docs/examples_index.md`](../examples_index.md) (created by EX-D03) —
  list **executed-notebook release-asset URLs** in the sibling repo, not
  raw `.ipynb` source URLs, so drive-by readers see rendered outputs
  immediately. Each row of the index is of the form
  `name | sibling source URL | executed asset URL (release v0.4.0)`.

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
ultimate plan).

### Phase 5 — Release

#### Cross-repo coupling overview (EX-CPL-01 / EX-CPL-02)

**Why this section exists.** The user concern "how can we split it to two
repos but keep in one project?" is answered structurally here. The two
physical repos stay independent at the code surface; coupling lives at the
**verification surface** (CI handshake) and the **planning surface**
(shared milestone + `RELEASES.md` index). Submodule, subtree, and monorepo
patterns were considered and rejected: submodule complicates contributor
workflow, subtree creates a duplicate source-of-truth, and a workspace
monorepo directly violates the slim-release thesis recorded in
[aux_documents/developer_instruction_repo_scope.md §5](../plan/aux_documents/developer_instruction_repo_scope.md).

**EX-CPL-01 — cross-repo CI handshake (workflow trigger).**

- Core release workflow emits `repository_dispatch` (`event_type:
  core_release`, payload `{ "version": "0.4.0", "tag": "v0.4.0",
  "pypi_url": "..." }`) on every published release tag.
- Sibling repo's `.github/workflows/release.yml` subscribes to that event,
  re-installs `dependence-forecastability == <version>` from PyPI, and
  re-runs the EX-NB-MATRIX-01 notebook matrix end-to-end.
- On success, the sibling workflow posts a comment on the core release
  page linking to the sibling notebook execution report.
- Manual `workflow_dispatch` fallback exists for outages and re-runs.
- Secret scope: a single fine-grained PAT scoped to
  `metadata: read, contents: read, issues: write` on the core repo,
  stored as `CORE_RELEASE_HANDSHAKE_TOKEN` in the sibling repo secrets.

**EX-CPL-02 — shared planning surface.**

- Create a GitHub Project board spanning both repos with a `v0.4.0`
  milestone; both repos label issues with `release/0.4.0`.
- Add a top-level `RELEASES.md` to the core repo that maintains a chronological
  table of `(core_tag, sibling_tag, date, notes_url)` so release pairs are
  visible in one place even without the GitHub Project.

#### EX-REL-01 / EX-REL-02 — two-repo release dance

Resolves the chicken-and-egg between "sibling needs PyPI artifact" and
"core release acceptance requires sibling notebooks pass".

1. **Core: cut `v0.4.0-rc1` on the v0.4.0 feature branch.** Bump
   `pyproject.toml` to `0.4.0rc1`. Tag `v0.4.0-rc1`. **Do not publish to PyPI.**
2. **Core: publish `v0.4.0-rc1` to TestPyPI** via the trusted-publisher flow.
3. **Sibling: open `release/v0.4.0` branch.**
   - Run the EX-REL-02 pre-flight matrix with `source ∈ {testpypi, git}`:
     either pin `dependence-forecastability == 0.4.0rc1` against the
     TestPyPI extra-index, or `dependence-forecastability @
     git+https://github.com/<owner>/dependence-forecastability.git@v0.4.0-rc1`.
   - Run the EX-NB-MATRIX-01 notebook matrix end-to-end. Either `source`
     green satisfies the gate; both green is preferred.
4. **Acceptance gate.** Sibling pre-flight matrix green is a hard
   prerequisite for the core final tag. Gate completion is recorded as a
   comment on the core RC tag's release page (manual or via the EX-CPL-01
   handshake).
5. **Core: cut `v0.4.0` final.** Bump to `0.4.0`, retag, push. Trusted
   publisher uploads to PyPI. (This is EX-R02.)
6. **Sibling: bump pin to `==0.4.0`, retag `v0.4.0`.** (This is EX-R03.)
7. **Cross-repo handshake.** EX-CPL-01 fires; sibling workflow posts the
   notebook execution report URL on the core release page.

#### EX-CHG-01 — `CHANGELOG.md` entry

```markdown
## [0.4.0] - 2026-XX-XX

### Changed

- **Library-first slim release.** All walkthrough and tutorial notebooks have
  moved to the dedicated [forecastability-examples](https://github.com/example/forecastability-examples)
  sibling repository. The Python API is unchanged; the minor version bump
  signals the surface change. Rationale: see
  [docs/plan/aux_documents/developer_instruction_repo_scope.md](../plan/aux_documents/developer_instruction_repo_scope.md).
  The v0.3.4 forecast-prep contract is showcased end-to-end in the sibling
  repo at [walkthroughs/05_forecast_prep_to_models.ipynb](https://github.com/example/forecastability-examples/blob/v0.4.0/walkthroughs/05_forecast_prep_to_models.ipynb).

### Removed

- `notebooks/` directory.
- `outputs/notebook_runs/` directory.
- `scripts/check_notebook_contract.py` and the corresponding CI step.
- The 14 v0.3.5 redirect stubs (EX-CR-05) once lychee confirms no
  inbound link remains.
- All notebook anchors from `README.md`, `llms.txt`, `AGENTS.md`, and
  `.github/copilot-instructions.md`.

### Added

- `forecastability.TargetBaselineCurves` and
  `forecastability.compute_target_baseline_by_horizon` re-exported additively
  from the new `forecastability.extensions` module (EX-CR-CR-01). No existing
  symbol is removed or renamed.
- `scripts/run_causal_rivers_analysis.py` and
  `configs/causal_rivers_analysis.yaml` deterministic showcase for the
  CausalRivers East Germany subset.
- `scripts/bootstrap_local_workspace.sh` and
  `docs/development/local_workspace.md` documenting the
  one-checkout-two-remotes maintainer workflow (EX-LOCAL-01).
- `docs/examples_index.md` listing the migrated notebooks with
  executed-notebook release-asset URLs in the sibling repo. The
  causal-rivers capability-demo walkthrough
  `walkthroughs/07_causal_rivers_lag_and_feature_selection.ipynb`
  (EX-NB-05) is the headline lag-and-feature-selection demo at v0.4.0
  launch. It is positioned in the index as a **capability demo on a
  public benchmark dataset**, not as a forecasting study.
- "Tutorials, walkthroughs, and integrations" section in `README.md`
  pointing at the sibling repo, including a "Where to file issues" subsection.
- Top-level `RELEASES.md` index pairing core and sibling release tags
  (EX-CPL-02).
```

#### EX-R01..R03 — Versioning, publish, sibling release

Follows the seven-step EX-REL-01 dance above (with EX-REL-02 pre-flight).
The single sentence "sibling repo cuts its first release immediately after
PyPI publication" in earlier drafts is replaced by that ordered sequence.

---

## 6. Risks and mitigations

### 6.1. Migration risks

| Risk | Mitigation |
| --- | --- |
| Notebook history loss during migration | Use `git filter-repo` with `--path-rename` and verify with `git log --follow` before the core-side deletion. |
| Sibling repo CI flakiness due to framework version churn | Pin `darts` and `mlforecast` to compatible major-version ranges in the sibling repo; commit `uv.lock` (EX-NB-LOCK-01); refresh on a quarterly cadence in the sibling repo, never in core. |
| Users following stale README links | Keep `docs/notebooks/` as a one-page stub for at least one release after v0.4.0, with a single-line "moved to [URL]" note. |
| `git filter-repo` unavailable in maintainer environment | Document the `git subtree split` fallback in the sibling repo `CONTRIBUTING.md`. |
| Sibling repo accidentally importing core internals | Add a small CI lint in the sibling repo: `grep -rn "from forecastability\.\(services\|use_cases\|utils\|adapters\|diagnostics\)"` returns zero hits. |

### 6.2. Two-repo coupling risks (added 2026-04-24)

| Risk | Mitigation |
| --- | --- |
| **Version drift between sibling pin and core latest.** Sibling pinned to `==0.4.0` while core ships `0.5.0` with a contract field rename; users following sibling get stale guidance. | Sibling `unpinned-main` matrix job (EX-NB-MATRIX-01) catches drift on a weekly cron; quarterly refresh PR (EX-NB-LOCK-01) bumps the pin. Core release workflow auto-files an issue on the sibling repo for every minor bump. |
| **Notebook lock-in to old core symbols.** Sibling notebooks call a public API that core deprecates without removing; sibling stays green, the user copies stale code. | Core deprecation policy: mark with `DeprecationWarning` for one full minor cycle. Sibling CI runs with `PYTHONWARNINGS=error::DeprecationWarning` on the `unpinned-main` matrix job, surfacing deprecations as red builds. |
| **PR coupling friction.** A single conceptual change (e.g. add a contract field) needs a core PR plus a sibling PR; one half merges and the other does not. | Sibling repo's PR template requires either a "no core change required" checkbox or a link to the merged core PR + the version it shipped in. EX-CPL-02 shared GitHub Project lets reviewers see both PRs in one column. Core PRs that change `ForecastPrepContract` schema must include a sibling-repo issue link in the PR description (enforced by a CODEOWNERS reviewer). |
| **Contributor confusion about where to file issues.** Bug report against a notebook lands on core; question about contract semantics lands on sibling. | Core `README.md` "Tutorials, walkthroughs, and integrations" section (EX-D03) has an explicit "Where to file issues" subsection. Sibling `README.md` mirrors it. Both repos add a single GitHub issue template "Wrong repo? See <URL>" as the top option in `.github/ISSUE_TEMPLATE/`. |
| **Doc cross-link rot.** Renames or moves on either side break inbound links from the other; users see 404s; LLMs cite dead anchors. | Core CI gains a small lychee link-checker step (already present from v0.3.5 V3_5-DOC-RE-03) extended to scope outbound links to `forecastability-examples`. Sibling CI does the same in reverse. EX-NB-04 makes the contract recipe links bidirectional and explicit. Sibling release workflow tags every executed-notebook URL with the release tag (`/releases/download/v0.4.0/05_forecast_prep_to_models.html`) so URLs are immutable. |
| **Chicken-and-egg at first release.** Sibling tests require the v0.4.0 PyPI artifact; the v0.4.0 acceptance criteria require sibling tests to pass. | Two-step release dance from EX-REL-01 with the rc1 + TestPyPI / `git+` pre-flight (EX-REL-02). |
| **Acceptance-gate availability.** Sibling CI is green at release time, but a transient PyPI / GitHub-Actions outage prevents the cross-repo handshake. | EX-CPL-01 workflow has a manual `workflow_dispatch` trigger so a maintainer can re-fire the gate; EX-CPL-02 shared milestone serves as the manual ledger of gate completion. |
| **Sibling repo grows its own monolith.** Without scope rules, the sibling accretes everything that does not fit core: blog posts, slide decks, paper drafts. | Sibling `README.md` adopts a one-sentence scope statement: "Runnable, framework-specific demonstrations of `dependence-forecastability`. Anything else belongs in the core repo, in a personal blog, or in a paper." Sibling CI requires every new top-level directory to be added to a manifest; PRs introducing undocumented top-level directories fail. |
| **Local-dev path drift / accidental cross-repo commit.** Maintainer working in the multi-root workspace runs `git add` from the parent directory, or pushes to the wrong remote, or leaves `FORECASTABILITY_LOCAL_DEV=1` set on a release-rehearsal run and silently builds the sibling against an unreleased core. | EX-LOCAL-01 ships three independent safeguards: (1) the `forbid-cross-repo-staging` pre-commit hook in core fails when staged paths leave the core tree; (2) `scripts/bootstrap_local_workspace.sh` is idempotent and prints the resolved core install path on every run, so a non-PyPI resolution is visible; (3) `docs/development/local_workspace.md` documents the rule that release rehearsals must run with `FORECASTABILITY_LOCAL_DEV` unset, mirrored by sibling CI which never reads the env var. |
| **CausalRivers data fetch breakage.** The benchmark release URL or schema changes; EX-NB-05 starts failing on a sibling CI matrix that worked yesterday. | `scripts/download_causal_rivers.py` (EX-NB-DATA-02) pins the source URL to a tagged release, validates the SHA-256 manifest before writing the parquet, and surfaces a clear error message naming the expected hash. The sibling repo opens a tracking issue and the unpinned-main matrix job (EX-NB-MATRIX-01) catches drift weekly. |

---

## 7. Out of scope

- Any change to the public Python API of `dependence-forecastability`.
- Adding any new optional extra to the core repo.
- Adding any new notebook to the core repo.
- Maintenance of the framework-side (`darts`, `mlforecast`, …) versions
  beyond what the sibling repo declares.

---

## 8. Cross-references

- [aux_documents/developer_instruction_repo_scope.md](../plan/aux_documents/developer_instruction_repo_scope.md) — driver document.
- [v0.3.4 Forecast Prep Contract: Ultimate Release Plan](v0_3_4_forecast_prep_contract_ultimate_plan.md) — surface that EX-NB-01..03 demonstrate.
- [v0.3.5 Documentation Quality Improvement: Scope Revision (2026-04-24)](v0_3_5_documentation_quality_improvement_revision_2026_04_24.md) — supplies V3_5-DOC-RE-10 (consumed by EX-CR-05) and the lychee CI job extended in §6.2.
- [pypi_release_plan.md](pypi_release_plan.md).
