<!-- type: reference -->
# Module Map

This page is the live source-layout map for `src/forecastability/`.

_Last verified for release 0.2.0 consolidation on 2026-04-14._

The package is layered and subpackage-heavy. The stable import facade is small, but the internal tree is organized by role: triage domain, use cases, analyzer pipeline, metrics, diagnostics, reporting, utils, adapters, services, ports, and bootstrap helpers.

## Facades And Root Modules

| Path | Role | Contract |
| --- | --- | --- |
| [src/forecastability/__init__.py](../../src/forecastability/__init__.py) | Top-level package facade with re-exports for `run_triage`, `run_batch_triage`, analyzers, config models, result models, dataset helpers, scorer registry, and validation | Public |
| [src/forecastability/triage/__init__.py](../../src/forecastability/triage/__init__.py) | Advanced triage namespace for batch models, readiness helpers, events, bundle types, and triage-specific diagnostics | Public |
| [src/forecastability/extensions.py](../../src/forecastability/extensions.py) | Extension helpers used by repository workflows such as sensitivity and uncertainty studies | Repo-facing support |
| [src/forecastability/models.py](../../src/forecastability/models.py) | Forecast baselines and optional model integrations used by rolling-origin workflows | Repo-facing support |
| [src/forecastability/exog_benchmark.py](../../src/forecastability/exog_benchmark.py) | Exogenous benchmark helpers used by benchmark workflows | Repo-facing support |

## Layered Package Map

| Package | Representative modules | Purpose |
| --- | --- | --- |
| [src/forecastability/triage/](../../src/forecastability/triage/) | `models.py`, `batch_models.py`, `readiness.py`, `router.py`, `events.py`, `forecastability_profile.py`, `predictive_info_learning_curve.py`, `spectral_predictability.py`, `complexity_band.py`, `lyapunov.py`, `theoretical_limit_diagnostics.py`, `result_bundle.py` | Triage-domain models, readiness/router policy, diagnostic result models, and serialisable result bundles |
| [src/forecastability/use_cases/](../../src/forecastability/use_cases/) | `run_triage.py`, `run_batch_triage.py` | Application entry points that orchestrate deterministic triage and batch triage |
| [src/forecastability/pipeline/](../../src/forecastability/pipeline/) | `analyzer.py`, `pipeline.py`, `rolling_origin.py` | Analyzer facade, canonical workflow helpers, and rolling-origin evaluation support |
| [src/forecastability/metrics/](../../src/forecastability/metrics/) | `metrics.py`, `scorers.py` | Core AMI/pAMI computation and scorer registry infrastructure |
| [src/forecastability/diagnostics/](../../src/forecastability/diagnostics/) | `surrogates.py`, `cmi.py`, `spectral_utils.py`, `diagnostic_regression.py` | Significance bands, conditional-MI backends, spectral helpers, and regression tooling |
| [src/forecastability/reporting/](../../src/forecastability/reporting/) | `interpretation.py`, `reporting.py` | Deterministic interpretation and Markdown/report builders |
| [src/forecastability/utils/](../../src/forecastability/utils/) | `config.py`, `datasets.py`, `types.py`, `validation.py`, `aggregation.py`, `io_models.py`, `plots.py`, `reproducibility.py`, `robustness.py`, `state.py` | Config models, typed result containers, dataset helpers, validation, plotting, reproducibility, and workflow support code |
| [src/forecastability/adapters/](../../src/forecastability/adapters/) | `cli.py`, `api.py`, `dashboard.py`, `mcp_server.py`, `settings.py`, `event_emitter.py`, `checkpoint.py`, `result_bundle_io.py`, `triage_presenter.py`, `agents/`, `llm/` | Transport, runtime, agent, checkpoint, and presentation adapters |
| [src/forecastability/services/](../../src/forecastability/services/) | `raw_curve_service.py`, `partial_curve_service.py`, `significance_service.py`, `forecastability_profile_service.py`, `predictive_info_learning_curve_service.py`, `spectral_predictability_service.py`, `complexity_band_service.py`, `lyapunov_service.py`, `theoretical_limit_diagnostics_service.py`, `recommendation_service.py`, `exog_*_service.py` | Internal builder and orchestration helpers used by analyzers and use cases |
| [src/forecastability/ports/](../../src/forecastability/ports/) | `__init__.py` | Protocol-oriented seams for the hexagonal architecture direction |
| [src/forecastability/bootstrap/](../../src/forecastability/bootstrap/) | `output_dirs.py` | Bootstrap helpers for output directory management |

## What Lives Where

### Public facade and triage namespace

- `__init__.py` exposes the stable package imports documented in [../public_api.md](../public_api.md).
- `triage/__init__.py` groups advanced triage exports such as batch row models, event models, result bundles, and readiness/router helpers.

### Metrics and diagnostics

- `metrics/metrics.py` is the core AMI and pAMI computation surface.
- `metrics/scorers.py` owns the scorer registry and built-in scorer family metadata.
- `diagnostics/surrogates.py` owns phase-randomized FFT surrogates and significance bands.
- `diagnostics/cmi.py` owns alternative residual backends used by pAMI-style workflows.

### Triage domain and use cases

- `triage/models.py` defines `TriageRequest`, `TriageResult`, readiness models, and method-plan models.
- `triage/batch_models.py` defines the batch request, row, execution, and response types.
- `use_cases/run_triage.py` and `use_cases/run_batch_triage.py` are the authoritative orchestration entry points called by the public facade and adapters.

### Pipeline and rolling-origin support

- `pipeline/analyzer.py` contains `ForecastabilityAnalyzer`, `ForecastabilityAnalyzerExog`, and `AnalyzeResult`.
- `pipeline/rolling_origin.py` contains rolling-origin split helpers used by evaluation workflows.
- `pipeline/pipeline.py` contains canonical workflow helpers used by scripts and tests.

### Reporting, artifacts, and support code

- `reporting/interpretation.py` owns deterministic interpretation output.
- `reporting/reporting.py` owns Markdown and report-building helpers.
- `utils/types.py` and `utils/config.py` provide the typed models re-exported by the package facade.
- `utils/datasets.py` contains canonical generators and dataset loaders used by docs, tests, and scripts.

### Adapter and automation surfaces

- `adapters/cli.py` implements the `forecastability` command.
- `adapters/dashboard.py` implements the `forecastability-dashboard` command.
- `adapters/api.py` exposes the FastAPI application at `forecastability.adapters.api:app`.
- `adapters/agents/` and `adapters/llm/` contain optional structured payload and narration adapters.
- `adapters/mcp_server.py` contains the experimental MCP surface.

## Contributor Guidance

- Use [../public_api.md](../public_api.md) when deciding whether a symbol is part of the supported import contract.
- Use [../architecture.md](../architecture.md) when deciding where new logic should live.
- Use [../maintenance/developer_guide.md](../maintenance/developer_guide.md) for the repo workflow around scripts, notebooks, configs, outputs, and docs.
