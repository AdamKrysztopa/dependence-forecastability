<!-- type: how-to -->
# Release Checklist

**Last reviewed:** 2026-04-13  
**Use this before every release (especially v0.1.0)**

## Pre-release preparation

- [ ] All items from the Repo Consolidation & Release-Readiness Update Plan are completed
- [ ] `CHANGELOG.md` has a new, clean section for the upcoming version (with highlights, stability changes, and migration notes if any)
- [ ] Version bumped in `pyproject.toml` (semantic versioning)
- [ ] `docs/versioning.md` and stability tables (in README + `docs/production_readiness.md`) are up to date
- [ ] Package name in `pyproject.toml` is set to a conflict-free name (`dependence-forecastability` recommended)
- [ ] Install instructions and badges in README are correct
- [ ] Golden-path example and smoke tests pass locally (`uv run scripts/run_canonical_examples.py` or equivalent)
- [ ] `docs/releases/pypi_publication.md` exists and has been followed for any manual steps

## Release execution

- [ ] Draft GitHub Release with tag `vX.Y.Z`
- [ ] Paste release notes from `CHANGELOG.md` into the GitHub release description
- [ ] Publish the release (triggers automated PyPI workflow)
- [ ] Verify package appears on PyPI under the chosen distribution name

## Post-release tasks

- [ ] Add/update PyPI badges in `README.md` top section
- [ ] Update `docs/golden_path.md`, quickstart, and examples with correct `pip install` command
- [ ] Update `docs/implementation_status.md` if stability changed
- [ ] Post announcement (LinkedIn + X)
- [ ] Verify installation: `pip install dependence-forecastability` works cleanly

## Stability decision reminders

| Surface | Release status |
|---|---|
| Core domain & deterministic triage | Stable |
| CLI / HTTP API | Beta |
| MCP / agent narration | Experimental |

> [!IMPORTANT]
> Do not promote experimental surfaces without explicit criteria and a stability review.
