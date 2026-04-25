<!-- type: reference -->
# Repository Contract

This page defines the repository contract maintenance surface for release-truth and docs-integrity checks.

These checks keep documentation, repository metadata, and public-facing examples aligned with deterministic forecastability triage outputs (readiness, leakage boundaries, and informative-horizon context) without introducing framework-specific dependencies.

## Single Configuration Surface

- Canonical path: [repo_contract.yaml](../../repo_contract.yaml)
- Policy: [repo_contract.yaml](../../repo_contract.yaml) is the single configuration source for repository metadata checks and sync tooling.

## Path policy

- `canonical_paths` declares the canonical repository-relative targets that checkers/fixers should enforce.
- `deprecated_paths` declares stale repository-relative paths that should be rewritten to canonical targets.
- Keep path entries repository-relative and aligned with on-disk locations.

## Local Commands

Run all checks and fixers from repository root with uv:

```bash
uv run python scripts/check_repo_contract.py
```

```bash
uv run python scripts/sync_repo_contract.py --write
```

```bash
uv run python scripts/check_markdown_links.py
```

```bash
uv run python scripts/check_readme_surface.py
```

## Recommended Local Loop

1. Run `check_repo_contract.py` first to detect contract drift against [repo_contract.yaml](../../repo_contract.yaml).
2. If drift is fixable, run `sync_repo_contract.py --write` to apply canonical rewrites.
3. Re-run `check_repo_contract.py` to confirm the contract is clean after rewrites.
4. Run `check_markdown_links.py` to verify docs-integrity path resolution.
5. Run `check_readme_surface.py` to verify README surface claims remain release-truth compliant.

## Autofix PR Triage and Merge

When automation opens an autofix PR (typically from `sync_repo_contract.py --write` output), use this triage flow:

1. Confirm scope is contract-only:
   - Changes should map to [repo_contract.yaml](../../repo_contract.yaml) policy and documented canonical/deprecated paths.
   - Reject or split PRs that bundle unrelated content edits.
2. Validate locally on the PR branch:
   - `uv run python scripts/check_repo_contract.py`
   - `uv run python scripts/check_markdown_links.py`
   - `uv run python scripts/check_readme_surface.py`
3. Review diff semantics:
   - Verify rewrites preserve intended deterministic triage wording and do not alter readiness/leakage/informative-horizon meaning.
4. Merge criteria:
   - All three checks pass locally (or in CI) after the autofix commit.
   - Diff remains within release-truth/docs-integrity maintenance scope.
   - No framework-specific dependency or workflow surface is introduced.
5. Merge action:
   - Merge with the standard repository strategy after required approvals.
   - If checks still fail, push follow-up commit(s) in the same PR and re-run the loop above before merge.

## Notes

- Keep [repo_contract.yaml](../../repo_contract.yaml) authoritative and update this page only when operational behavior or command flow changes.
