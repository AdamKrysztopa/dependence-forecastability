<!-- type: how-to -->
<!-- Last verified against current workflows: 2026-05-05 -->

# Release Checklist

Use this checklist before pushing a release tag.

## Prepare the tree

- [ ] Update the package version where the repo contract expects it.
- [ ] Update `CHANGELOG.md`.
- [ ] Add the required release notes file at `docs/releases/vX.Y.Z.md`.
- [ ] Confirm the branch is ready to tag from `main`.

## CI parity before tagging

Repo-contract parity:

```bash
uv sync --dev
uv run python scripts/check_repo_contract.py
uv run python scripts/check_markdown_links.py
uv run python scripts/check_readme_surface.py
```

Quality and docs-contract parity:

```bash
uv sync --dev --all-extras
uv run ruff check .
npx --yes markdownlint-cli2 "docs/**/*.md" README.md CHANGELOG.md llms.txt
uv run ty check
uv run pytest -q -ra -n auto
uv run python scripts/check_docs_contract.py --import-contract
uv run python scripts/check_docs_contract.py --version-coherence
uv run python scripts/check_docs_contract.py --terminology
uv run python scripts/check_docs_contract.py --plan-lifecycle
uv run python scripts/check_docs_contract.py --no-framework-imports
uv run python scripts/check_docs_contract.py --root-path-pinned
uv run python scripts/check_docs_contract.py --version-consistent
uv run python scripts/rebuild_lag_aware_mod_mrmr_regression_fixtures.py --verify
uv build
```

- [ ] If lychee offline is unavailable locally, note that `docs-links` remains CI-only and rely on the GitHub Actions run for that check.

## Smoke parity before tagging

Run the same showcase smoke commands as [smoke.yml](../../.github/workflows/smoke.yml):

```bash
uv sync --dev --all-extras
uv run scripts/run_showcase.py --no-rolling --no-bands
uv run scripts/run_showcase_covariant.py --fast
uv run scripts/run_showcase_fingerprint.py --smoke --quiet
uv run scripts/run_showcase_lagged_exogenous.py --smoke --quiet
uv run python scripts/run_routing_validation_report.py --smoke --no-real-panel
uv run scripts/run_ami_information_geometry_csv.py --help
uv run scripts/run_showcase_forecast_prep.py --smoke --quiet
uv run scripts/run_showcase_lag_aware_mod_mrmr.py --smoke --quiet
uv run scripts/run_showcase_lag_aware_catt_mod_mrmr.py --smoke --quiet
```

## Release-tag parity

Before pushing the tag, confirm that the tag matches the package version and that the release notes file exists.

```bash
TAG="vX.Y.Z"
PACKAGE_VERSION="$(awk -F'"' '/^version = "/ { print $2; exit }' pyproject.toml)"
test "${TAG}" = "v${PACKAGE_VERSION}"
test -f "docs/releases/${TAG}.md"

uv sync --dev --all-extras
uv run python -c "from forecastability.use_cases.run_covariant_analysis import run_covariant_analysis; print('covariant import OK')"
uv run python scripts/check_repo_contract.py --release-tag "${TAG}"
uv build
uv run twine check dist/*

wheel_path="$(ls dist/*.whl | head -1)"
python -m venv /tmp/release-wheel-smoke
/tmp/release-wheel-smoke/bin/pip install --quiet "${wheel_path}[causal]"
/tmp/release-wheel-smoke/bin/python - <<'PY'
import numpy as np

from forecastability import run_covariant_analysis, run_lag_aware_mod_mrmr
from forecastability.triage import LagAwareModMRMRConfig, PairwiseScorerSpec

target = np.tile(np.array([0.0, 1.0]), 16)
covariate = np.concatenate([target[1:], target[-1:]])
spec = PairwiseScorerSpec(
	name="pearson_abs",
	backend="scipy",
	normalization="none",
	significance_method="none",
)
config = LagAwareModMRMRConfig(
	forecast_horizon=1,
	availability_margin=0,
	candidate_lags=[1],
	relevance_scorer=spec,
	redundancy_scorer=spec,
	max_selected_features=1,
)
result = run_lag_aware_mod_mrmr(
	target=target,
	covariates={"driver": covariate},
	config=config,
)

assert callable(run_covariant_analysis)
assert len(result.selected) == 1
assert result.selected[0].feature_name == "x_driver_lag1"
print("wheel smoke test: stable facades OK")
PY
```

## Publish parity

The PyPI workflow reruns the package gates and repeats the same stable-facade wheel smoke test:

```bash
uv sync --dev --all-extras
uv run ruff check .
uv run ty check
uv run pytest -q -ra -n auto
uv build
uv run twine check dist/*

wheel_path="$(ls dist/*.whl | head -1)"
python -m venv /tmp/smoke-venv
/tmp/smoke-venv/bin/pip install --quiet "${wheel_path}[causal]"
/tmp/smoke-venv/bin/python - <<'PY'
import numpy as np

from forecastability import run_covariant_analysis, run_lag_aware_mod_mrmr
from forecastability.triage import LagAwareModMRMRConfig, PairwiseScorerSpec

target = np.tile(np.array([0.0, 1.0]), 16)
covariate = np.concatenate([target[1:], target[-1:]])
spec = PairwiseScorerSpec(
	name="pearson_abs",
	backend="scipy",
	normalization="none",
	significance_method="none",
)
config = LagAwareModMRMRConfig(
	forecast_horizon=1,
	availability_margin=0,
	candidate_lags=[1],
	relevance_scorer=spec,
	redundancy_scorer=spec,
	max_selected_features=1,
)
result = run_lag_aware_mod_mrmr(
	target=target,
	covariates={"driver": covariate},
	config=config,
)

assert callable(run_covariant_analysis)
assert len(result.selected) == 1
assert result.selected[0].feature_name == "x_driver_lag1"
print("wheel smoke test: stable facades OK")
PY
```

After publish, mirror the verification job:

```bash
uv run python scripts/check_published_release.py \
	--repository "OWNER/REPO" \
	--tag "vX.Y.Z" \
	--skip-github-release
```

- [ ] Expect a `repository_dispatch` notification to `forecastability-examples` after publish verification when `EXAMPLES_DISPATCH_TOKEN` is configured.

## Execute the release

1. Push the release commit to `main` and wait for `ci.yml` and `smoke.yml` to pass.
2. Create and push tag `vX.Y.Z`.
3. Confirm `release.yml` succeeds and publishes the GitHub release from `docs/releases/vX.Y.Z.md`.
4. Confirm `publish-pypi.yml` succeeds through publish, post-publish verification, and sibling notification.
