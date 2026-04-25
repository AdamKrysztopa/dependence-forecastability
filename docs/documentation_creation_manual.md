<!-- type: how-to -->
# Documentation Creation Manual

Contributor-facing rules for creating and updating documentation in this repository.

## 1. Scope And Intent

This repository is a deterministic forecastability triage toolkit. Keep documentation aligned with that scope:

- Describe triage-first workflow before downstream model-family hand-off.
- Keep the core package framework-agnostic.
- Do not frame the project as a replacement for downstream forecasting libraries.

Pinned root references (do not move):

- [quickstart.md](quickstart.md)
- [public_api.md](public_api.md)

Terminology source of truth:

- [maintenance/wording_policy.md](maintenance/wording_policy.md)

## 2. Writing Standards

- Add a Diataxis type marker at the top of every new standalone doc.
- Keep claims mechanically verifiable and tied to repository surfaces.
- Prefer concise, operational language over broad marketing language.
- Use repository terms consistently: readiness, leakage risk, informative horizons, primary lags, seasonality structure, covariate informativeness.
- Keep examples minimal and plausible, and avoid duplicating implementation details.

## 3. Folder Placement Rules

Use the current doc layout first, then create new files.

### Current Diataxis Buckets

- How-to guides: [how-to/](how-to/)
- Explanations: [explanation/](explanation/)
- References: [reference/](reference/)

Current tutorial surface is transitional and notebook-based. See notebook policy below.

### Root-Level Docs

Use docs root only for high-signal entry pages or pinned references, including:

- [README.md](README.md)
- [quickstart.md](quickstart.md)
- [public_api.md](public_api.md)
- release-level entry/positioning pages already established at root

If a page fits a Diataxis bucket, prefer that bucket instead of root.

### Other Important Surfaces

- Maintenance/process docs: [maintenance/](maintenance/)
- Recipes (illustrative framework hand-off text, not core runtime behavior): [recipes/](recipes/)
- Planning docs: [plan/](plan/)
- Historical material: [archive/](archive/)

## 4. Link Style

- Use relative links for repository docs.
- Prefer descriptive link text over raw paths when possible.
- Keep links stable during moves by updating inbound references in the same change.
- Avoid unresolved placeholders or speculative links.

## 5. Redirect Stub Rules For Moved Docs

When moving a page, keep a redirect stub at the old path for one release cycle.

Stub template:

```markdown
<!-- type: reference -->
# Moved

This page moved to [<new path>](<new path>).
```

Rules:

- Use only this minimal body for stubs.
- Ensure the target link resolves.
- Track stub cleanup explicitly in the next release cleanup plan.

## 6. Notebook Policy

Notebooks are transitional in the core repository and are being moved in v0.4.0.

- Do not add new notebooks to this repository.
- Prefer docs pages, scripts in [../scripts/](../scripts/), and examples in [../examples/](../examples/).
- Keep reusable logic in package code, not notebook cells.

## 7. Required Validation Commands

Run the lightest relevant checks for docs-only changes:

```bash
uv run python scripts/check_docs_contract.py
```

If notebook paths or notebook policy text are touched, also run:

```bash
uv run python scripts/check_notebook_contract.py
```

If available in the current environment, additionally run markdown linting.

## 8. Definition Of Done

- [ ] Diataxis marker is present and correct.
- [ ] File is placed in the correct folder (or justified root placement).
- [ ] Terminology aligns with [maintenance/wording_policy.md](maintenance/wording_policy.md).
- [ ] Pinned root references remain intact: [quickstart.md](quickstart.md), [public_api.md](public_api.md).
- [ ] Links resolve and any moved-page stubs are in place.
- [ ] Required docs contract check passes.

## 9. Common Mistakes

- Writing model-fitting guidance before deterministic triage guidance.
- Treating framework-specific integrations as core runtime behavior.
- Adding new docs to root when they belong in a Diataxis bucket.
- Forgetting the Diataxis type marker.
- Moving docs without a redirect stub and backlink updates.
- Adding new notebooks even though notebook surface is transitional for v0.4.0.
- Drifting from canonical wording in [maintenance/wording_policy.md](maintenance/wording_policy.md).