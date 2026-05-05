<!-- type: how-to -->
<!-- Last verified against current workflows: 2026-05-05 -->

# PyPI Publication Flow

This repository publishes to PyPI through [publish-pypi.yml](../../.github/workflows/publish-pypi.yml) using GitHub OIDC trusted publishing. Long-lived PyPI API tokens are not part of the release path.

## One-time maintainer setup

1. Create or claim the `dependence-forecastability` project on PyPI.
2. Add a Trusted Publisher on PyPI for the GitHub repository that owns `publish-pypi.yml`.
3. Set the workflow file to `publish-pypi.yml` and the environment to `pypi`.
4. Protect the `pypi` environment in GitHub as needed for your release process.

## What the workflow does on a tag push

Trigger: `push` on tags matching `v*`.

### `build-dist`

The workflow syncs development dependencies with extras and runs:

```bash
uv run ruff check .
uv run ty check
uv run pytest -q -ra -n auto
uv build
uv run twine check dist/*
```

It then smoke-installs the built wheel with the `[causal]` extra, imports the stable facade, checks that the older covariant entry point remains callable, and exercises the lag-aware public surface through `forecastability.triage` configs in the isolated environment.

### `publish-pypi`

The publish job downloads the built artifacts and runs `pypa/gh-action-pypi-publish@release/v1` in the `pypi` environment with `id-token: write`.

### `verify-published-release`

After publishing, the workflow runs:

```bash
uv run python scripts/check_published_release.py \
  --repository "OWNER/REPO" \
  --tag "vX.Y.Z" \
  --skip-github-release
```

`--skip-github-release` is intentional: GitHub release creation is validated by [release.yml](../../.github/workflows/release.yml), and the two tag workflows run independently.

### `notify-sibling`

After publish verification, the workflow sends a `repository_dispatch` event named `core_release` to `forecastability-examples`. The payload carries the released version, the tag, and the PyPI project URL. If `EXAMPLES_DISPATCH_TOKEN` is not configured, the workflow logs a skip and exits cleanly.

## Local parity before pushing the tag

Use these commands to match the publish workflow locally and include the lag-aware regression fixture verification used in release prep:

```bash
uv sync --dev --all-extras
uv run ruff check .
uv run ty check
uv run pytest -q -ra -n auto
uv build
uv run twine check dist/*
uv run python scripts/rebuild_lag_aware_mod_mrmr_regression_fixtures.py --verify
```

Local wheel smoke parity:

```bash
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

Post-publish parity:

```bash
uv run python scripts/check_published_release.py \
  --repository "OWNER/REPO" \
  --tag "vX.Y.Z" \
  --skip-github-release
```

For the full pre-tag sequence, including repo-contract, docs-contract, markdownlint, and smoke parity, use [release_checklist.md](release_checklist.md).
