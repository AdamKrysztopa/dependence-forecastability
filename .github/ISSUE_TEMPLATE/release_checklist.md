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
- [ ] `uv run python scripts/rebuild_lagged_exog_regression_fixtures.py --verify` passes
- [ ] `uv run python scripts/rebuild_routing_validation_fixtures.py --verify` passes

### Showcase and notebook validation
- [ ] Univariate showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase.py --no-rolling`
- [ ] Covariant showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase_covariant.py --fast`
- [ ] Fingerprint showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase_fingerprint.py --smoke`
- [ ] Lagged-exogenous triage showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase_lagged_exogenous.py --smoke`
- [ ] Routing validation report generated and reviewed at `outputs/reports/routing_validation/report.md`
- [ ] Notebook contract validated: `uv run python scripts/check_notebook_contract.py`

### Lagged-exogenous triage invariants (v0.3.2+)
- [ ] Zero-lag ban holds: no `selected_for_tensor=True` at `lag=0` in default triage call (no `known_future_drivers` opt-in)
- [ ] Sparse lag map emitted: at least one `LaggedExogSelectionRow` per `(target, driver)` pair with `selected_for_tensor` populated
- [ ] Known-future opt-in path works: `known_future_drivers={"driver": True}` flips `lag=0` row to `selected_for_tensor=True`
- [ ] `run_showcase_lagged_exogenous.py --smoke` regression fixtures verify passes: `uv run python scripts/rebuild_lagged_exog_regression_fixtures.py --verify`
- [ ] Any change to `services/routing_policy_service.py` carries a matching fixture refresh under `docs/fixtures/routing_validation_regression/expected/`

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
