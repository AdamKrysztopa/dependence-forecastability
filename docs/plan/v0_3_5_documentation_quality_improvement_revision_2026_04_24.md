<!-- type: reference -->
# v0.3.5 — Documentation Quality Improvement: Scope Revision (2026-04-24)

**Plan type:** Revision overlay — aligns the v0.3.5 docs-hardening plan with the slimmed v0.3.4 surface and the upcoming v0.4.0 examples-repo split
**Audience:** Maintainer, reviewer, documentation contributor, Jr. developer
**Target release:** `0.3.5` (unchanged ordering: 0.3.3 → 0.3.4 → 0.3.5 → 0.4.0)
**Branch:** `feat/v0.3.5-docs-quality-hardening`
**Status:** Draft / Proposed
**Last reviewed:** 2026-04-24

> [!IMPORTANT]
> This file **is** the v0.3.5 plan of record. It started life as a revision
> overlay against an earlier draft scope that was later abandoned; the
> name is kept for audit-trail continuity. There is no separate
> `v0_3_5_documentation_quality_improvement_ultimate_plan.md` file.

**Driver documents:**

- [aux_documents/developer_instruction_repo_scope.md](aux_documents/developer_instruction_repo_scope.md)
- [v0.3.4 Forecast Prep Contract: Ultimate Release Plan](v0_3_4_forecast_prep_contract_ultimate_plan.md) — v0.3.4 shipped; the previously referenced standalone revision overlay was folded into the ultimate plan and is intentionally absent.

---

## 1. Why this revision exists

The original v0.3.5 plan was sized for a v0.3.4 surface that included
`to_darts_spec`, `to_mlforecast_spec`, `fit_darts`, `fit_mlforecast`,
`[darts]` and `[mlforecast]` extras, and a downstream-fitting walkthrough
notebook. The v0.3.4 scope revision (now folded into the
[v0.3.4 ultimate plan](v0_3_4_forecast_prep_contract_ultimate_plan.md))
removed all of these from the release. v0.3.5 must:

1. **Drop** the matching docs work tied to those removed surfaces (§2).
2. **Enforce** the no-framework-imports rule via a new docs-contract sub-check (§3.1).
3. **Prepare** the docs surface for the v0.4.0 examples-repo split without performing the split itself (§3.2).
4. **Reorganize** the flat `docs/` root into Diátaxis-aligned buckets so the documentation reads as a professionally curated surface rather than a 20-file dump (§3.4 — added in this 2026-04-24 expansion).
5. **Adopt** the lightweight docs tooling that directly mitigates the reorganization risk (markdownlint-cli2, lychee link-check) and **defer** the heavyweight tooling (MkDocs Material, mkdocstrings, Vale, pre-commit) until v0.4.x (§3.5).

> [!IMPORTANT]
> The reorganization in §3.4 is mechanical and additive. It moves files, leaves
> redirect stubs at the old paths for one release cycle, and pins
> [`docs/quickstart.md`](../quickstart.md) and [`docs/public_api.md`](../public_api.md)
> at the root permanently because they are externally referenced by
> `llms.txt`, `.github/copilot-instructions.md`, the README badge, and the
> PyPI `Documentation` URL in `pyproject.toml`. v0.3.5 ships **no new
> statistical methods**, **no new public symbols**, and **no new optional
> dependencies** — exactly as the v0.4.0 plan promises for the next release.

### Identity statement (binding)

`v0.3.5` is a **docs hygiene and structure release**. Its only purpose is
to leave the documentation surface in a shape that can be (a) safely sliced
for the v0.4.0 sibling-examples split and (b) eventually published as a
static site by a future release without further reorganization. No part of
this release modifies runtime behavior, the public API contract, or
artifact schemas.

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

### 3.4. Documentation reorganization — flat `docs/` root → Diátaxis buckets

**Motivation.** The `docs/` root currently holds 20 flat `*.md` files with no
organizing principle. New readers cannot tell which file is a tutorial, which
is reference, and which is positioning. The flat layout also blocks any
future migration to a static-site renderer (MkDocs, Sphinx) because every
such tool expects a navigable tree.

**Pinned root paths (must not move in v0.3.5).** Verified externally
referenced — moving them silently breaks shipped artifacts:

| File | External anchors |
| --- | --- |
| [`docs/quickstart.md`](../quickstart.md) | `llms.txt:13`, `.github/copilot-instructions.md:14`, `README.md:14` (badge), `README.md:86,197`, `pyproject.toml:46` (`Documentation` URL) |
| [`docs/public_api.md`](../public_api.md) | `llms.txt:14`, `.github/copilot-instructions.md:15,23`, `README.md:85,341`, `AGENTS.md` |

In addition, [`docs/executive_summary.md`](../executive_summary.md) and
[`docs/why_use_this.md`](../why_use_this.md) **stay at the root** as the
two high-level decision-oriented entry points.

**Target tree** (root reduced from 20 → 5 files; existing subfolders
`plan/`, `recipes/`, `theory/`, `triage_methods/`, `maintenance/`,
`releases/`, `archive/`, `fixtures/`, `img/`, `input_papers/`, `code/`,
`notebooks/` are unchanged):

```
docs/
├── README.md                       # navigation map (rewritten)
├── quickstart.md                   # PINNED — do not move
├── public_api.md                   # PINNED — do not move
├── executive_summary.md            # one-page overview (root entry)
├── why_use_this.md                 # decision-oriented positioning (root entry)
│
├── how-to/
│   ├── golden_path.md
│   └── use_cases_industrial.md
│
├── explanation/
│   ├── architecture.md
│   ├── surface_guide.md
│   ├── results_summary.md
│   └── limitations.md
│
├── reference/
│   ├── api_contract.md
│   ├── agent_layer.md
│   ├── observability.md
│   ├── production_readiness.md
│   ├── diagnostics_matrix.md
│   ├── forecast_prep_contract.md
│   ├── implementation_status.md
│   └── versioning.md
│
├── maintenance/
│   └── wording_policy.md           # MOVED from docs/ root (joins developer_guide.md)
│
└── (unchanged subtrees: plan/, recipes/, theory/, triage_methods/,
    releases/, archive/, fixtures/, img/, input_papers/, code/, notebooks/)
```

**Old → new path mapping** (14 files moved; 5 stay at root; 1 moves into
`maintenance/`):

| Old path | New path | Notes |
| --- | --- | --- |
| `docs/golden_path.md` | `docs/how-to/golden_path.md` | move + redirect stub |
| `docs/use_cases_industrial.md` | `docs/how-to/use_cases_industrial.md` | move + redirect stub |
| `docs/architecture.md` | `docs/explanation/architecture.md` | move + redirect stub |
| `docs/surface_guide.md` | `docs/explanation/surface_guide.md` | move + redirect stub |
| `docs/results_summary.md` | `docs/explanation/results_summary.md` | move + redirect stub |
| `docs/limitations.md` | `docs/explanation/limitations.md` | move + redirect stub |
| `docs/api_contract.md` | `docs/reference/api_contract.md` | move + redirect stub |
| `docs/agent_layer.md` | `docs/reference/agent_layer.md` | move + redirect stub (3 notebook cells reference this) |
| `docs/observability.md` | `docs/reference/observability.md` | move + redirect stub |
| `docs/production_readiness.md` | `docs/reference/production_readiness.md` | move + redirect stub |
| `docs/diagnostics_matrix.md` | `docs/reference/diagnostics_matrix.md` | move + redirect stub |
| `docs/forecast_prep_contract.md` | `docs/reference/forecast_prep_contract.md` | move + redirect stub (linked from `docs/recipes/forecast_prep_to_external_frameworks.md`) |
| `docs/implementation_status.md` | `docs/reference/implementation_status.md` | move + redirect stub |
| `docs/versioning.md` | `docs/reference/versioning.md` | move + redirect stub |
| `docs/wording_policy.md` | `docs/maintenance/wording_policy.md` | move + redirect stub (contributor doc, fits next to `developer_guide.md`) |

**Redirect-stub contract.** Every old path keeps a one-page stub for **one
release cycle only**. Stub body is exactly:

```markdown
<!-- type: reference -->
# Moved

This page moved to [<new path>](<new path>).
```

Stubs are excluded from terminology / link-density checks via the leading
HTML comment marker. Their deletion is tracked as an explicit work item in
the v0.4.0 plan (see [v0.4.0 plan §EX-CR-05](v0_4_0_examples_repo_split_ultimate_plan.md)).

**Work items** (style mirrors §3.1 / §3.2):

#### Phase R1 — Inventory and guardrails (pre-move)

**`V3_5-DOC-RE-01` — Add `--root-path-pinned` invariant to docs-contract.**

- File targets: [`scripts/check_docs_contract.py`](../../scripts/check_docs_contract.py); extend `DocsCheckName` `Literal` in `src/forecastability/diagnostics/docs_contract.py` with `"root-path-pinned"`.
- Acceptance criteria:
  - `uv run python scripts/check_docs_contract.py --root-path-pinned` exits 0.
  - Deleting either pinned root doc, or replacing it with a redirect stub, fails the check with `<path>: pinned root doc missing or stubbed`.
  - Wired into the `docs-contract` workflow job alongside the four pre-existing invariants and the new `--no-framework-imports` from §3.1, bringing the total to **six** sub-checks.

**`V3_5-DOC-RE-02` — Add markdownlint-cli2 CI job.**

- File targets: `.markdownlint.jsonc` (new), `.github/workflows/ci.yml` (new step in the existing `quality` job, after ruff).
- Acceptance criteria:
  - `.markdownlint.jsonc` enables `MD001`, `MD003`, `MD009`, `MD025`, `MD034`, `MD040`, `MD051`; disables `MD013` and `MD033`.
  - `markdownlint-cli2 'docs/**/*.md' README.md CHANGELOG.md llms.txt` exits 0 on `main` after the reorganization PR is merged.
  - A deliberate `[link](does-not-exist.md)` in any scoped file fails the job.

**`V3_5-DOC-RE-03` — Add lychee link-check CI job.**

- File targets: `lychee.toml` (new), `.github/workflows/ci.yml` (new job `docs-links`).
- Acceptance criteria:
  - `lychee.toml` runs in `--offline` mode by default and includes `notebooks/**/*.ipynb` (extracts markdown cells) so the three known cell references to `docs/agent_layer.md` are caught.
  - Job exits 0 on the post-reorganization tree.
  - A deliberate `[broken](docs/missing.md)` insertion fails the job with the offending file:line.

#### Phase R2 — Reorganization PR (atomic — single PR per Diátaxis bucket)

**`V3_5-DOC-RE-04` — Move how-to docs.**

- File targets: `git mv docs/golden_path.md docs/how-to/golden_path.md`; same for `use_cases_industrial.md`. Add the matching redirect stubs.
- Acceptance criteria: 2 files moved; 2 stubs at old paths; markdownlint and lychee jobs green.

**`V3_5-DOC-RE-05` — Move explanation docs.**

- File targets: `architecture.md`, `surface_guide.md`, `results_summary.md`, `limitations.md` → `docs/explanation/`.
- Acceptance criteria: 4 files moved; 4 stubs; jobs green.

**`V3_5-DOC-RE-06` — Move reference docs.**

- File targets: `api_contract.md`, `agent_layer.md`, `observability.md`, `production_readiness.md`, `diagnostics_matrix.md`, `forecast_prep_contract.md`, `implementation_status.md`, `versioning.md` → `docs/reference/`.
- Acceptance criteria: 8 files moved; 8 stubs; the back-link in [`docs/recipes/forecast_prep_to_external_frameworks.md`](../recipes/forecast_prep_to_external_frameworks.md) is updated to `../reference/forecast_prep_contract.md` in the same PR; the three notebook cells referencing `docs/agent_layer.md` are updated to `docs/reference/agent_layer.md`; jobs green.

**`V3_5-DOC-RE-07` — Move wording policy to `maintenance/`.**

- File targets: `git mv docs/wording_policy.md docs/maintenance/wording_policy.md`. The terminology entries added in §3.3 land at the new location.
- Acceptance criteria: file moved; stub at old path; the existing `scripts/check_docs_contract.py --terminology` sub-check reads from the new path; jobs green.

**`V3_5-DOC-RE-08` — Rewrite `docs/README.md` navigation map.**

- File targets: [`docs/README.md`](../README.md).
- Acceptance criteria:
  - Navigation lists exactly **5 root files** and **4 buckets** (`how-to/`, `explanation/`, `reference/`, `maintenance/`).
  - The `<!-- type: reference -->` Diátaxis label HTML comment is preserved.
  - Every link resolves under lychee.

**`V3_5-DOC-RE-09` — Sweep cross-references in plans, changelog, and README.**

- File targets: `scripts/archive/rewrite_docs_paths_v035.py` (new, committed for audit), `docs/plan/**/*.md`, `CHANGELOG.md`, `README.md`.
- Acceptance criteria:
  - Script prints a deterministic mapping table and is **idempotent** (running twice is a no-op; `git diff` is empty on the second run).
  - After the first run, `git diff` touches only the expected files.
  - lychee reports zero broken links across the whole tree.

#### Phase R3 — Stub lifecycle

**`V3_5-DOC-RE-10` — Track stub deletion in v0.4.0 plan.**

- File targets: [`docs/plan/v0_4_0_examples_repo_split_ultimate_plan.md`](v0_4_0_examples_repo_split_ultimate_plan.md) (append a single feature row, `EX-CR-05`).
- Acceptance criteria: v0.4.0 plan contains the new row enumerating the 14 stub paths created here, with the deletion gated on "no inbound link from any tracked surface remains (lychee green after stub deletion)".

### 3.5. Documentation tooling — adopt now vs defer

Decisions are recorded once here and referenced by the work items above.

| Tool | Decision (v0.3.5) | Rationale (one paragraph) |
| --- | --- | --- |
| **markdownlint-cli2** | **Adopt** (V3_5-DOC-RE-02) | Cheap to wire (single CI step, one config file, zero runtime deps). Catches the breakage class the reorganization introduces: heading-level skips, broken inline links, duplicate headings inside moved files. Recommended ruleset enables MD001, MD003, MD009, MD025, MD034, MD040, MD051; disables MD013 (line length, conflicts with prose) and MD033 (inline HTML, conflicts with the GFM `> [!NOTE]` callouts). |
| **lychee link-check** | **Adopt** (V3_5-DOC-RE-03) | Directly mitigates the largest reorganization risk: silent dead intra-doc links after files move. Single GitHub Action, runs in `--offline` mode in CI, scope `docs/**/*.md README.md CHANGELOG.md llms.txt notebooks/**/*.ipynb`. Wired so the three notebook-cell references to `docs/agent_layer.md` are caught before they rot. |
| **MkDocs Material** | **Defer to v0.4.x** | The repository has no public docs site; docs are read on GitHub where Markdown, Mermaid, and GFM callouts already render natively. Standing up MkDocs requires `mkdocs.yml`, navigation config, theme config, GitHub Pages deploy workflow, KaTeX/Arithmatex JS, and per-page front-matter migration — meaningful work for zero new reader value until a published site is in scope. The Diátaxis tree from §3.4 maps cleanly to a future `nav:` so this reorganization is a prerequisite, not a blocker. |
| **mkdocstrings** | **Defer to v0.4.x** | Depends on MkDocs being adopted first. [`docs/public_api.md`](../public_api.md) is hand-curated and stable; mkdocstrings would replace nothing today and would couple doc builds to import-time behavior of `forecastability.*`. |
| **Vale** | **Skip** | The wording-policy CI sub-check (`scripts/check_docs_contract.py --terminology`, scope extended in §3.3) already enforces canonical tokens / banned alternates with deterministic rules and fast feedback. Vale would add a separate vocabulary, style package, container image, and a second source of prose-style truth without measurable accuracy gain on this corpus. |
| **pre-commit** | **Skip** | The repository has no `.pre-commit-config.yaml` today, contributors run `uv run ruff check` and `uv run pytest` directly, and CI gates everything. Adding pre-commit changes the contributor onboarding shape and would need its own ADR. The two new docs jobs land in CI for v0.3.5; a lift into pre-commit can happen later if maintainers ask. |

---

## 4. Reviewer acceptance block — revised

The original §1 acceptance block is amended:

- Item 1 (Import contract) — unchanged.
- Item 2 (Version coherence) — unchanged.
- Item 3 (Terminology) — extended with the §3.3 entries.
- Item 4 (Plan lifecycle) — unchanged.
- Item 5 (Status freshness) — extended: `docs/implementation_status.md` notes
  the upcoming v0.4.0 examples-repo split.
- Item 6 (CI surface) — extended: the `docs-contract` job runs **six**
  sub-checks (the four originals plus `--no-framework-imports` from §3.1
  and `--root-path-pinned` from §3.4 / V3_5-DOC-RE-01).
- Item 7 (Changelog) — unchanged.
- **New item 8.** Every existing notebook carries the v0.4.0 transition
  banner per §3.2.
- **New item 9 (docs reorganization).** The `docs/` root contains exactly
  five files: `README.md`, `quickstart.md`, `public_api.md`,
  `executive_summary.md`, `why_use_this.md`. Every other former root file
  is reachable under `docs/how-to/`, `docs/explanation/`, `docs/reference/`,
  or `docs/maintenance/` per the §3.4 mapping, with a one-page redirect
  stub at the old path.
- **New item 10 (link hygiene).** The `docs-links` job runs lychee in
  `--offline` mode over `docs/**/*.md`, `README.md`, `CHANGELOG.md`,
  `llms.txt`, and `notebooks/**/*.ipynb`, and is green on `main`.
- **New item 11 (markdown hygiene).** The `quality` job runs
  `markdownlint-cli2` over `docs/**/*.md`, `README.md`, `CHANGELOG.md`,
  `llms.txt`, and is green on `main`.

---

## 5. Out of scope

- Performing the actual notebook migration. That is the [v0.4.0 plan](v0_4_0_examples_repo_split_ultimate_plan.md).
- Removing existing notebooks from this repo. They stay through v0.3.5 and
  are removed in v0.4.0.
- Adding any new walkthrough notebook in v0.3.5 (none ships in v0.3.4 either,
  per the [v0.3.4 ultimate plan](v0_3_4_forecast_prep_contract_ultimate_plan.md)).
- **Publishing a public docs site** (GitHub Pages, Read the Docs, Netlify).
  MkDocs Material remains deferred per §3.5.
- **mkdocstrings sweep** — `docs/public_api.md` stays hand-curated; no
  autogenerated API page in v0.3.5.
- **Vale prose linting** — wording-policy sub-check is sufficient.
- **Pre-commit framework adoption** — CI gates are sufficient; no
  `.pre-commit-config.yaml` ships in v0.3.5.
- **Autogenerated changelog** — `CHANGELOG.md` continues to be maintained
  by hand.
- **Merging `golden_path.md` into `quickstart.md`** — both stay as distinct
  files in v0.3.5; revisit post-v0.4.0.
- **Splitting any docs by Diátaxis subtype within a bucket** (e.g.
  `reference/api/` vs `reference/contract/`). Single-level buckets only in
  v0.3.5.
- **Renaming any file** other than the path moves listed in §3.4. For
  example, `executive_summary.md` is not renamed to `overview.md`.
- **Editing the body content of moved files** beyond the mechanical
  fixes required to keep relative links valid (e.g. an in-page link
  `(architecture.md#section)` becomes `(../explanation/architecture.md#section)`).
  No prose rewrites land in v0.3.5.
- **Touching `docs/archive/`, `docs/input_papers/`, `docs/fixtures/`,
  `docs/img/`, `docs/code/`, `docs/theory/`, `docs/triage_methods/`,
  `docs/notebooks/`, `docs/releases/`, or `docs/maintenance/`** other
  than `maintenance/` receiving `wording_policy.md` (V3_5-DOC-RE-07).

---

## 6. Cross-references

- [v0.3.4 Forecast Prep Contract: Ultimate Release Plan](v0_3_4_forecast_prep_contract_ultimate_plan.md) — v0.3.4 shipped; the standalone revision overlay was folded into the ultimate plan and is intentionally absent.
- [v0.4.0 Examples Repo Split: Ultimate Release Plan](v0_4_0_examples_repo_split_ultimate_plan.md) — consumes the redirect-stub deletion item (V3_5-DOC-RE-10 → EX-CR-05).
- [aux_documents/developer_instruction_repo_scope.md](aux_documents/developer_instruction_repo_scope.md) — primary scope directive.

> [!NOTE]
> No separate `v0_3_5_documentation_quality_improvement_ultimate_plan.md` file
> ships. This revision overlay **is** the v0.3.5 plan of record. The naming is
> kept ("revision") for continuity with the audit trail and to signal that the
> document started life as an overlay against an earlier draft scope that was
> later abandoned.
