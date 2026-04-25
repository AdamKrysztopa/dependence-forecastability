<!-- type: reference -->
# Release 0.2.0 Tracking

Status tracker for Release 0.2.0 consolidation work. Keep this file updated during execution.

## Metadata

- Target release: `0.2.0`
- Release branch: `release-0.2.0-cleanup`
- Plan source: `docs/plan/v0_2_0_release_consolidation_plan_v2.md`

## Buckets

### Implemented

- [x] Release branch available and in use (`release-0.2.0-cleanup`)
- [x] Changelog scaffold for `0.2.0` added at top-level release sections

### In progress

- [ ] Maintainer review and approval of product surface freeze
- [ ] Ongoing migration checks to keep public-surface behavior stable while internal layout is cleaned

### Not started

- [ ] Full Phase 1 source layout cleanup execution
- [ ] Full Phase 2 examples/scripts/notebooks de-duplication
- [ ] Full Phase 3 notebook rationalization and archive note coverage
- [ ] Full Phase 4 documentation-code alignment sweep
- [ ] Full Phase 5 README renovation
- [ ] Full Phase 6 CI/CD hardening execution
- [ ] Full Phase 7 release validation checklist completion
- [ ] Full Phase 8 release execution and publication steps

## Product Surface Freeze (0.2.0)

The following surfaces are frozen for this release and must remain supported:

- [ ] deterministic core
- [ ] CLI
- [ ] HTTP API
- [ ] agent layer
- [ ] dashboard
- [ ] transport/MCP layer

Maintainer notes:

- Freeze means no intentional behavior removals in 0.2.0 without explicit deprecation notes and migration guidance.
- Internal module moves are allowed when compatibility facades preserve user-facing behavior.

## Public-Surface Compatibility Expectations

### Imports

- [ ] Existing documented public imports keep working, or are preserved via compatibility re-exports.
- [ ] Any intentional import-path changes include deprecation notices and migration examples.
- [ ] `import forecastability` remains valid.

### CLI behavior

- [ ] Existing command names remain available, or aliases are provided.
- [ ] Existing CLI options and output contracts remain stable unless documented as changed.
- [ ] CLI smoke test from installed wheel is tracked and passing before release.

### Documentation references

- [ ] README and docs command examples resolve to current script/module names.
- [ ] Cross-references to notebooks/examples/scripts remain valid after reorganization.
- [ ] Public API docs reflect actual exports and signatures.

### Deprecation policy

- [ ] Deprecations are additive, explicit, and documented in changelog + migration notes.
- [ ] No silent removals for frozen surfaces in 0.2.0.
- [ ] Candidate removals are tagged for a future minor release (for example, 0.3.0).

## Practical Update Cadence

Use this mini-loop while working:

1. Move one area at a time.
2. Update bucket status in this file immediately.
3. Record compatibility impact under the relevant subsection.
4. Link related PR/commit IDs inline when available.

## Change Log For This Tracker

- 2026-04-14: Initial tracker created for Phase 0 baseline.