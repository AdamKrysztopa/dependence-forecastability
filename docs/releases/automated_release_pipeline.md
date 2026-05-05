<!-- type: how-to -->
<!-- Last verified against current workflows: 2026-05-05 -->

# Automated Release Pipeline

This repository uses four GitHub Actions workflows for validation and release:

- [ci.yml](../../.github/workflows/ci.yml) validates pushes and pull requests to `main`.
- [smoke.yml](../../.github/workflows/smoke.yml) runs showcase smoke checks on pushes to `main`.
- [release.yml](../../.github/workflows/release.yml) validates a release tag and publishes the GitHub release.
- [publish-pypi.yml](../../.github/workflows/publish-pypi.yml) publishes to PyPI and verifies the published package.

## CI workflow

Trigger: `push` and `pull_request` on `main`.

| Job | Runtime | Current gate |
| --- | --- | --- |
| `repo-contract` | Python 3.12 | `scripts/check_repo_contract.py`, `scripts/check_markdown_links.py`, `scripts/check_readme_surface.py` |
| `quality` | Python 3.11 and 3.12 | `ruff`, `markdownlint-cli2`, `ty`, `pytest -q -ra -n auto`, `uv build` |
| `docs-contract` | Python 3.12 | `check_docs_contract.py` subcommands for import contract, version coherence, terminology, plan lifecycle, no-framework-imports, root-path-pinned, and version-consistent |
| `docs-links` | GitHub Action | `lychee-action` in offline mode over docs, README, CHANGELOG, and `llms.txt` |

Local parity commands:

```bash
uv sync --dev
uv run python scripts/check_repo_contract.py
uv run python scripts/check_markdown_links.py
uv run python scripts/check_readme_surface.py

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
uv build
```

> [!NOTE]
> `docs-links` runs lychee offline in CI. If the local lychee runtime is unavailable,
> treat that check as CI-only and rely on the GitHub Actions job for parity.

## Smoke workflow

Trigger: `push` on `main`.

Current smoke parity from [smoke.yml](../../.github/workflows/smoke.yml):

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

## Release tag workflow

Trigger: `push` on tags matching `v*`.

Current release-tag parity from [release.yml](../../.github/workflows/release.yml):

- The tag must match the package version in `pyproject.toml`.
- The release notes file `docs/releases/vX.Y.Z.md` must exist for the pushed tag.
- The workflow runs a covariant import sanity check before packaging.
- The workflow runs `scripts/check_repo_contract.py --release-tag ...`.
- The workflow builds artifacts with `uv build` and validates them with `uv run twine check dist/*`.
- The workflow smoke-installs the built wheel with the `[causal]` extra, imports the stable facade, checks that the older covariant entry point remains callable, and exercises the lag-aware public surface through `forecastability.triage` configs.

Local parity commands for the workflow, plus the lag-aware regression fixture verification used in release prep:

```bash
TAG="vX.Y.Z"
PACKAGE_VERSION="$(awk -F'"' '/^version = "/ { print $2; exit }' pyproject.toml)"
test "${TAG}" = "v${PACKAGE_VERSION}"
test -f "docs/releases/${TAG}.md"

uv sync --dev --all-extras
uv run python -c "from forecastability.use_cases.run_covariant_analysis import run_covariant_analysis; print('covariant import OK')"
uv run python scripts/check_repo_contract.py --release-tag "${TAG}"
uv run python scripts/rebuild_lag_aware_mod_mrmr_regression_fixtures.py --verify
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

After `build-dist`, the `publish-release` job creates or updates the GitHub release from the tag and uploads the built distribution artifacts.

## PyPI publication workflow

Trigger: `push` on tags matching `v*`. This workflow runs in parallel with `release.yml`.

Current publish parity from [publish-pypi.yml](../../.github/workflows/publish-pypi.yml):

- `build-dist` reruns `ruff`, `ty`, `pytest -q -ra -n auto`, `uv build`, and `uv run twine check dist/*`.
- `build-dist` smoke-installs the built wheel with the `[causal]` extra, imports the stable facade, checks that the older covariant entry point remains callable, and exercises the lag-aware public surface through `forecastability.triage` configs.
- `publish-pypi` uses trusted publishing in the `pypi` environment.
- `verify-published-release` runs `scripts/check_published_release.py --skip-github-release`.
- `notify-sibling` sends a `repository_dispatch` event to `forecastability-examples` after publish verification.

See [pypi_publication.md](pypi_publication.md) for the publish-specific setup and local wheel smoke commands, and see [release_checklist.md](release_checklist.md) for the full pre-tag sequence.
