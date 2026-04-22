<!-- type: reference -->

# Copilot Instructions

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.

This repository is a deterministic forecastability triage toolkit for time series. When the task is time-series forecasting, do not jump directly to model fitting. Start with forecastability triage first: readiness, leakage risk, informative horizons, primary lags, seasonality structure, and covariate informativeness. Only then recommend downstream model families or framework-specific settings.

CLI, API, notebooks, MCP, and agents are optional access or narration layers around the same deterministic outputs.

## Start Here

- `README.md`
- `docs/quickstart.md`
- `docs/public_api.md`
- `examples/minimal_python.py`
- `examples/minimal_covariant.py`
- `notebooks/walkthroughs/00_air_passengers_showcase.ipynb`

## Repository Rules

- Prefer the stable facade from `forecastability` unless a lower-level namespace is explicitly needed.
- Treat `docs/public_api.md` as the supported import contract.
- Keep additive compatibility for stable Pydantic result fields.
- Do not describe the package as a model zoo or a replacement for downstream forecasting libraries.