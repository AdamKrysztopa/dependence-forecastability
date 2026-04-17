---
name: Release checklist
about: Checklist to complete before creating and publishing a new release
title: "Release vX.Y.Z checklist"
labels: release
assignees: ""
---

## Pre-release checklist

### Documentation and versioning
- [ ] Changelog updated in `CHANGELOG.md` with all notable changes
- [ ] Version bumped in `pyproject.toml` (and consistent with the git tag)
- [ ] All V3-CI and V3-F items marked Done in plan docs

### Quality gates
- [ ] `uv run pytest -q -ra` passes on Python 3.11
- [ ] `uv run pytest -q -ra` passes on Python 3.12
- [ ] `uv run ruff check .` — zero errors
- [ ] `uv run ty check` — zero errors

### Showcase and notebook validation
- [ ] Univariate showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase.py --no-rolling`
- [ ] Covariant showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase_covariant.py --fast`
- [ ] Notebook contract validated: `uv run python scripts/check_notebook_contract.py`

### Build and publish validation
- [ ] `uv build` succeeds and produces both sdist and wheel
- [ ] `uv run twine check dist/*` — zero errors or warnings

### Release mechanics
- [ ] Git tag created and pushed:
  ```bash
  git tag vX.Y.Z
  git push origin vX.Y.Z
  ```
- [ ] `publish-pypi.yml` CI run completes successfully (OIDC trusted publishing)
- [ ] `release.yml` CI run completes and GitHub release is created
- [ ] PyPI release page verified at https://pypi.org/p/dependence-forecastability

### Post-release
- [ ] GitHub release notes reviewed and accurate
- [ ] Milestone closed (if applicable)
