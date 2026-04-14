<!-- type: reference -->
# Documentation Map

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.

_Last verified for release 0.2.0 consolidation on 2026-04-14._

Use this index to get to the right surface quickly. The live repository is the source of truth for package entry points, scripts, notebooks, and checked-in artifacts.

> [!IMPORTANT]
> The primary learning path starts with the package/API docs and the live notebooks under `notebooks/walkthroughs/`. Historical planning and archive material is retained, but it is not part of the primary docs path.

## Users

Use this path if you want to install the package, run deterministic triage, and inspect the current artifact surfaces.

| Start here | Why |
| --- | --- |
| [../README.md](../README.md) | Package-level overview: install, Python quickstart, CLI, API, scripts, notebooks, and artifact surfaces |
| [golden_path.md](golden_path.md) | Shortest route from install to a trustworthy first result |
| [quickstart.md](quickstart.md) | Surface-by-surface quickstart for Python, CLI, HTTP API, dashboard, and optional extras |
| [public_api.md](public_api.md) | Stable imports from `forecastability` and `forecastability.triage` |
| [api_contract.md](api_contract.md) | HTTP request, response, and SSE contract for `forecastability.adapters.api:app` |

### Canonical notebook path

Use the live notebooks directly rather than notebook narrative proxies.

1. [notebooks/README.md](notebooks/README.md) for the notebook map.
2. [../notebooks/walkthroughs/00_air_passengers_showcase.ipynb](../notebooks/walkthroughs/00_air_passengers_showcase.ipynb) for the first-stop walkthrough.
3. [../notebooks/walkthroughs/01_canonical_forecastability.ipynb](../notebooks/walkthroughs/01_canonical_forecastability.ipynb) through [../notebooks/walkthroughs/04_screening_end_to_end.ipynb](../notebooks/walkthroughs/04_screening_end_to_end.ipynb) for expanded walkthroughs.
4. [../notebooks/triage/01_forecastability_profile_walkthrough.ipynb](../notebooks/triage/01_forecastability_profile_walkthrough.ipynb) through [../notebooks/triage/06_agent_ready_triage_interpretation.ipynb](../notebooks/triage/06_agent_ready_triage_interpretation.ipynb) for deep-dive method notebooks.

## Contributors

Use this path if you are changing code, docs, scripts, or release-facing surfaces.

| Document | Why |
| --- | --- |
| [maintenance/developer_guide.md](maintenance/developer_guide.md) | Maintainer workflow for source layout, scripts, configs, notebooks, and artifacts |
| [maintenance/doc_coverage_matrix.md](maintenance/doc_coverage_matrix.md) | Which docs own which repo surfaces, and what is archived vs active |
| [code/module_map.md](code/module_map.md) | Current `src/forecastability/` package map by layer and subpackage |
| [architecture.md](architecture.md) | Actual layered architecture and dependency direction |
| [versioning.md](versioning.md) | Stability levels for package, CLI, API, dashboard, agent, and MCP surfaces |

## Operators And Maintainers

Use this path if you operate the CLI/API/dashboard surfaces, regenerate outputs, or maintain release hygiene.

| Document | Why |
| --- | --- |
| [surface_guide.md](surface_guide.md) | Which surfaces are stable, beta, or experimental, and what most users can ignore |
| [observability.md](observability.md) | Event, checkpoint, and auditability contracts |
| [production_readiness.md](production_readiness.md) | Operational boundaries and non-goals |
| [agent_layer.md](agent_layer.md) | Contract for optional LLM narration over deterministic outputs |
| [wording_policy.md](wording_policy.md) | Canonical wording and banned claims for release-facing copy |

## Researchers And Reference Readers

Use this path for method background, caveats, and evidence summaries.

| Document | Why |
| --- | --- |
| [theory/foundations.md](theory/foundations.md) | AMI, pAMI, surrogate significance, and rolling-origin boundaries |
| [theory/pami_residual_backends.md](theory/pami_residual_backends.md) | Linear-residual pAMI assumptions and backend caveats |
| [theory/forecastability_profile.md](theory/forecastability_profile.md) | Forecastability profile model and informative-horizon summary logic |
| [theory/spectral_predictability.md](theory/spectral_predictability.md) | Spectral predictability interpretation and complementarity with AMI |
| [theory/entropy_based_complexity.md](theory/entropy_based_complexity.md) | Entropy-based complexity interpretation |
| [triage_methods/predictive_information_learning_curves.md](triage_methods/predictive_information_learning_curves.md) | Predictive-information learning curves |
| [triage_methods/largest_lyapunov_exponent.md](triage_methods/largest_lyapunov_exponent.md) | Experimental Lyapunov diagnostic caveats |
| [diagnostics_matrix.md](diagnostics_matrix.md) | Cross-diagnostic index |
| [results_summary.md](results_summary.md) | Evidence-oriented output summary |
| [limitations.md](limitations.md) | Statistical and operational limitations |

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
