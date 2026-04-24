<!-- type: reference -->
# v0.3.4 — Forecast Prep Contract: Scope Revision (2026-04-24)

**Plan type:** Revision overlay — narrows the scope of the in-flight v0.3.4 plan
**Audience:** Maintainer, reviewer, statistician reviewer, Jr. developer
**Target release:** `0.3.4` (unchanged ordering: 0.3.3 → 0.3.4 → 0.3.5 → 0.4.0)
**Branch:** `feat/v0.3.4-forecast-prep-contract`
**Status:** Draft / Proposed
**Last reviewed:** 2026-04-24

> [!IMPORTANT]
> This file **revises and supersedes** specific sections of
> [v0.3.4 Forecast Prep Contract: Ultimate Release Plan](v0_3_4_forecast_prep_contract_ultimate_plan.md).
> Where the two disagree, this overlay wins. Sections of the original plan
> not listed below are preserved verbatim.

**Driver document:** [aux_documents/developer_instruction_repo_scope.md](aux_documents/developer_instruction_repo_scope.md).

---

## 1. Why this revision exists

The reviewer-provided
[developer_instruction_repo_scope.md](aux_documents/developer_instruction_repo_scope.md)
calls out that the original v0.3.4 plan would push the repository past its
charter as a deterministic forecastability triage toolkit by:

- adding `darts` and `mlforecast` runtime dependencies, even as optional extras;
- shipping framework-coupled public symbols (`to_darts_spec`, `to_mlforecast_spec`, `fit_darts`, `fit_mlforecast`) as supported API;
- shipping a downstream-fitting walkthrough notebook (`05_forecast_prep_to_models.ipynb`) as the headline learning surface.

This revision **keeps** the headline contribution — a neutral, deterministic,
additive `ForecastPrepContract` with a three-axis mapping and deterministic
calendar features — and **removes** every framework-coupled surface from the
release. Framework usage becomes an illustrative recipe in docs, and lives in
the future sibling examples repository ([v0.4.0 plan](v0_4_0_examples_repo_split_ultimate_plan.md)).

---

## 2. What is dropped from v0.3.4

The following items from the original plan are **removed** from the v0.3.4
release scope:

| Item ID (original plan) | Description | Disposition |
| --- | --- | --- |
| FPC-F04 | `to_mlforecast_spec()` exporter | **Dropped.** Replaced by FPC-F04R (framework-agnostic exporters). Spec mapping moves to docs recipe FPC-D04R. |
| FPC-F05 | `to_darts_spec()` exporter | **Dropped.** Same disposition as FPC-F04. |
| FPC-F05.1 | Exporter warnings policy (Darts/MLForecast wording) | **Dropped.** Caution flags continue to live on `ForecastPrepContract`; framework-specific warnings move to the recipe page. |
| FPC-F06 | `fit_mlforecast()` runner | **Dropped.** No fitting helpers ship from the core package. |
| FPC-F07 | `fit_darts()` runner | **Dropped.** Same as FPC-F06. |
| FPC-F07.1 | Optional extras (`[darts]`, `[mlforecast]`) | **Dropped.** No new optional extras are added in v0.3.4. |
| FPC-F09 | Walkthrough notebook `05_forecast_prep_to_models.ipynb` | **Dropped.** Ships in the sibling examples repo in v0.4.0. v0.3.4 ships docs and a small script demo only. |
| FPC-F10.1 | Runner tests with `pytest.importorskip` | **Dropped.** No runners exist. |
| FPC-CI-02 | Optional-extras CI matrix | **Dropped.** Core CI matrix is unchanged. |
| FPC-R02 | Walkthrough notebook executed-and-committed | **Dropped.** No new walkthrough is committed in v0.3.4. |

> [!NOTE]
> The `forecastability.integrations` namespace, `darts_runner.py`,
> `mlforecast_runner.py`, `darts_spec.py`, `mlforecast_spec.py`, and any
> matching tests are **not created** in v0.3.4. The reviewer's directive is
> binding: the core package adds zero new framework runtime dependencies in
> any tier (core, optional, dev, CI).

---

## 3. What replaces them — framework-agnostic exporters and recipes

### 3.1. FPC-F04R — Framework-agnostic exporters (replaces FPC-F04 + FPC-F05)

**Goal.** Make the contract trivially consumable from any forecasting framework
without importing one.

**Public surface (additive, re-exported from `forecastability` and
`forecastability.triage`):**

- `ForecastPrepContract.model_dump()` — already free via Pydantic; documented
  as the canonical Python-dict export.
- `ForecastPrepContract.model_dump_json(indent=2)` — already free via Pydantic;
  documented as the canonical JSON payload.
- `forecast_prep_contract_to_markdown(contract: ForecastPrepContract) -> str`
  — short human- and LLM-readable summary (frequency, horizon, recommended
  target lags, seasonal lags, past covariates with sparse lag sets, future
  covariates including calendar columns, recommended families, caution flags).
  Pure standard-library implementation; no rendering deps.
- `forecast_prep_contract_to_lag_table(contract: ForecastPrepContract) -> list[dict[str, object]]`
  — tabular `(driver, role, lag, selected_for_handoff, rationale)` rows
  suitable for serialisation to CSV / DataFrame by the user. Returns plain
  Python; the package never imports `pandas` here even though the rest of
  the package may.

**Modules:**

- `src/forecastability/services/forecast_prep_export.py` (new, pure standard-library).
- `src/forecastability/use_cases/build_forecast_prep_contract.py` (unchanged from original plan).

**Acceptance criteria:**

- `model_dump_json()` round-trips deterministically across Python versions.
- `forecast_prep_contract_to_markdown()` produces a stable string for a frozen
  fixture (snapshot tested).
- `forecast_prep_contract_to_lag_table()` returns rows ordered by
  `(role, driver, lag)` deterministically.
- None of the new exporters import `darts`, `mlforecast`, `statsforecast`,
  `nixtla`, or any other forecasting framework.

### 3.2. FPC-D04R — External recipes documentation page (replaces FPC-D02 framework prose + FPC-F09 notebook)

**File:** `docs/recipes/forecast_prep_to_external_frameworks.md` (new).

**Content:**

- Section *"Map a contract to MLForecast"*: a fenced Python code block showing
  how a user could translate `ForecastPrepContract.past_covariates`,
  `selected_lags`, `recommended_target_lags`, and `future_covariates` into
  `MLForecast(lags=…, lag_transforms=…, target_transforms=…)` arguments.
  Marked at the top as **"Illustrative recipe — not part of the supported
  package API."**
- Section *"Map a contract to Darts"*: same shape; covers
  `lags_past_covariates` (driven by `selected_for_tensor=True` only),
  `lags_future_covariates`, and the calendar-column treatment.
- Section *"Map a contract to Nixtla / StatsForecast"*: same shape, single
  illustrative snippet.
- Section *"Why these are recipes, not adapters"*: 3–5 bullets restating the
  scope decision and pointing at
  `docs/plan/aux_documents/developer_instruction_repo_scope.md`.

**Acceptance criteria:**

- The page exists and is linked from `docs/forecast_prep_contract.md`.
- Every framework-specific snippet is fenced and prefixed with the
  illustrative-recipe disclaimer.
- The page contains **no `import` of the forecastability package** that
  resolves to anything other than `forecastability` or
  `forecastability.triage` (see v0.3.5 Invariant A).
- The terminology grep panel (v0.3.5 Invariant C) is updated to allow the
  framework names *only* on this page and on archived plans.

### 3.3. FPC-S04R — Showcase script (replaces FPC-F08.1 + FPC-F09)

**File:** `scripts/run_showcase_forecast_prep.py` (new).

- Runs the full triage → contract path on a deterministic synthetic series.
- Writes the contract as JSON and as the new markdown summary into
  `outputs/examples/forecast_prep/`.
- Has `--smoke` mode for CI.
- Imports only from `forecastability` / `forecastability.triage`.
- **Does not** import any forecasting framework. The script ends at the
  contract boundary; the recipe page (FPC-D04R) shows what a user would do
  next.

**Acceptance criteria:**

- `uv run python scripts/run_showcase_forecast_prep.py --smoke` exits 0 in CI.
- Writes a JSON contract that round-trips through
  `ForecastPrepContract.model_validate_json`.
- Has no framework imports (lint-checked via the new exclusion rule introduced
  in v0.3.5; see §5 below).

---

## 4. Reviewer acceptance block — revised

The original §1 reviewer acceptance block is replaced by the following (10
items reduced to 8 to reflect the dropped surfaces):

1. **Neutral core contract.** Unchanged from original §1.1.
2. **Builder.** Unchanged from original §1.2.
3. **Three input axes.** Unchanged from original §1.3.
4. **Calendar features.** Unchanged from original §1.4.
5. **Framework-agnostic exporters.**
   - `model_dump()` and `model_dump_json()` are documented as the canonical
     Python and JSON export surfaces.
   - `forecast_prep_contract_to_markdown()` and
     `forecast_prep_contract_to_lag_table()` are re-exported from
     `forecastability` and `forecastability.triage`.
   - No `to_darts_spec`, `to_mlforecast_spec`, `fit_darts`, `fit_mlforecast`,
     or `forecastability.integrations.*` symbol exists in the source tree.
6. **Recipes page.**
   - `docs/recipes/forecast_prep_to_external_frameworks.md` exists with the
     three illustrative mappings and the "why recipes, not adapters"
     justification.
7. **Showcase script.**
   - `scripts/run_showcase_forecast_prep.py` runs end-to-end in `--smoke`
     mode without any framework dependency.
8. **Release engineering.**
   - Version bump, fixture rebuilds, and tag `v0.3.4` proceed exactly as in
     the original plan, but with **no new walkthrough notebook committed**
     and **no `[project.optional-dependencies]` changes**.

---

## 5. Coordination with v0.3.5 docs hardening

The v0.3.5 plan's import-resolution invariant is extended (in
[v0.3.5 revision](v0_3_5_documentation_quality_improvement_revision_2026_04_24.md))
with an additional check:

> **Invariant E — No framework runtime imports in the core package or in
> user-facing examples.** No file under `src/forecastability/`, `examples/`,
> `scripts/` (except the recipe-rendering script if any), or `tests/` may
> contain `import darts`, `import mlforecast`, `import statsforecast`, or
> `import nixtla`. Allowed exceptions: `docs/recipes/**` (documentation
> snippets, never executed by CI) and `docs/archive/**`.

A grep-based CI sub-check enforces this. See the v0.3.5 revision for the
exact `scripts/check_docs_contract.py --no-framework-imports` flag.

---

## 6. Coordination with v0.4.0 examples-repo split

Items dropped from v0.3.4 are not abandoned. They re-appear in the sibling
examples repository introduced by
[v0.4.0 Examples Repo Split: Ultimate Release Plan](v0_4_0_examples_repo_split_ultimate_plan.md):

- The `05_forecast_prep_to_models.ipynb` walkthrough is created in the
  examples repo, not in this repo.
- Concrete framework-fitting code (Darts and MLForecast end-to-end runs)
  lives in the examples repo.
- The recipe page in this repo links forward to the examples repo for
  executable demos.

---

## 7. Migration of in-flight work

If branch `feat/v0.3.4-forecast-prep-contract` already contains code or tests
for the dropped items, the following cleanup is part of this revision:

1. Delete `src/forecastability/integrations/` if created.
2. Delete `tests/test_darts_runner.py`, `tests/test_mlforecast_runner.py`,
   `tests/test_to_darts_spec.py`, `tests/test_to_mlforecast_spec.py` if
   created.
3. Revert the `[project.optional-dependencies]` block in `pyproject.toml` to
   the v0.3.3 baseline.
4. Remove any `forecastability.integrations.*` re-exports from
   `src/forecastability/__init__.py` and `src/forecastability/triage/__init__.py`.
5. Add `forecast_prep_contract_to_markdown` and
   `forecast_prep_contract_to_lag_table` to those re-exports per §3.1.
6. Move any drafted recipe snippets out of notebook form and into
   `docs/recipes/forecast_prep_to_external_frameworks.md`.

A single follow-up commit on the feature branch is sufficient.

---

## 8. Out of scope

Explicitly **out of scope** for v0.3.4 under this revision:

- Any framework-specific public symbol or test.
- Any optional extra that pulls a forecasting framework.
- Any change to existing notebooks (their fate is the v0.4.0 plan).
- Renaming or removing existing public symbols (the additive contract holds).

---

## 9. Cross-references

- [v0.3.4 Forecast Prep Contract: Ultimate Release Plan](v0_3_4_forecast_prep_contract_ultimate_plan.md) — original plan; this overlay supersedes the items listed in §2.
- [v0.3.5 Documentation Quality Improvement: Scope Revision (2026-04-24)](v0_3_5_documentation_quality_improvement_revision_2026_04_24.md).
- [v0.4.0 Examples Repo Split: Ultimate Release Plan](v0_4_0_examples_repo_split_ultimate_plan.md).
- [aux_documents/developer_instruction_repo_scope.md](aux_documents/developer_instruction_repo_scope.md) — driver document.
