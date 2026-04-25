<!-- type: how-to -->
# Release Checklist

**Last reviewed:** 2026-04-13  
**Use this before every release (especially v0.1.0)**

## Pre-release preparation

- [ ] All items from the Repo Consolidation & Release-Readiness Update Plan are completed
- [ ] `CHANGELOG.md` has a new, clean section for the upcoming version (with highlights, stability changes, and migration notes if any)
- [ ] Version bumped in `pyproject.toml` (semantic versioning)
- [ ] `docs/reference/versioning.md` and stability tables (in README + `docs/reference/production_readiness.md`) are up to date
- [ ] Package name in `pyproject.toml` is set to `dependence-forecastability`
- [ ] Install instructions and badges in README are correct
- [ ] Golden-path example and smoke tests pass locally (`uv run python scripts/run_canonical_triage.py` or equivalent)
- [ ] `docs/releases/pypi_publication.md` exists and has been followed for any manual steps

## Local release pipeline (R7 — run before every release)

```bash
uv sync --all-extras --group dev
uv run pytest -q -ra
uv run ruff check .
uv run ty check
rm -rf dist/ build/
uv build
uv run twine check dist/*
python3.11 -m venv .venv-release-smoke
source .venv-release-smoke/bin/activate
pip install dist/dependence_forecastability-*.whl
python -c "import forecastability; print('import ok')"
forecastability --help
deactivate
rm -rf .venv-release-smoke
```

All steps must pass before proceeding to TestPyPI or production.

## TestPyPI dry run (R8 — required before first production release)

Requires TestPyPI API token in `~/.pypirc` or `TWINE_API_KEY` env var.
Full command path: `docs/releases/pypi_publication.md` → TestPyPI Dry Run section.

- [ ] `uv run twine upload --repository testpypi dist/*` succeeds
- [ ] Install from TestPyPI in a clean venv succeeds
- [ ] `import forecastability` works from TestPyPI-installed package
- [ ] `forecastability --help` works
- [ ] Project page at `https://test.pypi.org/project/dependence-forecastability/` renders correctly
- [ ] README renders without issues; metadata is complete

## Release execution

- [ ] Draft GitHub Release with tag `vX.Y.Z`
- [ ] Paste release notes from `CHANGELOG.md` into the GitHub release description
- [ ] Publish the release (triggers automated PyPI workflow)
- [ ] Verify package appears on PyPI under the chosen distribution name

## Post-release tasks

- [ ] Add/update PyPI badges in `README.md` top section
- [ ] Update `docs/how-to/golden_path.md`, quickstart, and examples with correct `pip install` command
- [ ] Update `docs/reference/implementation_status.md` if stability changed
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
