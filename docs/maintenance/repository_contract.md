<!-- type: reference -->
# Repository Contract

This page documents the repository contract surface used by release-truth and docs-integrity maintenance automation.

## Contract file

- Canonical path: [repo_contract.yaml](../../repo_contract.yaml)
- Policy: this root-level contract is the single configuration source for repository metadata checks and sync tooling.

## Path policy

- `canonical_paths` declares the canonical repository-relative targets that checkers/fixers should enforce.
- `deprecated_paths` declares stale repository-relative paths that should be rewritten to canonical targets.
- Keep path entries repository-relative and aligned with on-disk locations.

## Phase 0 note

Phase 0 establishes the contract file and typed loader only. Checker, fixer, and CI workflow wiring land in later phases.
