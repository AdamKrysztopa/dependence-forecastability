<!-- type: reference -->
# v0.3.5 — Documentation Quality Improvement: Scope Revision (2026-04-24)

**Plan type:** Revision overlay — aligns the v0.3.5 docs-hardening plan with the slimmed v0.3.4 surface and the upcoming v0.4.0 examples-repo split
**Audience:** Maintainer, reviewer, documentation contributor, Jr. developer
**Target release:** `0.3.5` (unchanged ordering: 0.3.3 → 0.3.4 → 0.3.5 → 0.4.0)
**Branch:** `feat/v0.3.5-docs-quality-hardening`
**Status:** Draft / Proposed
**Last reviewed:** 2026-04-24

> [!IMPORTANT]
> This file **revises and supersedes** specific sections of
> [v0.3.5 Documentation Quality Improvement: Ultimate Release Plan](v0_3_5_documentation_quality_improvement_ultimate_plan.md).
> Where the two disagree, this overlay wins. Sections of the original plan
> not listed below are preserved verbatim.

**Driver documents:**

- [aux_documents/developer_instruction_repo_scope.md](aux_documents/developer_instruction_repo_scope.md)
- [v0.3.4 Forecast Prep Contract: Scope Revision (2026-04-24)](v0_3_4_forecast_prep_contract_revision_2026_04_24.md)

---

## 1. Why this revision exists

The original v0.3.5 plan was sized for a v0.3.4 surface that included
`to_darts_spec`, `to_mlforecast_spec`, `fit_darts`, `fit_mlforecast`,
`[darts]` and `[mlforecast]` extras, and a downstream-fitting walkthrough
notebook. The
[v0.3.4 scope revision](v0_3_4_forecast_prep_contract_revision_2026_04_24.md)
removed all of these from the release. v0.3.5 must (a) drop the matching docs
work, (b) add a docs-contract sub-check that **enforces** the no-framework-imports
rule going forward, and (c) prepare the docs surface for the v0.4.0
examples-repo split without performing the split itself.

---

## 2. What is dropped from v0.3.5

The following items from the original plan are **removed** or **narrowed**:

| Item ID (original plan) | Description | Disposition |
| --- | --- | --- |
| V3_3-DQ-01 (subset) | Audit framework-extras docs snippets | **Narrowed.** No `[darts]` / `[mlforecast]` install snippets exist; check is reduced to "no install line refers to those extras". |
| V3_3-D01 (subset) | README/quickstart prose covering optional extras and framework adapters | **Dropped.** README install section keeps only the unchanged extras (`agent`, `causal`, `transport`). |
| V3_3-D03 (subset) | Changelog narrative for `[darts]` / `[mlforecast]` extras | **Dropped.** v0.3.4 changelog entry instead documents the framework-agnostic exporters and the recipe page. |
| Notebook contract sweep over `05_forecast_prep_to_models.ipynb` | Add the new headline notebook to `scripts/check_notebook_contract.py` | **Dropped.** No new notebook ships in v0.3.4. |

The notebook hygiene scope (V3_3-DQ-07) is **kept** for the four current
walkthrough notebooks and the six `notebooks/triage/` notebooks. Their full
migration is the v0.4.0 plan, not v0.3.5.

---

## 3. What is added — Invariant E and notebook transition banner

### 3.1. Invariant E — No framework runtime imports

> **Invariant E.** No file under `src/forecastability/`, `examples/`,
> `scripts/`, or `tests/` may contain a top-level or nested `import` of
> `darts`, `mlforecast`, `statsforecast`, or `nixtla` (any submodule). The
> only places these names may appear in the repository are:
>
> - `docs/recipes/**` — illustrative recipes (never executed by CI);
> - `docs/archive/**` — historical material;
> - `docs/plan/aux_documents/**` — driver documents and reviewer notes;
> - `CHANGELOG.md` — release-note text describing the scope decision.

Formal predicate: for the set $\mathcal{F}_{\text{guarded}}$ of guarded files
(everything under `src/`, `examples/`, `scripts/`, `tests/`):

$$\forall f \in \mathcal{F}_{\text{guarded}}, \forall n \in \{\texttt{darts}, \texttt{mlforecast}, \texttt{statsforecast}, \texttt{nixtla}\}: \texttt{rg "^\\s*(import|from)\\s+" + n + "\\b"}\,f = \emptyset$$

**Implementation:**

- New sub-check `--no-framework-imports` in `scripts/check_docs_contract.py`.
- Result type: extends `DocsCheckName` `Literal` in
  `src/forecastability/diagnostics/docs_contract.py` with
  `"no-framework-imports"`.
- Wired into the `docs-contract` workflow job alongside the four existing
  invariants.

**Acceptance criteria:**

- `uv run python scripts/check_docs_contract.py --no-framework-imports` exits 0
  on a clean checkout.
- A deliberate `import darts` added to any guarded file makes the check fail
  with a file:line message.

### 3.2. V3_3-DQ-09R — Notebook transition banner (new)

**File targets:**

- `notebooks/walkthroughs/00_air_passengers_showcase.ipynb`
- `notebooks/walkthroughs/01_covariant_informative_showcase.ipynb`
- `notebooks/walkthroughs/01_canonical_forecastability.ipynb`
- `notebooks/walkthroughs/02_exogenous_analysis.ipynb`
- `notebooks/walkthroughs/02_forecastability_fingerprint_showcase.ipynb`
- `notebooks/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb`
- `notebooks/walkthroughs/03_triage_end_to_end.ipynb`
- `notebooks/walkthroughs/04_routing_validation_showcase.ipynb`
- `notebooks/walkthroughs/04_screening_end_to_end.ipynb`
- every `*.ipynb` under `notebooks/triage/`

**Change:** add a single transition banner as the first markdown cell of each
notebook with the following text (verbatim):

> **Note — notebook surface is moving.** Starting with `v0.4.0`, all notebooks
> in this repository will move to the dedicated
> [`forecastability-examples`](https://github.com/example/forecastability-examples)
> sibling repository. The library itself will keep only deterministic Python
> APIs, scripts under `scripts/`, and recipe pages under `docs/recipes/`.
> See [docs/plan/v0_4_0_examples_repo_split_ultimate_plan.md](../../docs/plan/v0_4_0_examples_repo_split_ultimate_plan.md).

**Acceptance criteria:**

- Every notebook listed above starts with the transition banner.
- A small CI sub-check (`scripts/check_notebook_contract.py --transition-banner`)
  asserts the banner is present.
- The banner text contains the substring `"v0.4.0"` and the relative link to
  the v0.4.0 plan.

> [!NOTE]
> The actual GitHub URL is a placeholder until the v0.4.0 plan creates the
> sibling repo. The banner uses a placeholder URL for now and is updated in
> v0.4.0.

### 3.3. V3_3-DQ-04 (extension) — Terminology table additions

Add to the canonical terminology table in `docs/wording_policy.md` (and to
the §6.4 mirror in the original v0.3.5 plan):

| Concept | Canonical token | Forbidden alternates |
| --- | --- | --- |
| Hand-off contract | `ForecastPrepContract` | `forecast prep spec`, `prep payload`, `model handoff struct` |
| Framework-agnostic export | `ForecastPrepContract.model_dump_json()` | `to_json()`, `to_darts_spec()`, `to_mlforecast_spec()` |
| External usage code | `external recipe` | `framework adapter`, `framework integration`, `runner` |
| Sibling examples repo | `examples repository` (or `forecastability-examples`) | `notebooks repo`, `tutorials repo` |

The terminology grep panel scope is unchanged: `README.md`, `docs/**/*.md`,
`examples/**/*.{py,md}`. `docs/recipes/**` is included in scope because the
canonical token policy still applies to recipe prose; only the *framework
import names* are excepted (Invariant E).

---

## 4. Reviewer acceptance block — revised

The original §1 acceptance block is amended:

- Item 1 (Import contract) — unchanged.
- Item 2 (Version coherence) — unchanged.
- Item 3 (Terminology) — extended with the §3.3 entries.
- Item 4 (Plan lifecycle) — unchanged.
- Item 5 (Status freshness) — extended: `docs/implementation_status.md` notes
  the upcoming v0.4.0 examples-repo split.
- Item 6 (CI surface) — extended: the `docs-contract` job runs **five**
  sub-checks (the four originals plus `--no-framework-imports`).
- Item 7 (Changelog) — unchanged.
- **New item 8.** Every existing notebook carries the v0.4.0 transition
  banner per §3.2.

---

## 5. Out of scope

- Performing the actual notebook migration. That is the [v0.4.0 plan](v0_4_0_examples_repo_split_ultimate_plan.md).
- Removing existing notebooks from this repo. They stay through v0.3.5 and
  are removed in v0.4.0.
- Adding any new walkthrough notebook in v0.3.5 (none ships in v0.3.4 either,
  per the [v0.3.4 revision](v0_3_4_forecast_prep_contract_revision_2026_04_24.md)).

---

## 6. Cross-references

- [v0.3.5 Documentation Quality Improvement: Ultimate Release Plan](v0_3_5_documentation_quality_improvement_ultimate_plan.md) — original plan; this overlay supersedes the items listed in §2 and adds the items in §3.
- [v0.3.4 Forecast Prep Contract: Scope Revision (2026-04-24)](v0_3_4_forecast_prep_contract_revision_2026_04_24.md).
- [v0.4.0 Examples Repo Split: Ultimate Release Plan](v0_4_0_examples_repo_split_ultimate_plan.md).
- [aux_documents/developer_instruction_repo_scope.md](aux_documents/developer_instruction_repo_scope.md).
