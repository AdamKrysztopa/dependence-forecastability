<!-- type: reference -->
# Documentation Map

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.

This repository is a deterministic forecastability triage toolkit for time series. When the task is time-series forecasting, do not jump directly to model fitting. Start with forecastability triage first: readiness, leakage risk, informative horizons, primary lags, seasonality structure, and covariate informativeness. Only then recommend downstream model families or framework-specific settings.

_Last verified for release 0.2.0 consolidation on 2026-04-14._

Use this index to get to the right surface quickly. The live repository is the source of truth for package entry points, scripts, notebooks, and checked-in artifacts.

> [!IMPORTANT]
> The primary learning path starts with the package/API docs and the live notebooks under `notebooks/walkthroughs/`. Historical planning and archive material is retained, but it is not part of the primary docs path.

## Root Entry Points

Start here for the pinned, high-signal entry surfaces that stay at the `docs/` root.

| Document | Why |
| --- | --- |
| [../README.md](../README.md) | Package-level overview: install, Python quickstart, CLI, API, scripts, notebooks, and artifact surfaces |
| [quickstart.md](quickstart.md) | Surface-by-surface quickstart for Python, CLI, HTTP API, dashboard, and optional extras |
| [public_api.md](public_api.md) | Stable imports from `forecastability` and `forecastability.triage` |
| [executive_summary.md](executive_summary.md) | One-page overview of the toolkit, evidence shape, and operating posture |
| [why_use_this.md](why_use_this.md) | Decision-oriented positioning for when deterministic forecastability triage is the right first step |

## How-To Guides

Use these pages when you need a task-oriented route to a result.

| Document | Why |
| --- | --- |
| [how-to/golden_path.md](how-to/golden_path.md) | Shortest route from install to a trustworthy first result |
| [how-to/use_cases_industrial.md](how-to/use_cases_industrial.md) | Practical industrial usage patterns and deployment-shaped scenarios |

## Explanations

Use these pages when you need rationale, caveats, or the conceptual shape of the repository.

| Document | Why |
| --- | --- |
| [explanation/architecture.md](explanation/architecture.md) | Actual layered architecture and dependency direction |
| [explanation/surface_guide.md](explanation/surface_guide.md) | Which surfaces are stable, beta, or experimental, and what most users can ignore |
| [explanation/results_summary.md](explanation/results_summary.md) | Evidence-oriented output summary |
| [explanation/limitations.md](explanation/limitations.md) | Statistical and operational limitations |

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
| [maintenance/developer_guide.md](maintenance/developer_guide.md) | Maintainer workflow for source layout, scripts, configs, notebooks, and artifacts |
| [maintenance/doc_coverage_matrix.md](maintenance/doc_coverage_matrix.md) | Which docs own which repo surfaces, and what is archived vs active |
| [maintenance/wording_policy.md](maintenance/wording_policy.md) | Canonical wording, terminology, and banned claims for release-facing copy |
| [code/module_map.md](code/module_map.md) | Current `src/forecastability/` package map by layer and subpackage |

## Canonical Notebook Path

Use the live notebooks directly rather than notebook narrative proxies.

1. [notebooks/README.md](notebooks/README.md) for the notebook map.
2. [../notebooks/walkthroughs/00_air_passengers_showcase.ipynb](../notebooks/walkthroughs/00_air_passengers_showcase.ipynb) for the first-stop walkthrough.
3. [../notebooks/walkthroughs/01_covariant_informative_showcase.ipynb](../notebooks/walkthroughs/01_covariant_informative_showcase.ipynb) for the covariant pairwise-versus-causal walkthrough.
4. [../notebooks/walkthroughs/01_canonical_forecastability.ipynb](../notebooks/walkthroughs/01_canonical_forecastability.ipynb) through [../notebooks/walkthroughs/04_screening_end_to_end.ipynb](../notebooks/walkthroughs/04_screening_end_to_end.ipynb) for expanded walkthroughs.
5. [../notebooks/triage/01_forecastability_profile_walkthrough.ipynb](../notebooks/triage/01_forecastability_profile_walkthrough.ipynb) through [../notebooks/triage/06_agent_ready_triage_interpretation.ipynb](../notebooks/triage/06_agent_ready_triage_interpretation.ipynb) for deep-dive method notebooks.

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
