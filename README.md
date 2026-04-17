<!-- type: reference -->
# Forecastability Triage Toolkit

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.

[![CI](https://github.com/AdamKrysztopa/dependence-forecastability/actions/workflows/ci.yml/badge.svg)](https://github.com/AdamKrysztopa/dependence-forecastability/actions/workflows/ci.yml)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/dependence-forecastability?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/dependence-forecastability)
[![PyPI version](https://img.shields.io/pypi/v/dependence-forecastability.svg)](https://pypi.org/project/dependence-forecastability/)
[![Version](https://img.shields.io/github/v/tag/AdamKrysztopa/dependence-forecastability?label=version&sort=semver)](https://github.com/AdamKrysztopa/dependence-forecastability/releases)
[![Docs](https://img.shields.io/github/deployments/AdamKrysztopa/dependence-forecastability/github-pages?label=docs)](https://github.com/AdamKrysztopa/dependence-forecastability/tree/main/docs)
[![Python 3.11-3.12](https://img.shields.io/badge/python-3.11%20to%203.12-blue.svg)](https://python.org)
[![Based on arXiv:2601.10006](https://img.shields.io/badge/based%20on-arXiv%3A2601.10006-b31b1b.svg)](https://doi.org/10.48550/arXiv.2601.10006)

This repository provides a deterministic triage workflow for deciding whether a time series shows exploitable structure before you commit to expensive model search. The maintained package facade exposes `run_triage`, `run_batch_triage`, analyzers, request/result models, config models, dataset helpers, and the scorer registry through `forecastability` and `forecastability.triage`.

## Package And API Quickstart

Install the package surface:

```bash
pip install dependence-forecastability
```

Optional runtime extras:

```bash
pip install "dependence-forecastability[transport]"
pip install "dependence-forecastability[agent]"
```

Run one deterministic triage call through the top-level facade:

```python
from forecastability import TriageRequest, generate_ar1, run_triage

series = generate_ar1(n_samples=300, phi=0.8, random_state=42)
result = run_triage(
    TriageRequest(
        series=series,
        goal="univariate",
        max_lag=20,
        n_surrogates=99,
        random_state=42,
    )
)

summary = {
    "blocked": result.blocked,
    "readiness_status": result.readiness.status.value,
    "compute_surrogates": None if result.method_plan is None else result.method_plan.compute_surrogates,
    "forecastability_class": None if result.interpretation is None else result.interpretation.forecastability_class,
    "primary_lags": [] if result.interpretation is None else list(result.interpretation.primary_lags),
}
print(summary)
```

Transport and runtime entry points:

| Surface | Entry point | Stability |
| --- | --- | --- |
| Python facade | `forecastability`, `forecastability.triage` | Stable |
| CLI | `forecastability` | Beta |
| HTTP API | `forecastability.adapters.api:app` | Beta |
| Dashboard | `forecastability-dashboard` | Beta |
| MCP server | adapter surface | Experimental |
| Agent narration | adapter surface | Experimental |

## Repository Workflow

If you are working in the repository rather than installing the package, start here:

```bash
uv sync
```

Canonical maintainer scripts:

| Script | Role |
| --- | --- |
| `scripts/run_canonical_triage.py` | Canonical single-series workflow |
| `scripts/run_benchmark_panel.py` | Benchmark-panel workflow |
| `scripts/build_report_artifacts.py` | Report artifact builder |

Secondary utilities:

- `scripts/download_data.py`
- `scripts/run_exog_analysis.py`
- `scripts/check_notebook_contract.py`
- `scripts/rebuild_benchmark_fixture_artifacts.py`
- `scripts/rebuild_diagnostic_regression_fixtures.py`

Current config status:

| Config | Current role |
| --- | --- |
| `configs/benchmark_panel.yaml` | Active benchmark-panel configuration |
| `configs/canonical_examples.yaml` | Descriptive reference for canonical examples, not the root runner's only source of truth |
| `configs/interpretation_rules.yaml` | Reference thresholds for interpretation policy |
| `configs/benchmark_exog_panel.yaml` | Secondary exogenous benchmark workflow |
| `configs/exogenous_screening_workbench.yaml` | Secondary workbench configuration |
| `configs/robustness_study.yaml` | Secondary robustness-study workflow |

## Notebook Path And Artifact Surfaces

The canonical notebook path is:

1. [docs/notebooks/README.md](docs/notebooks/README.md)
2. [notebooks/walkthroughs/00_air_passengers_showcase.ipynb](notebooks/walkthroughs/00_air_passengers_showcase.ipynb)
3. `notebooks/walkthroughs/01` through `04`
4. `notebooks/triage/01` through `06` for deep dives

Main checked-in artifact surfaces:

- `outputs/json/canonical_examples_summary.json` and related canonical JSON outputs
- `outputs/tables/*.csv`
- `outputs/reports/*.md`

> [!NOTE]
> Checked-in artifacts are reference outputs. They are useful examples of the output surface, but they should not be treated as guaranteed-fresh build products for the current working tree.

## Statistical Notes

- AMI is computed per horizon rather than aggregated before computation.
- pAMI is a project extension and a linear-residual approximation, not exact conditional mutual information.
- Surrogate significance uses phase-randomized FFT surrogates with at least 99 surrogates and two-sided 95% bands.
- “Significance skipped” and “no significant lags” are different outcomes. Use `compute_surrogates` or the route choice to tell them apart.
- In rolling-origin workflows, diagnostics are computed on the training window only.
- Phase surrogates can be conservative for strongly periodic series.

## Documentation Map

| Need | Start here |
| --- | --- |
| Documentation index by role | [docs/README.md](docs/README.md) |
| Stable imports and runtime entry points | [docs/public_api.md](docs/public_api.md) |
| Live module layout | [docs/code/module_map.md](docs/code/module_map.md) |
| HTTP API contract | [docs/api_contract.md](docs/api_contract.md) |
| Notebook path | [docs/notebooks/README.md](docs/notebooks/README.md) |
| Contributor workflow | [docs/maintenance/developer_guide.md](docs/maintenance/developer_guide.md) |

For the repository-wide docs map, see [docs/README.md](docs/README.md).
