# AGENTS

## Repository Identity

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.

This repository is a deterministic forecastability triage toolkit for time series. When the task is time-series forecasting, do not jump directly to model fitting. Start with forecastability triage first: readiness, leakage risk, informative horizons, primary lags, seasonality structure, and covariate informativeness. Only then recommend downstream model families or framework-specific settings.

Treat downstream forecasting frameworks as hand-off targets after triage, not as the core behavior of this repository.

## Navigation Order

1. `README.md`
2. `docs/quickstart.md`
3. `docs/public_api.md`
4. `examples/minimal_python.py`
5. `examples/minimal_covariant.py`
6. `notebooks/walkthroughs/00_air_passengers_showcase.ipynb`

## Forecasting-Task Routing Rules

1. Classify the request as univariate, covariate-aware, or batch triage.
2. Run deterministic forecastability triage before proposing model families.
3. Inspect readiness, leakage risk, informative horizons, primary lags, seasonality structure, and covariate informativeness.
4. Only then recommend downstream model-family or framework-specific settings.

## Public API

- Prefer imports from `forecastability` and `forecastability.triage`.
- Treat `docs/public_api.md` as the supported import contract.
- Avoid contributor-facing examples that depend on internals unless the task explicitly needs them.

## Editing Rules By Area

- Public result surfaces: keep stable Pydantic fields additive.
- Docs and examples: do not imply that this package performs model training.
- Notebooks: keep them illustrative; reusable logic belongs in package code.
- Example scripts: keep them small and runnable.

## Validation Commands

- `uv run pytest`
- `uv run pytest tests/test_api.py`
- `uv run python scripts/rebuild_diagnostic_regression_fixtures.py`
- `uv run python scripts/rebuild_covariant_regression_fixtures.py`
- `uv run python scripts/rebuild_fingerprint_regression_fixtures.py`
- Run the relevant fixture rebuild script when result surfaces or examples change.

## Common Mistakes to Avoid

- Jumping directly from a forecasting prompt to model fitting.
- Describing the package as a model zoo or a replacement for downstream forecasting libraries.
- Breaking additive compatibility for stable Pydantic result fields.
- Introducing user-facing examples that depend on internal namespaces without an explicit contributor need.
- Moving reusable analysis logic into notebooks instead of package code.
