<!-- type: reference -->
# v0.3.5 — Documentation Quality Improvement: Ultimate Release Plan

**Plan type:** Actionable release plan — documentation contract and quality hardening
**Audience:** Maintainer, reviewer, documentation contributor, Jr. developer
**Target release:** `0.3.5` — **ships last** (0.3.3 → 0.3.4 → 0.3.5) so docs cover the full new surface in one pass
**Current released version:** `0.3.4`
**Branch:** `feat/v0.3.5-docs-quality-hardening`
**Status:** Draft / Proposed
**Last reviewed:** 2026-04-22

> [!NOTE]
> **Cross-release ordering.** This release was originally drafted as the
> first in the 0.3.x trail, but the dependency chain reverses it: v0.3.3
> calibrates routing confidence (consumed by v0.3.4) and v0.3.4 introduces
> the headline `ForecastPrepContract`, two framework adapters, optional
> extras (`[darts]`, `[mlforecast]`, `[calendar]`), and a new walkthrough
> notebook. Running the docs hardening pass **once** after both ship avoids
> running the terminology / version-coherence / import-contract / status
> refresh sweep three times. The v0.3.5 ticket bodies below already account
> for the v0.3.3 and v0.3.4 surfaces.

**Companion refs:**

- [v0.3.0 Covariant Informative: Ultimate Release Plan](implemented/v0_3_0_covariant_informative_ultimate_plan.md)
- [v0.3.1 Forecastability Fingerprint & Model Routing: Ultimate Release Plan](implemented/v0_3_1_forecastability_fingerprint_model_routing_plan.md)
- [v0.3.2 Lagged-Exogenous Triage: Ultimate Release Plan](implemented/v0_3_2_lagged_exogenous_triage_ultimate_plan.md)
- [v0.3.3 Routing Validation & Benchmark Hardening: Ultimate Release Plan](v0_3_3_routing_validation_benchmark_hardening_plan.md) — shipped before this release
- [v0.3.4 Forecast Prep Contract: Ultimate Release Plan](v0_3_4_forecast_prep_contract_ultimate_plan.md) — shipped before this release

**Builds on:**

- implemented `0.3.0` public docs, theory pages, release notes
- implemented `0.3.1` fingerprint + routing docs, `docs/theory/forecastability_fingerprint.md`,
  `docs/theory/ami_information_geometry.md`
- implemented `0.3.2` lagged-exogenous docs, `docs/theory/lagged_exogenous_triage.md`,
  forward-link rewiring in `run_covariant_analysis._FORWARD_LINK`
- current `README.md`, `docs/quickstart.md`, `docs/public_api.md`,
  `docs/surface_guide.md`, `docs/implementation_status.md`, `docs/wording_policy.md`
- existing release-checklist (`.github/ISSUE_TEMPLATE/release_checklist.md`),
  smoke workflow (`.github/workflows/smoke.yml`), publish workflow
  (`.github/workflows/publish-pypi.yml`)
- existing `scripts/check_notebook_contract.py` precedent for cheap, scriptable
  doc-contract checks

---

## 1. Why this plan exists

After three feature releases (`0.3.0`, `0.3.1`, `0.3.2`) the documentation surface
is no longer a side artifact — it is the **product interface that downstream
agents, reviewers, and Jr. developers actually read first**. The `0.3.3` routing
calibration release and the `0.3.4` Forecast Prep Contract release will both
publish new public symbols and a new walkthrough notebook. If we ship those on
top of a docs surface that already contains version drift, half-true status
prose, ambiguous terminology, and import examples that point at internal
namespaces, the additive surfaces will inherit and amplify that confusion.

This release exists to **freeze a small, mechanical documentation contract
before any further user-visible surface ships**. The contract has four
invariants (formalised in §2). The release is small in code surface and very
small in math, but high in editorial discipline.

> [!IMPORTANT]
> v0.3.5 ships **no new statistical methods**, no new use cases, and no new
> public symbols. Any PR submitted under this plan that adds runtime behavior
> outside the docs-contract checks defined here is out of scope and must be
> moved to a separate plan.

### Planning principles

| Principle | Implication |
| --- | --- |
| Docs are part of the contract | Quickstarts and API examples must import from `forecastability` or `forecastability.triage` only |
| Mechanical over editorial | Every invariant in §2 must be checkable by `rg`, `python -c`, or a CI script — not by reviewer taste |
| Single source of truth | One canonical terminology table; one canonical version source; one canonical plan-lifecycle label set |
| Additive only | No deletion of existing public symbols; no rename of stable Pydantic fields; no breaking changes to `_FORWARD_LINK` constants |
| Lightweight QA first | Contributors without `mkdocs`/`vale`/`markdownlint` must still be able to run the docs-contract check |
| Plan lifecycle is mechanical | `Draft / Proposed`, `Implemented`, `Superseded` are the only allowed labels — and they live in YAML headers, not in body prose |
| Honesty over polish | Stale caveats are removed, not paraphrased |

### Reviewer acceptance block

`0.3.5` is successful only if all of the following are visible together:

1. **Import contract**
   - every code block in `README.md`, `docs/quickstart.md`, `docs/public_api.md`,
     `docs/surface_guide.md`, and the `examples/**/*.py` user-facing files
     imports from `forecastability` or `forecastability.triage` only
   - if a contributor-facing example legitimately depends on
     `forecastability.services` or `forecastability.utils` it carries an
     explicit `<!-- contributor-only -->` HTML comment and lives outside the
     user-quickstart pages
   - a CI check (V3_3-CI-01) executes `python -c "from forecastability import …"`
     for every documented top-level export
2. **Version coherence**
   - `pyproject.toml` `[project].version`, `src/forecastability/__init__.py`
     `__version__`, the `CHANGELOG.md` headline entry, and any README badge
     text agree exactly on the released version string
   - the same agreement holds at HEAD for the in-flight version (`0.3.5`)
   - a CI check (V3_3-CI-01) fails the build on any mismatch
3. **Terminology**
   - `docs/wording_policy.md` is the single source of truth for canonical token
     spellings and forbidden alternates (see §2.3 table)
   - `rg` patterns from §6.4 detect zero hits for forbidden alternates inside
     `README.md`, `docs/**/*.md`, and `examples/**/*.{py,md}`
4. **Plan lifecycle**
   - every plan file under `docs/plan/` carries a YAML header with `Status:`
     drawn from `{Draft / Proposed, Implemented, Superseded}`
   - implemented plans live under `docs/plan/implemented/`
   - the README "Roadmap" section (or its equivalent) lists active plans by
     filename, not by paraphrase
5. **Status freshness**
   - `docs/implementation_status.md` lists the shipped surfaces of `0.3.0`,
     `0.3.1`, `0.3.2` as **shipped**, not "in review" or "pending"
   - no body text in any non-archived doc claims a feature is "deferred" if
     `tests/` already exercises it
6. **CI surface**
   - a single workflow job named `docs-contract` runs the import check, the
     version-coherence check, and the terminology grep panel on every push and
     PR to `main`
7. **Changelog**
   - `CHANGELOG.md` `0.3.5` entry explicitly labels the release as a
     **documentation hardening release** with no behavior change

---

## 2. Documentation contract map — the four invariants

> [!IMPORTANT]
> Read this section before opening any docs PR for `0.3.5`. The contract is
> mechanical: every invariant has a check, and every check has a CI job. Editorial
> changes that do not preserve the invariants will be reverted.

### 2.1. Invariant A — Import resolution

Every public-facing example or doc snippet must import package symbols from
exactly one of two import roots:

- `forecastability` (the stable facade)
- `forecastability.triage` (the triage submodule re-export surface)

Formally, for every code-block snippet $c \in \mathcal{C}_{\text{public}}$ that
contains a Python `import` or `from … import …` statement targeting the
`forecastability` package, every imported symbol $s$ must satisfy:

$$\text{root}(s) \in \{\texttt{forecastability}, \texttt{forecastability.triage}\}$$

The set $\mathcal{C}_{\text{public}}$ is the union of code blocks in:

- `README.md`
- `docs/quickstart.md`
- `docs/public_api.md`
- `docs/surface_guide.md`
- every `*.py` file under `examples/` whose path does not contain `internal/`
  or `contributor/`

> [!NOTE]
> Internal modules (`forecastability.services.*`, `forecastability.use_cases.*`,
> `forecastability.utils.*`, `forecastability.adapters.*`,
> `forecastability.diagnostics.*`) are reachable but are **not** part of the
> public docs contract. They may appear in contributor docs, plan files, or
> tests, but never in user-facing quickstart code.

### 2.2. Invariant B — Version coherence

Define four version sources at HEAD:

- $v_{\text{toml}}$ — the value of `[project].version` in `pyproject.toml`
- $v_{\text{init}}$ — the value of `__version__` in
  `src/forecastability/__init__.py`
- $v_{\text{changelog}}$ — the topmost released version header in
  `CHANGELOG.md` matching the regex `^## \[(\d+\.\d+\.\d+)\]`
- $v_{\text{readme}}$ — the version segment of any version badge or "current
  release" sentence in `README.md`

The invariant is:

$$v_{\text{toml}} = v_{\text{init}} = v_{\text{changelog}} = v_{\text{readme}}$$

Pre-release branches are allowed to have $v_{\text{changelog}}$ contain an
`Unreleased` block above the topmost released header; the $v_{\text{readme}}$
text may then refer to the **last released** version, not the in-flight one.
The CI check encodes this rule explicitly.

### 2.3. Invariant C — Terminology

There is exactly one canonical token spelling per concept, and one canonical
display form for prose. The canonical table lives in `docs/wording_policy.md`
and is mirrored in this plan as §6.4.

The invariant is: for every concept $k$ with canonical token $t_k$ and forbidden
alternates $A_k = \{a_{k,1}, a_{k,2}, \ldots\}$, the search:

$$\text{count}_{\text{rg}}(a_{k,i}, \text{docs/, README.md, examples/}) = 0
\quad \forall a_{k,i} \in A_k$$

> [!NOTE]
> Test fixtures (`tests/`), historical changelog entries (`CHANGELOG.md`
> entries strictly older than `0.3.0`), and archived docs
> (`docs/archive/`) are **excluded** from the terminology scan.

### 2.4. Invariant D — Plan lifecycle is mechanical

Every file under `docs/plan/` (excluding `docs/plan/implemented/` and
`docs/plan/aux_documents/`) is in one of three states, expressed in the YAML
header `Status:` field:

- `Draft / Proposed` — under active editorial work, not on a release branch yet
- `Implemented` — the corresponding `vX.Y.Z` tag is published; the file has been
  moved to `docs/plan/implemented/` in the same release that ships the feature
- `Superseded` — replaced by a newer plan; the header carries `Superseded by:`
  with a relative link to the replacement

The invariant is: at HEAD, no plan file lives **outside** `docs/plan/implemented/`
while declaring `Status: Implemented`, and no plan file lives **inside**
`docs/plan/implemented/` while declaring anything else.

Formally, for every plan file $p$:

$$\text{path\_dir}(p) = \texttt{docs/plan/implemented/} \iff \text{status}(p) = \texttt{Implemented}$$

### 2.5. Contract-to-CI map

| Invariant | Check name | Implementation surface | Failure mode |
| --- | --- | --- | --- |
| A | `import-resolution` | `scripts/check_docs_contract.py --imports` | non-zero exit lists offending file:line |
| B | `version-coherence` | `scripts/check_docs_contract.py --version` | non-zero exit prints the four observed versions |
| C | `terminology-grep` | `scripts/check_docs_contract.py --terminology` | non-zero exit lists forbidden alternates and their hits |
| D | `plan-lifecycle` | `scripts/check_docs_contract.py --plan-lifecycle` | non-zero exit lists offending plan files |

A single GitHub Actions workflow job named `docs-contract` runs all four checks
on every push and PR. The script lives entirely in `scripts/` and depends only
on the standard library plus `tomllib` (built in for Python 3.11+).

---

## 3. Repo baseline — what already exists

| Layer | Module / Area | What it provides | Status |
| --- | --- | --- | --- |
| **README** | `README.md` | landing surface, install snippet, mini-quickstart | Stable, drift-prone |
| **Quickstart** | `docs/quickstart.md` | end-to-end Python snippet | Stable, must use facade only |
| **Public API** | `docs/public_api.md` | enumerated stable imports | Stable, must match `forecastability/__init__.py` |
| **Surface guide** | `docs/surface_guide.md` | shows triage/covariant surfaces | Stable, must match facade |
| **Implementation status** | `docs/implementation_status.md` | per-feature shipped/deferred narrative | Stable, drift-prone |
| **Theory docs** | `docs/theory/**` | mathematical positioning | Stable, terminology-sensitive |
| **Wording policy** | `docs/wording_policy.md` | canonical tokens (partial) | Stable, must become single source of truth |
| **Plans (active)** | `docs/plan/v0_3_*.md` (non-implemented) | upcoming-release narratives | Stable, lifecycle-sensitive |
| **Plans (done)** | `docs/plan/implemented/v0_3_*.md` | shipped-release narratives | Stable |
| **Plans (archive)** | `docs/plan/aux_documents/`, `docs/archive/` | superseded drafts | Stable, excluded from contract |
| **CHANGELOG** | `CHANGELOG.md` | release history | Stable, authoritative for $v_{\text{changelog}}$ |
| **Release metadata** | `pyproject.toml`, `src/forecastability/__init__.py` | runtime + build version | Stable, authoritative for $v_{\text{toml}}$, $v_{\text{init}}$ |
| **Examples (public)** | `examples/minimal_python.py`, `examples/minimal_covariant.py`, `examples/forecasting_triage_first.py`, `examples/minimal_cli.sh`, `examples/triage/`, `examples/covariant_informative/`, `examples/fingerprint/`, `examples/univariate/` | public usage stories | Stable, must obey Invariant A |
| **Examples (advanced)** | `examples/forecasting_triage_then_handoff.md` | narrative-only | Stable |
| **Validation tooling** | `scripts/check_notebook_contract.py`, `.github/workflows/{ci,smoke,publish-pypi,release}.yml`, `.github/ISSUE_TEMPLATE/release_checklist.md` | precedent for low-cost CI checks | Stable, must accept the new `docs-contract` job |
| **Notebooks** | `notebooks/walkthroughs/00_air_passengers_showcase.ipynb`, `01_covariant_informative_showcase.ipynb`, `02_forecastability_fingerprint_showcase.ipynb`, `03_lagged_exogenous_triage_showcase.ipynb` | walkthrough surface | Stable; only path-and-index hygiene needed |

> [!NOTE]
> The `data/raw/m4/` and `data/raw/causal_rivers/` paths are excluded from
> the sdist via `pyproject.toml` `[tool.hatch.build.targets.sdist].exclude` and
> remain out of scope for the docs-contract checks.

---

## 4. Feature inventory and overlap assessment

| ID | Feature | Phase | Overlap with existing | Genuine new work | Status |
| --- | --- | ---: | --- | --- | --- |
| V3_3-DQ-01 | Public API example contract cleanup | 1 | Edits existing user-facing docs | Force every public snippet to import from `forecastability` / `forecastability.triage` only | Proposed |
| V3_3-DQ-02 | Release / version narrative alignment | 1 | Edits `README.md`, `CHANGELOG.md`, `docs/public_api.md`, `pyproject.toml` if needed | Reconcile $v_{\text{toml}}$, $v_{\text{init}}$, $v_{\text{changelog}}$, $v_{\text{readme}}$ | Proposed |
| V3_3-DQ-03 | Implementation-status freshness pass | 1 | Edits `docs/implementation_status.md` | Replace stale "in review" / "pending" prose with shipped/deferred labels backed by tests | Proposed |
| V3_3-DQ-04 | Cross-doc terminology normalization | 1 | Edits theory docs, quickstart, README, surface guide | Promote `docs/wording_policy.md` to single source of truth and apply §6.4 table | Proposed |
| V3_3-DQ-05 | Docs QA baseline | 2 | Builds on `scripts/check_notebook_contract.py` precedent | Implement `scripts/check_docs_contract.py` with four sub-checks | Proposed |
| V3_3-DQ-06 | Tooling enablement follow-up | 2 | Edits contributor docs | Honest "tools optional" message + lightweight `uv run` invocation pattern | Proposed |
| V3_3-DQ-07 | Notebook / doc index hygiene | 2 | Edits `docs/notebooks/`, `examples/*/README.md` | Re-validate every walkthrough and example reference path | Proposed |
| V3_3-DQ-08 | Plan lifecycle labeling | 2 | Edits `docs/plan/**` headers | Apply `Status: {Draft / Proposed, Implemented, Superseded}` mechanically | Proposed |
| V3_3-CI-01 | Docs contract check in CI | 3 | Adds workflow job | New `docs-contract` job calling `scripts/check_docs_contract.py` | Proposed |
| V3_3-CI-02 | Release checklist hardening | 3 | Edits `.github/ISSUE_TEMPLATE/release_checklist.md` | Add docs-contract pass requirement before publish | Proposed |
| V3_3-D01 | README / quickstart refresh | 4 | Edits `README.md`, `docs/quickstart.md` | Refresh examples to reflect `0.3.1` fingerprint and `0.3.2` lagged-exog surfaces | Proposed |
| V3_3-D02 | Contributor docs refresh | 4 | Edits `docs/maintenance/`, `CONTRIBUTING.md` if present | Document the docs QA path and the `Status:` lifecycle policy | Proposed |
| V3_3-D03 | Changelog / migration notes | 4 | Edits `CHANGELOG.md` | Publish `0.3.5` entry as a no-behavior-change docs hardening release | Proposed |

---

## 5. Domain contracts — MANDATORY FIRST STEP

Although `0.3.5` does not introduce new Pydantic models, the **docs-contract
script** is itself a typed surface. The script must declare its result schema as
typed Python so that contributors can run it programmatically and so that
follow-up plans (`0.3.3`, `0.3.4`) can reuse it.

### 5.1. Typed docs-contract result models

**File:** `src/forecastability/diagnostics/docs_contract.py` (new, contributor-only;
explicitly **not** re-exported from `forecastability` or `forecastability.triage`)

```python
"""Typed result surface for the docs-contract checker.

This module is contributor-only. It is reachable from CI (via
``scripts/check_docs_contract.py``) but is not part of the public
``forecastability`` import surface.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DocsCheckName = Literal[
    "import-resolution",
    "version-coherence",
    "terminology-grep",
    "plan-lifecycle",
]
DocsCheckOutcome = Literal["passed", "failed", "skipped"]


class DocsViolation(BaseModel, frozen=True):
    """One violation discovered by a docs-contract sub-check."""

    check: DocsCheckName
    file_path: str
    line: int | None = None
    message: str
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class DocsCheckResult(BaseModel, frozen=True):
    """Result of one docs-contract sub-check."""

    check: DocsCheckName
    outcome: DocsCheckOutcome
    violations: list[DocsViolation] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DocsContractReport(BaseModel, frozen=True):
    """Aggregate report across all docs-contract sub-checks."""

    results: list[DocsCheckResult]
    overall_outcome: DocsCheckOutcome
    metadata: dict[str, str | int | float] = Field(default_factory=dict)

    @property
    def violation_count(self) -> int:
        return sum(len(r.violations) for r in self.results)
```

### 5.2. Boundary rules

- The `docs_contract` module lives under `diagnostics/`, not `services/` or
  `use_cases/`. It is a build-time / CI artifact, not a runtime surface.
- The module must not import any other `forecastability.*` symbol at top level
  beyond standard typing helpers; it does **not** participate in the runtime
  triage flow.
- The CLI script `scripts/check_docs_contract.py` is the only sanctioned entry
  point. Tests may import from `forecastability.diagnostics.docs_contract`
  directly.

### 5.3. Acceptance criteria

- typed result models importable from
  `forecastability.diagnostics.docs_contract` (contributor-only path)
- categorical fields use closed `Literal` labels
- `overall_outcome` is `"passed"` if and only if every sub-check is
  `"passed"` or `"skipped"`
- the module is **not** added to `src/forecastability/__init__.py`'s
  `__all__` and **not** documented in `docs/public_api.md`

---

## 6. Phased delivery

### Phase 1 — Content correctness and contract alignment

#### V3_3-DQ-01 — Public API example contract cleanup

**Goal.** Make every user-facing snippet obey Invariant A.

**File targets:**

- `README.md`
- `docs/quickstart.md`
- `docs/public_api.md`
- `docs/surface_guide.md`
- `examples/minimal_python.py`
- `examples/minimal_covariant.py`
- `examples/forecasting_triage_first.py`
- `examples/minimal_cli.sh`
- every `*.py` under `examples/triage/`, `examples/univariate/`,
  `examples/covariant_informative/`, `examples/fingerprint/`

**Responsibilities:**

- audit every Python `import`/`from` line in the listed files
- if a symbol is importable from `forecastability`, rewrite the import to use
  that root
- if a symbol is only available under `forecastability.triage`, rewrite to that
  root
- if a symbol is only available under an internal namespace
  (`forecastability.services.*`, `forecastability.utils.*`,
  `forecastability.use_cases.*`, `forecastability.adapters.*`,
  `forecastability.diagnostics.*`), file a follow-up note in §7 listing the
  symbol and either:
  1. promote it to the facade (additive re-export only), or
  2. move the example out of the public docs surface into
     `examples/contributor/` (creating that directory if needed)

**Implementation notes — before/after pattern:**

Before (forbidden in user-facing docs):

```python
from forecastability.use_cases.run_lagged_exogenous_triage import (
    run_lagged_exogenous_triage,
)
from forecastability.utils.types import LaggedExogBundle
```

After (must hold for user-facing docs):

```python
from forecastability import LaggedExogBundle, run_lagged_exogenous_triage
```

If `run_lagged_exogenous_triage` is not yet re-exported from the facade, the
ticket includes a one-line additive change to `src/forecastability/__init__.py`
to add it. The change is additive only; nothing existing is removed.

**Acceptance criteria:**

- `scripts/check_docs_contract.py --imports` exits zero
- every documented symbol resolves via
  `python -c "from forecastability import <symbol>"` or
  `python -c "from forecastability.triage import <symbol>"`
- no new `__all__` entry in `forecastability/__init__.py` is removed
- if any helper generator (e.g.
  `forecastability.utils.synthetic.generate_lagged_exog_panel`) is intentionally
  not re-exported, `docs/surface_guide.md` carries one paragraph explaining the
  policy and pointing contributors to the internal path

#### V3_3-DQ-02 — Release / version narrative alignment

**Goal.** Make Invariant B hold at HEAD.

**File targets:**

- `pyproject.toml`
- `src/forecastability/__init__.py`
- `CHANGELOG.md`
- `README.md`
- `docs/public_api.md` (only the "current released version" sentence, if any)

**Responsibilities:**

- read $v_{\text{toml}}$ from `pyproject.toml`
- read $v_{\text{init}}$ from `src/forecastability/__init__.py`
- read $v_{\text{changelog}}$ from `CHANGELOG.md`
- read $v_{\text{readme}}$ from `README.md` (badge text and any "current
  release" sentence)
- reconcile to a single value (`0.3.5` for the in-flight branch; `0.3.2` until
  the release branch is cut)
- remove any "verified on YYYY-MM-DD" banner that names a version older than
  $v_{\text{toml}}$

**Implementation notes — version-coherence check skeleton (used by V3_3-DQ-05):**

```python
import re
import tomllib
from pathlib import Path

VERSION_REGEX = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)


def read_pyproject_version(repo_root: Path) -> str:
    data = tomllib.loads((repo_root / "pyproject.toml").read_text())
    return str(data["project"]["version"])


def read_init_version(repo_root: Path) -> str:
    text = (repo_root / "src" / "forecastability" / "__init__.py").read_text()
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match is None:
        raise RuntimeError("__version__ not found in src/forecastability/__init__.py")
    return match.group(1)


def read_top_changelog_version(repo_root: Path) -> str:
    text = (repo_root / "CHANGELOG.md").read_text()
    match = VERSION_REGEX.search(text)
    if match is None:
        raise RuntimeError("No '## [X.Y.Z]' header found in CHANGELOG.md")
    return match.group(1)
```

**Acceptance criteria:**

- $v_{\text{toml}} = v_{\text{init}} = v_{\text{changelog}} = v_{\text{readme}}$
  at HEAD on the release branch
- `scripts/check_docs_contract.py --version` exits zero on the release branch
- on a pre-release branch, `Unreleased` is allowed in `CHANGELOG.md` and
  $v_{\text{readme}}$ may legally lag $v_{\text{toml}}$ by exactly one patch
  level — the script encodes this exception explicitly

#### V3_3-DQ-03 — Implementation-status freshness pass

**Goal.** Replace stale narrative with shipped/deferred labels backed by tests.

**File targets:**

- `docs/implementation_status.md`
- `docs/results_summary.md`
- `docs/executive_summary.md`
- `docs/why_use_this.md`

**Responsibilities:**

- for every feature listed, classify it into exactly one of:
  - **shipped** — at least one passing test under `tests/` exercises it, and
    a public symbol exists for it
  - **deferred** — explicitly named in a non-implemented plan as out of scope
    for the current release
  - **archived** — explicitly removed; carries a `removed_in: vX.Y.Z` note
- delete any prose that hedges shipped features as "in review", "pending
  follow-up", or "subject to change without notice" unless an open issue
  explicitly links the hedge

**Implementation notes — sample before/after:**

Before:

```markdown
- Lagged-exogenous triage is currently in review. The sparse selector is
  expected to ship in a follow-up release.
```

After:

```markdown
- Lagged-exogenous triage shipped in `0.3.2`. See
  `docs/theory/lagged_exogenous_triage.md` and the walkthrough at
  `notebooks/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb`.
```

**Acceptance criteria:**

- no occurrence of the strings `"in review"`, `"pending follow-up"`,
  `"to be confirmed"`, `"TBD"`, `"TBA"` in any non-archived doc, unless paired
  with a GitHub issue link in the same paragraph
- every "shipped" claim is matched by a test path or a public-symbol path
  that the docs-contract import check can resolve

#### V3_3-DQ-04 — Cross-doc terminology normalization

**Goal.** Make Invariant C hold; promote `docs/wording_policy.md` to single
source of truth.

**File targets:**

- `docs/wording_policy.md`
- `README.md`
- `docs/quickstart.md`
- `docs/public_api.md`
- `docs/surface_guide.md`
- `docs/theory/**.md`
- `examples/**/*.md`

**Responsibilities:**

- author the canonical terminology table (§6.4 below)
- copy the table verbatim into `docs/wording_policy.md`
- for every forbidden alternate, run `rg --no-heading -n` across `docs/`,
  `README.md`, and `examples/` and replace each hit with the canonical token
- record genuinely allowed exceptions (e.g. a quotation from an upstream
  paper) in a small `## Exceptions` section in `docs/wording_policy.md`

**Acceptance criteria:**

- `scripts/check_docs_contract.py --terminology` exits zero
- the §6.4 table appears verbatim inside `docs/wording_policy.md`
- exceptions list, if non-empty, is exhaustive

### Phase 2 — Docs QA infrastructure

#### V3_3-DQ-05 — Docs QA baseline (the contract checker)

**Goal.** Implement `scripts/check_docs_contract.py` and the typed result module
from §5.1.

**File targets:**

- `scripts/check_docs_contract.py` (new)
- `src/forecastability/diagnostics/docs_contract.py` (new, contributor-only)
- `tests/test_docs_contract.py` (new)

**Responsibilities:**

- expose four CLI flags: `--imports`, `--version`, `--terminology`,
  `--plan-lifecycle`
- expose `--all` to run every sub-check
- exit code `0` on overall pass; non-zero on any failure
- emit a JSON report when `--json` is passed (uses
  `DocsContractReport.model_dump_json(indent=2)`)

**Implementation notes — script entry point skeleton:**

```python
"""Docs-contract checker — run from repo root.

Usage:
    uv run python scripts/check_docs_contract.py --all
    uv run python scripts/check_docs_contract.py --imports --terminology
    uv run python scripts/check_docs_contract.py --all --json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from forecastability.diagnostics.docs_contract import (
    DocsCheckResult,
    DocsContractReport,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imports", action="store_true")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--terminology", action="store_true")
    parser.add_argument("--plan-lifecycle", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def run(repo_root: Path, args: argparse.Namespace) -> DocsContractReport:
    results: list[DocsCheckResult] = []
    if args.all or args.imports:
        results.append(check_imports(repo_root))
    if args.all or args.version:
        results.append(check_version(repo_root))
    if args.all or args.terminology:
        results.append(check_terminology(repo_root))
    if args.all or args.plan_lifecycle:
        results.append(check_plan_lifecycle(repo_root))
    overall = "passed" if all(r.outcome != "failed" for r in results) else "failed"
    return DocsContractReport(results=results, overall_outcome=overall)


def main() -> int:
    args = parse_args()
    if not (
        args.all or args.imports or args.version or args.terminology or args.plan_lifecycle
    ):
        print("Specify at least one check or --all", file=sys.stderr)
        return 2
    repo_root = Path(__file__).resolve().parents[1]
    report = run(repo_root, args)
    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        for result in report.results:
            print(f"[{result.outcome}] {result.check}")
            for v in result.violations:
                location = f"{v.file_path}:{v.line}" if v.line else v.file_path
                print(f"  - {location}: {v.message}")
    return 0 if report.overall_outcome == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

**Acceptance criteria:**

- script runs from repo root with `uv run python scripts/check_docs_contract.py --all`
- exits `0` on a clean tree
- prints actionable file:line diagnostics on failure
- `tests/test_docs_contract.py` exercises each sub-check on a small synthetic
  fixture under `tests/fixtures/docs_contract/`
- the script depends only on the standard library, `pydantic`, and the
  contributor-only diagnostics module — no new third-party dependency

#### V3_3-DQ-06 — Tooling enablement follow-up

**Goal.** Be honest about which tools are required vs optional.

**File targets:**

- `docs/maintenance/` (create if missing) — new file
  `docs/maintenance/docs_quality.md`
- `README.md` (one-line install pointer for the docs QA path)

**Responsibilities:**

- declare `mkdocs`, `vale`, `markdownlint` as **optional**
- declare `scripts/check_docs_contract.py --all` as **mandatory** (run by CI)
- document the lightweight invocation pattern that works in any developer
  shell with `uv` installed
- if a section claims a tool is mandatory, list it in
  `[dependency-groups].dev` of `pyproject.toml`

**Implementation notes — sample maintenance doc body:**

```markdown
## Mandatory checks

```bash
uv run python scripts/check_docs_contract.py --all
```

## Optional tools

The following tools are useful but not required for CI:

- `mkdocs` (with `mkdocs-material` theme) — local docs preview
- `vale` — prose linter
- `markdownlint` — Markdown structural lint

If a tool is missing, the relevant docs-contract sub-check is reported as
`skipped`, not `failed`.
```

**Acceptance criteria:**

- no contributor doc prescribes a command that requires a missing optional
  tool to be installed
- `scripts/check_docs_contract.py` reports `skipped` for any sub-check whose
  dependency is missing
- `README.md` contains exactly one pointer to the maintenance doc

#### V3_3-DQ-07 — Notebook / doc index hygiene

**Goal.** Ensure every linked walkthrough and example path resolves.

**File targets:**

- `docs/notebooks/` index files
- `examples/*/README.md` (any present index file under each example tree)
- `README.md` "Walkthroughs" section, if present
- `docs/quickstart.md` "See also" section, if present

**Responsibilities:**

- cross-check every relative link in the listed files against the actual
  file system
- delete or rewrite any link that resolves to a 404 path
- ensure the four canonical walkthroughs are listed:
  - `notebooks/walkthroughs/00_air_passengers_showcase.ipynb`
  - `notebooks/walkthroughs/01_covariant_informative_showcase.ipynb`
  - `notebooks/walkthroughs/02_forecastability_fingerprint_showcase.ipynb`
  - `notebooks/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb`

**Implementation notes — `rg` pattern for stale paths:**

```bash
rg --no-heading -n -o '\[[^\]]+\]\(([^)]+\.(md|ipynb|py))\)' \
   docs/ README.md examples/ \
   | sort -u
```

The Phase 2 follow-up walks each captured path and flags any miss as a
`docs-contract` violation under a new `--links` sub-check (deferred to v0.3.3
unless a contributor volunteers it earlier).

**Acceptance criteria:**

- every relative link in the listed files resolves
- the four canonical walkthroughs are referenced exactly once each per index
  file (no duplicates)

#### V3_3-DQ-08 — Plan lifecycle labeling

**Goal.** Make Invariant D hold.

**File targets:**

- every `*.md` under `docs/plan/` (excluding `aux_documents/` and `archive/`)

**Responsibilities:**

- audit every plan file's YAML header
- if `Status:` is missing, add it
- if a plan declares `Status: Implemented` but lives outside
  `docs/plan/implemented/`, move it (using `git mv`) and update inbound links
- if a plan lives under `docs/plan/implemented/` but does not declare
  `Status: Implemented`, update the header
- for superseded plans, add `Superseded by: <relative path>`

**Acceptance criteria:**

- `scripts/check_docs_contract.py --plan-lifecycle` exits zero
- no plan declares `Status: Implemented` while still living in the active
  `docs/plan/` root

### Phase 3 — CI / release hygiene

#### V3_3-CI-01 — Docs contract check in CI

**Goal.** Wire the new script into CI.

**File targets:**

- `.github/workflows/ci.yml` (add a new job named `docs-contract`)

**Responsibilities:**

- the new job runs on every push and PR to `main`
- the job uses the same Python toolchain as the existing `tests` job
- the job calls `uv run python scripts/check_docs_contract.py --all`

**Implementation notes — sample workflow snippet:**

```yaml
jobs:
  docs-contract:
    name: docs-contract
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Set up Python
        run: uv python install 3.12
      - name: Sync dev dependencies
        run: uv sync --group dev
      - name: Run docs contract checks
        run: uv run python scripts/check_docs_contract.py --all
```

**Acceptance criteria:**

- the `docs-contract` job appears as a required check on the `main` branch
  protection rules (documented in `.github/CODEOWNERS` or branch-protection
  notes; not blocking if the repo does not currently use branch protection)
- the job runs in under 60 seconds on a clean repo
- the job's output is human-readable on failure

#### V3_3-CI-02 — Release checklist hardening

**Goal.** Force docs-contract pass before publish.

**File targets:**

- `.github/ISSUE_TEMPLATE/release_checklist.md`

**Responsibilities:**

- add a checkbox: "`uv run python scripts/check_docs_contract.py --all` passes
  on the release commit"
- add a checkbox: "Version coherence holds at the release tag
  (`pyproject.toml`, `__init__.py`, `CHANGELOG.md`, `README.md`)"

**Acceptance criteria:**

- the release-checklist template carries both checkboxes
- the wording matches the canonical script invocation in V3_3-DQ-05

### Phase 4 — Public and contributor doc refresh

#### V3_3-D01 — README / quickstart refresh

**Goal.** Refresh the public landing surface to reflect `0.3.1` and `0.3.2`.

**File targets:**

- `README.md`
- `docs/quickstart.md`

**Responsibilities:**

- ensure the README quickstart shows `run_triage` (univariate) plus a one-line
  pointer to `run_covariant_analysis` and `run_lagged_exogenous_triage`
- ensure `docs/quickstart.md` contains a section "Hand-off after triage" that
  forward-links to the v0.3.4 Forecast Prep Contract plan and notes that the
  contract itself ships in `0.3.4`
- do not preview unreleased symbols from `0.3.3` or `0.3.4` in user-facing
  examples (only narrative pointers are allowed)

**Acceptance criteria:**

- every code block in the refreshed README and quickstart obeys Invariant A
- no code block imports a symbol that does not exist in the released `0.3.2`
  facade
- the "Hand-off after triage" section links to the v0.3.4 plan file by
  relative path

#### V3_3-D02 — Contributor docs refresh

**Goal.** Make the docs QA path discoverable.

**File targets:**

- `docs/maintenance/docs_quality.md` (created in V3_3-DQ-06)
- `README.md` (one-line "Maintenance" pointer)

**Responsibilities:**

- declare the canonical script invocation as the single supported docs QA
  command
- declare the plan lifecycle policy from §2.4 in one paragraph

**Acceptance criteria:**

- contributor docs include the docs QA command exactly once
- the plan lifecycle policy is stated once and linked from
  `docs/plan/README.md` if that index file exists

#### V3_3-D03 — Changelog / migration notes

**Goal.** Publish `0.3.5` as a no-behavior-change docs hardening release.

**File targets:**

- `CHANGELOG.md`

**Implementation notes — sample changelog entry:**

```markdown
## [0.3.5] - 2026-04-DD

### Added
- `scripts/check_docs_contract.py` — mechanical four-invariant docs contract
  checker (import resolution, version coherence, terminology, plan lifecycle).
- `forecastability.diagnostics.docs_contract` — typed result models for the
  docs contract checker (contributor-only; not re-exported from the public
  facade).
- `docs/maintenance/docs_quality.md` — single source of truth for the docs QA
  workflow.
- CI job `docs-contract` running on every push and PR.

### Changed
- `docs/wording_policy.md` is now the single source of truth for canonical
  terminology tokens. All forbidden alternates have been removed from public
  docs.
- `docs/implementation_status.md` lists shipped/deferred features only;
  stale "in review" wording has been removed.
- Every user-facing snippet in `README.md`, `docs/quickstart.md`,
  `docs/public_api.md`, `docs/surface_guide.md`, and `examples/` now imports
  from `forecastability` or `forecastability.triage` only.

### Notes
- This is a documentation-quality release. There are **no behavior changes**
  in the runtime triage, covariant, fingerprint, or lagged-exogenous surfaces.
```

**Acceptance criteria:**

- the entry is dated and labelled as a docs hardening release
- no "Removed" section is present (the release is additive)
- the entry is the topmost `## [X.Y.Z]` block in `CHANGELOG.md`

---

## 6.4. Canonical terminology table

> [!IMPORTANT]
> This is the single source of truth. `docs/wording_policy.md` must mirror this
> table verbatim. Any new terminology added by `0.3.3` or `0.3.4` extends this
> table; no parallel terminology table may exist.

| Canonical token (code) | Display form (prose) | Forbidden alternates |
| --- | --- | --- |
| `cross_ami` | CrossAMI | `cross-AMI`, `crossAMI`, `Cross-AMI`, `cross ami` |
| `cross_pami` | CrosspAMI | `cross-pAMI`, `crosspAMI`, `Cross-pAMI`, `cross pami`, `pCrossAMI` |
| `cross_correlation` | cross-correlation | `crosscorrelation`, `Cross-Correlation`, `XCorr` (in prose), `xcorr` (in prose) |
| `pami` | pAMI | `pAmi`, `partial AMI`, `partial-AMI`, `partialAMI`, `Partial AMI` |
| `ami` | AMI | `Auto Mutual Information`, `auto-mutual-information`, `auto_mutual_information` |
| `transfer_entropy` | transfer entropy | `Transfer Entropy`, `TransferEntropy`, `TE` (in prose; allowed only in code identifiers and tables) |
| `pcmci` | PCMCI | `Pcmci`, `pcmci+`, `PCMCI+` (when referring to the algorithm; the `+` variant is acceptable only in citation context) |
| `pcmci_ami` | PCMCI-AMI | `pcmci-ami`, `pcmciami`, `pcmci_AMI`, `PCMCI_AMI` |
| `pcmci_ami_hybrid` | PCMCI-AMI-Hybrid | `pcmci-ami-hybrid`, `PCMCI-AMI hybrid`, `pcmci_ami_v3` |
| `target_only` | target-only conditioning | `target only`, `target-only-conditioning` (in code identifiers) |
| `full_mci` | full-MCI conditioning | `Full MCI`, `full mci`, `fullMCI` |
| `lag_role` | lag role | `lagRole`, `Lag Role` (only allowed as table header) |
| `tensor_role` | tensor role | `tensorRole`, `Tensor Role` (only allowed as table header) |
| `instant` | instant (`lag = 0`) | `contemporaneous` (avoid as the canonical label; `instant` is the canonical token) |
| `predictive` | predictive (`lag ≥ 1`) | `lagged` (avoid as the canonical label) |
| `known_future` | known-future | `knownFuture`, `known future`, `future-known` |
| `LaggedExogBundle` | LaggedExogBundle | `LaggedExogenousBundle`, `lagged_exog_bundle` (in code identifiers, the snake_case is reserved for variables) |
| `ForecastabilityFingerprint` | Forecastability Fingerprint | `Forecastability fingerprint`, `forecastability_fingerprint` (in prose) |
| `RoutingRecommendation` | routing recommendation | `Routing Recommendation`, `routingRecommendation` |
| `information_mass` | information mass | `Information Mass`, `informationMass` |
| `information_horizon` | information horizon | `Information Horizon`, `informationHorizon` |
| `information_structure` | information structure | `Information Structure`, `informationStructure` |
| `nonlinear_share` | nonlinear share | `Nonlinear Share`, `nonlinearShare`, `non-linear share` |
| `ForecastPrepContract` | Forecast Prep Contract | `ForecastingHandOffSpec`, `ForecastPrepSpec`, `ModelInputRecommendation` (these remain doc-only aliases mentioned at most once with a redirect) |
| `build_forecast_prep_contract` | `build_forecast_prep_contract()` | `build_handoff_spec`, `build_prep_spec` |

The `rg` panel that V3_3-DQ-04 must drive to zero hits is:

```bash
rg --no-heading -n \
  -e 'cross-AMI' -e 'crossAMI' -e 'Cross-AMI' \
  -e 'cross-pAMI' -e 'crosspAMI' -e 'Cross-pAMI' -e 'pCrossAMI' \
  -e 'partial AMI' -e 'partial-AMI' -e 'partialAMI' \
  -e 'Auto Mutual Information' -e 'auto-mutual-information' \
  -e 'Transfer Entropy' -e 'TransferEntropy' \
  -e 'pcmci-ami' -e 'pcmciami' -e 'PCMCI_AMI' \
  -e 'PCMCI-AMI hybrid' -e 'pcmci_ami_v3' \
  -e 'fullMCI' -e 'Full MCI' \
  -e 'knownFuture' -e 'future-known' \
  -e 'LaggedExogenousBundle' \
  -e 'ForecastingHandOffSpec' -e 'ForecastPrepSpec' \
  docs/ README.md examples/
```

The script encoding of this panel lives in
`scripts/check_docs_contract.py::check_terminology`.

---

## 7. Non-goals

- adding new statistical methods, new dependence estimators, or new
  significance machinery
- rewriting any theory doc for new mathematics
- creating a hosted MkDocs Material site (the optional tooling clause
  intentionally keeps that off the critical path)
- changing package runtime behavior except where strictly necessary to repair
  a doc-contract violation (e.g. additive re-export of a symbol that the
  quickstart genuinely needs)
- reopening feature scope from `0.3.0`, `0.3.1`, `0.3.2`
- previewing `0.3.3` routing-validation surfaces or `0.3.4` Forecast Prep
  Contract surfaces in user-facing docs (narrative forward-links are allowed,
  code snippets are not)
- introducing any new dependency in `pyproject.toml` `[project].dependencies`
- promoting any internal namespace (`forecastability.services.*`,
  `forecastability.utils.*`, `forecastability.use_cases.*`) into the public
  facade unless V3_3-DQ-01 surfaces a documented user-facing example that
  genuinely requires it

---

## 8. Exit criteria

- [ ] V3_3-DQ-01 is **Done** — every user-facing snippet imports from
      `forecastability` or `forecastability.triage` only
- [ ] V3_3-DQ-02 is **Done** — $v_{\text{toml}} = v_{\text{init}} =
      v_{\text{changelog}} = v_{\text{readme}}$ holds at HEAD
- [ ] V3_3-DQ-03 is **Done** — `docs/implementation_status.md` lists
      shipped/deferred features only, with no stale "in review" prose
- [ ] V3_3-DQ-04 is **Done** — `docs/wording_policy.md` mirrors §6.4 verbatim
      and the terminology grep panel returns zero hits
- [ ] V3_3-DQ-05 is **Done** — `scripts/check_docs_contract.py` and
      `forecastability.diagnostics.docs_contract` exist with full test
      coverage
- [ ] V3_3-DQ-06 is **Done** — `docs/maintenance/docs_quality.md` declares
      the mandatory script and the optional tools honestly
- [ ] V3_3-DQ-07 is **Done** — every relative link in the listed index files
      resolves
- [ ] V3_3-DQ-08 is **Done** — every plan file's `Status:` matches its
      directory placement
- [ ] V3_3-CI-01 is **Done** — the `docs-contract` job runs on every push
      and PR
- [ ] V3_3-CI-02 is **Done** — the release checklist requires the script to
      pass before publish
- [ ] V3_3-D01 is **Done** — README and quickstart refreshed
- [ ] V3_3-D02 is **Done** — contributor docs refreshed
- [ ] V3_3-D03 is **Done** — `0.3.5` changelog entry published as a
      no-behavior-change release

---

## 9. Recommended implementation order

```text
1. V3_3-DQ-04 (terminology table) and V3_3-DQ-08 (plan lifecycle) — low risk, high cleanup yield
2. V3_3-DQ-05 — implement the contract checker and its typed result module
3. V3_3-DQ-01 — fix imports under the script's --imports check
4. V3_3-DQ-02 — fix version coherence under the script's --version check
5. V3_3-DQ-03 — implementation-status freshness pass
6. V3_3-DQ-07 — notebook / doc index hygiene
7. V3_3-DQ-06 — tooling enablement follow-up (after the script is stable)
8. V3_3-CI-01 + V3_3-CI-02 — wire the script into CI and the release checklist
9. V3_3-D01, V3_3-D02 — public and contributor doc refresh
10. V3_3-D03 — changelog entry, then tag v0.3.5
```
