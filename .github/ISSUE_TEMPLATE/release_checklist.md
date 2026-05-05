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
- [ ] Version bumped in `pyproject.toml` and release notes added at `docs/releases/vX.Y.Z.md`
- [ ] `docs/plan/README.md` points to the v0.4.3 LAM-F plan under `docs/plan/implemented/`, and the status matches current state: implemented in core repo; sibling-repo notebook follow-up remains

### CI parity and quality gates

- [ ] Repo-contract checks pass: `uv run python scripts/check_repo_contract.py`, `uv run python scripts/check_markdown_links.py`, `uv run python scripts/check_readme_surface.py`
- [ ] Markdown lint passes: `npx --yes markdownlint-cli2 "docs/**/*.md" README.md CHANGELOG.md llms.txt`
- [ ] Docs-contract checks pass: `uv run python scripts/check_docs_contract.py --import-contract`, `uv run python scripts/check_docs_contract.py --version-coherence`, `uv run python scripts/check_docs_contract.py --terminology`, `uv run python scripts/check_docs_contract.py --plan-lifecycle`, `uv run python scripts/check_docs_contract.py --no-framework-imports`, `uv run python scripts/check_docs_contract.py --root-path-pinned`, `uv run python scripts/check_docs_contract.py --version-consistent`
- [ ] `uv run ruff check .` — zero errors
- [ ] `uv run ty check` — zero errors
- [ ] `uv run pytest -q -ra -n auto` passes
- [ ] Lychee offline link check is green in CI (`docs-links` job); if `lychee` is not available locally, record CI status instead of blocking locally
- [ ] `uv run python scripts/rebuild_lagged_exog_regression_fixtures.py --verify` passes
- [ ] `uv run python scripts/rebuild_routing_validation_fixtures.py --verify` passes
- [ ] `uv run python scripts/rebuild_forecast_prep_regression_fixtures.py --verify` passes
- [ ] `uv run python scripts/rebuild_lag_aware_mod_mrmr_regression_fixtures.py --verify` passes

### Showcase smoke parity

- [ ] Univariate showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase.py --no-rolling --no-bands`
- [ ] Covariant showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase_covariant.py --fast`
- [ ] Fingerprint showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase_fingerprint.py --smoke --quiet`
- [ ] Lagged-exogenous triage showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase_lagged_exogenous.py --smoke --quiet`
- [ ] Routing validation report smoke runs clean: `MPLBACKEND=Agg uv run python scripts/run_routing_validation_report.py --smoke --no-real-panel`
- [ ] CSV geometry adapter CLI wiring smoke runs clean: `MPLBACKEND=Agg uv run scripts/run_ami_information_geometry_csv.py --help`
- [ ] Forecast prep contract showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase_forecast_prep.py --smoke --quiet`
- [ ] Lag-aware ModMRMR showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase_lag_aware_mod_mrmr.py --smoke --quiet`
- [ ] Catt-scored lag-aware ModMRMR showcase runs clean: `MPLBACKEND=Agg uv run scripts/run_showcase_lag_aware_catt_mod_mrmr.py --smoke --quiet`
- [ ] Routing validation report reviewed at `outputs/reports/routing_validation/report.md`
- [ ] Recipes page is present: check `docs/recipes/forecast_prep_to_external_frameworks.md` exists
- [ ] No framework runtime imports in core: `grep -r "import darts\|import mlforecast\|import statsforecast\|import nixtla" src/forecastability/ | grep -v ".pyc"` returns empty

### Lagged-exogenous triage invariants (v0.3.2+)

- [ ] Zero-lag ban holds: no `selected_for_tensor=True` at `lag=0` in default triage call (no `known_future_drivers` opt-in)
- [ ] Sparse lag map emitted: at least one `LaggedExogSelectionRow` per `(target, driver)` pair with `selected_for_tensor` populated
- [ ] Known-future opt-in path works: `known_future_drivers={"driver": True}` flips `lag=0` row to `selected_for_tensor=True`
- [ ] `run_showcase_lagged_exogenous.py --smoke` regression fixtures verify passes: `uv run python scripts/rebuild_lagged_exog_regression_fixtures.py --verify`
- [ ] Any change to `services/routing_policy_service.py` carries a matching fixture refresh under `docs/fixtures/routing_validation_regression/expected/`

### Build and publish validation

- [ ] `uv build` succeeds and produces both sdist and wheel
- [ ] `uv run twine check dist/*` — zero errors or warnings

### Tag, release, and publish workflows

- [ ] Release tag matches `pyproject.toml` version and `docs/releases/vX.Y.Z.md` exists before pushing `vX.Y.Z`
- [ ] Covariant import sanity check passes: `uv run python -c "from forecastability.use_cases.run_covariant_analysis import run_covariant_analysis; print('covariant import OK')"`
- [ ] Release-tag repo contract check passes: `uv run python scripts/check_repo_contract.py --release-tag vX.Y.Z`
- [ ] Git tag created and pushed:

  ```bash
  git tag vX.Y.Z
  git push origin vX.Y.Z
  ```

- [ ] `release.yml` completes: release-tag checks pass, dist artifacts are built and validated, stable-facade wheel smoke passes, and assets attach to the GitHub release
- [ ] `publish-pypi.yml` build-dist job completes: `uv run ruff check .`, `uv run ty check`, `uv run pytest -q -ra -n auto`, `uv build`, `uv run twine check dist/*`, and stable-facade wheel smoke passes
- [ ] PyPI trusted publishing job completes successfully in the `pypi` environment
- [ ] Post-publish verification passes: `uv run python scripts/check_published_release.py --repository AdamKrysztopa/dependence-forecastability --tag vX.Y.Z --skip-github-release`
- [ ] Sibling `repository_dispatch` notification to `forecastability-examples` is confirmed (or explicitly noted as skipped because `EXAMPLES_DISPATCH_TOKEN` is unset)
- [ ] PyPI release page verified at `https://pypi.org/project/dependence-forecastability/X.Y.Z/`

### Post-release

- [ ] GitHub release notes reviewed and accurate
- [ ] Milestone closed (if applicable)
