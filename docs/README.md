<!-- type: reference -->
# Documentation Map

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.

This repository is a deterministic forecastability triage toolkit for time series. When the task is time-series forecasting, do not jump directly to model fitting. Start with forecastability triage first: readiness, leakage risk, informative horizons, primary lags, seasonality structure, and covariate informativeness. Only then recommend downstream model families or framework-specific settings.

_Last verified for release 0.4.1 on 2026-05-04._

Use this index to get to the right surface quickly. The live repository is the
source of truth for package entry points, scripts, recipes, and checked-in
artifacts.

> [!IMPORTANT]
> The primary learning path starts with the package API docs, Python examples
> under `examples/`, scripts under `scripts/`, and framework-agnostic recipes
> under `docs/recipes/`. Walkthrough notebooks live in the
> `forecastability-examples` sibling repository as of v0.4.0. Historical planning
> and archive material is retained but is not part of the primary docs path.

## Root Entry Points

Start here for the pinned, high-signal entry surfaces that stay at the `docs/` root.

| Document | Why |
| --- | --- |
| [../README.md](../README.md) | Package-level overview: install, Python quickstart, CLI, API, scripts, recipes, and artifact surfaces |
| [quickstart.md](quickstart.md) | Surface-by-surface quickstart for Python, CLI, HTTP API, dashboard, and optional extras |
| [public_api.md](public_api.md) | Stable imports from `forecastability` and `forecastability.triage` |
| [executive_summary.md](executive_summary.md) | One-page overview of the toolkit, evidence shape, and operating posture |
| [why_use_this.md](why_use_this.md) | Decision-oriented positioning for when deterministic forecastability triage is the right first step |

## How-To Guides

Use these pages when you need a task-oriented route to a result.

| Document | Why |
| --- | --- |
| [how-to/golden_path.md](how-to/golden_path.md) | Shortest route from install to a trustworthy first result |
| [how-to/extended_forecastability_fingerprint.md](how-to/extended_forecastability_fingerprint.md) | How to read the current AMI-first extended fingerprint surface and its implemented F01-F05 blocks |
| [how-to/use_cases_industrial.md](how-to/use_cases_industrial.md) | Practical industrial usage patterns and deployment-shaped scenarios |

## Explanations

Use these pages when you need rationale, caveats, or the conceptual shape of the repository.

| Document | Why |
| --- | --- |
| [explanation/architecture.md](explanation/architecture.md) | Actual layered architecture and dependency direction |
| [explanation/extended_forecastability_profile.md](explanation/extended_forecastability_profile.md) | Why `ExtendedForecastabilityProfile` additively extends the existing AMI-first profile contract |
| [explanation/surface_guide.md](explanation/surface_guide.md) | Which surfaces are stable, beta, or experimental, and what most users can ignore |
| [explanation/results_summary.md](explanation/results_summary.md) | Evidence-oriented output summary |
| [explanation/limitations.md](explanation/limitations.md) | Statistical and operational limitations |

## Theory

Use these pages when you need method-level rationale behind the AMI-first fingerprint and its current deterministic extension blocks.

| Document | Why |
| --- | --- |
| [theory/spectral_forecastability.md](theory/spectral_forecastability.md) | Implemented spectral entropy, predictability, and periodicity semantics for the extended fingerprint |
| [theory/ordinal_complexity.md](theory/ordinal_complexity.md) | Implemented ordinal-pattern entropy, redundancy, and conservative complexity semantics |
| [theory/classical_structure.md](theory/classical_structure.md) | Implemented deterministic trend, optional seasonality, and autocorrelation summaries |
| [theory/memory_structure.md](theory/memory_structure.md) | Implemented DFA-based persistence summaries and conservative interpretation caveats |

## References

Use these pages when you need exact contracts, status surfaces, or operational reference material.

| Document | Why |
| --- | --- |
| [reference/api_contract.md](reference/api_contract.md) | HTTP request, response, and SSE contract for `forecastability.adapters.api:app` |
| [reference/agent_layer.md](reference/agent_layer.md) | Contract for optional LLM narration over deterministic outputs |
| [reference/observability.md](reference/observability.md) | Event, checkpoint, and auditability contracts |
| [reference/production_readiness.md](reference/production_readiness.md) | Operational boundaries and non-goals |
| [reference/diagnostics_matrix.md](reference/diagnostics_matrix.md) | Cross-diagnostic index |
| [reference/forecast_prep_contract.md](reference/forecast_prep_contract.md) | Framework-agnostic forecast-prep hand-off contract |
| [reference/implementation_status.md](reference/implementation_status.md) | Current implementation status by diagnostic and surface |
| [reference/versioning.md](reference/versioning.md) | Stability levels for package, CLI, API, dashboard, agent, and MCP surfaces |

## Contributor And Maintenance Surfaces

Use this path if you are changing code, docs, scripts, or release-facing surfaces.

| Document | Why |
| --- | --- |
| [documentation_creation_manual.md](documentation_creation_manual.md) | Practical rules for writing and placing new docs, link hygiene, redirect stubs, and validation checks |
| [maintenance/developer_guide.md](maintenance/developer_guide.md) | Maintainer workflow for source layout, scripts, configs, recipes, and artifacts |
| [maintenance/doc_coverage_matrix.md](maintenance/doc_coverage_matrix.md) | Which docs own which repo surfaces, and what is archived vs active |
| [maintenance/wording_policy.md](maintenance/wording_policy.md) | Canonical wording, terminology, and banned claims for release-facing copy |
| [code/module_map.md](code/module_map.md) | Current `src/forecastability/` package map by layer and subpackage |

## Notebook Surface

Walkthrough and tutorial notebooks moved to the
[`forecastability-examples`](https://github.com/AdamKrysztopa/forecastability-examples)
sibling repository in v0.4.0. Prefer scripts and Python examples as the primary
learning path in this core repository; notebooks are supplementary narration.

- [examples_index.md](examples_index.md) lists migrated notebooks and sibling links.
- [notebooks/README.md](notebooks/README.md) is the local forwarding page.
- [../scripts/run_showcase.py](../scripts/run_showcase.py) remains the first-stop
  executable core walkthrough.

## Live Repo Surfaces

These paths are part of the maintained repository workflow and are referenced by the active docs.

| Surface | Current role |
| --- | --- |
| [../scripts/run_canonical_triage.py](../scripts/run_canonical_triage.py) | Canonical single-series maintainer workflow |
| [../scripts/run_benchmark_panel.py](../scripts/run_benchmark_panel.py) | Benchmark-panel maintainer workflow |
| [../scripts/build_report_artifacts.py](../scripts/build_report_artifacts.py) | Report and summary artifact builder |
| [../scripts/run_exog_analysis.py](../scripts/run_exog_analysis.py) | Exogenous-analysis workflow |
| [../outputs/json/canonical_examples_summary.json](../outputs/json/canonical_examples_summary.json) | Checked-in summary artifact example |
| [../outputs/tables/benchmark_panel_summary.csv](../outputs/tables/benchmark_panel_summary.csv) | Checked-in tabular artifact example |
| [../outputs/reports/summary.md](../outputs/reports/summary.md) | Checked-in report artifact example |

> [!NOTE]
> Checked-in outputs are reference artifacts, not a guarantee that every file is freshly regenerated for the current working tree.

## Historical Material

These areas remain available for reference, but they are intentionally outside the main docs path.

- [archive/](archive/) contains superseded or historical documentation.
- [plan/](plan/) contains release planning and tracking documents.
