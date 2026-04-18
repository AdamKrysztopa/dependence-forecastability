<!-- type: reference -->
# v0.3.2 — Documentation Quality Improvement Plan

**Plan type:** Actionable documentation-quality improvement plan  
**Audience:** Maintainer, reviewer, documentation contributor  
**Target release:** `0.3.2`  
**Current released version:** `0.3.0`  
**Status:** Proposed  
**Last reviewed:** 2026-04-18  
**Builds on:** [v0.3.0 covariant plan](v0_3_0_covariant_informative_ultimate_plan.md)

---

## 1. Why this plan exists

The v0.3.0 covariant work materially expanded the repository surface, but the
documentation layer is no longer fully synchronized with the shipped code and
packaging metadata. The main gaps found in review are:

- public API examples that import symbols the top-level package does not export,
- stale implementation-status statements that describe already-closed gaps,
- mixed `0.2.0` vs `0.3.0` release banners across docs,
- missing doc-tooling in the current environment, which blocks normal docs QA.

This plan keeps the follow-up narrow: accuracy, consistency, and maintainability
of the in-repo docs surface.

---

## 2. Current tooling constraint

Docs checks were attempted but tooling is unavailable in the current environment:

```text
uv run mkdocs build (mkdocs not available)
vale . (vale not installed)
markdownlint . (markdownlint not installed)
```

This plan therefore separates:

- content corrections that can be done immediately with repo-local review,
- tooling enablement work needed for repeatable documentation QA later.

---

## 3. Work items

| ID | Item | Priority | Scope | Acceptance signal |
|---|---|---|---|---|
| DQ-01 | Public API example contract cleanup | P0 | `README.md`, `docs/public_api.md`, `docs/quickstart.md` | Every covariant quickstart import runs against the documented stable surface without hidden fallback knowledge. |
| DQ-02 | Release/version narrative alignment | P0 | `README.md`, `CHANGELOG.md`, `docs/public_api.md`, verification banners, packaging references | Docs no longer describe a release state that disagrees with `pyproject.toml` / `forecastability.__version__`. |
| DQ-03 | Implementation-status freshness pass | P1 | `docs/implementation_status.md`, `docs/README.md`, notebook/docs indexes | Status pages match shipped covariant behavior, examples, notebooks, and caveat boundaries. |
| DQ-04 | Cross-doc terminology normalization | P1 | `docs/theory/**`, `docs/code/**`, quickstarts, plan cross-references | Terms such as CrossAMI, CrosspAMI/pCrossAMI, conditioning scope, and PCMCI-AMI shipped-vs-proposal semantics are consistent repo-wide. |
| DQ-05 | Docs QA baseline | P1 | docs workflow notes, contributor docs, optional tooling install guidance | A maintainer can run at least one repeatable docs validation path even when full MkDocs/Vale/markdownlint are unavailable. |
| DQ-06 | Tooling enablement follow-up | P2 | dev docs / environment bootstrap | `mkdocs`, `vale`, and `markdownlint` are either installable from project guidance or explicitly removed from the expected workflow. |

---

## 4. Detailed actions

### DQ-01 — Public API example contract cleanup

- Decide whether `generate_covariant_benchmark` and `generate_directional_pair`
  belong in the stable top-level `forecastability` facade.
- If yes: export them and document them once.
- If no: rewrite all user-facing examples to import from
  `forecastability.utils.synthetic`, and make `docs/public_api.md` explicit that
  these imports are an intentional exception.

### DQ-02 — Release/version narrative alignment

- Reconcile `0.2.0` vs `0.3.0` references across docs and release metadata.
- Ensure "Last verified" banners are intentionally versioned, not stale leftovers.
- Keep docs and release-checklist references synchronized with package/runtime
  metadata.

### DQ-03 — Implementation-status freshness pass

- Update V3-F06/V3-F07/V3-F08 status text to match the current shipped facade,
  summary-row population, regression fixtures, and covariant walkthrough notebook.
- Remove statements that were true during an intermediate review but are false in
  the current tree.

### DQ-04 — Cross-doc terminology normalization

- Use one canonical spelling policy for:
  - `CrossAMI`
  - `CrosspAMI` / `pCrossAMI`
  - `target_only` / `full_mci` / `none`
  - `PCMCI-AMI-Hybrid`
- Where the shipped implementation differs from the original proposal, point to
  the same authoritative explanation instead of repeating drifting summaries.

### DQ-05 — Docs QA baseline

- Add a lightweight reviewer checklist that can be run with current repo tools:
  `rg`-based broken-term scans, version-string checks, and spot verification of
  documented imports against the actual package facade.
- Treat this as the minimum viable docs contract until richer tooling is present.

### DQ-06 — Tooling enablement follow-up

- Document how to install the missing docs tools, or explicitly mark them as
  optional and remove them from expected local validation instructions.
- Avoid a state where contributor docs prescribe commands that most maintainers
  cannot run in a fresh environment.

---

## 5. Non-goals

- Rewriting theory docs for new mathematical methods.
- Changing statistical behavior of TE, GCMI, PCMCI+, or PCMCI-AMI.
- Adding a hosted docs site or a large publishing pipeline.
- Reopening v0.3.0 feature scope beyond documentation accuracy and consistency.

---

## 6. Exit criteria

- [ ] All user-facing covariant examples import symbols from locations that are
      actually supported by the documented API contract.
- [ ] No documentation page claims a release/version state that conflicts with
      package metadata.
- [ ] `docs/implementation_status.md` is consistent with the current repo.
- [ ] At least one lightweight docs validation path is written down and usable in
      the current environment.
- [ ] The missing `mkdocs` / `vale` / `markdownlint` situation is either fixed or
      explicitly documented as an environment limitation.
