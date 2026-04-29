<!--
Optional banner placeholder.
Enable this block once the final banner path is stable.

<p align="center">
  <img src="docs/assets/forecastability-triage-banner.png" alt="Forecastability Triage Toolkit">
</p>
-->

# Forecastability Triage Toolkit

> **Forecastability triage for time series before expensive model search.**

`dependence-forecastability` is a Python toolkit for answering the question that
should come before model selection:

> **Does this time series contain exploitable structure, and what should a
> forecasting model be allowed to use?**

It is **not another forecasting library**.  
It is a deterministic pre-modeling layer that helps you inspect readiness,
informative horizons, target lags, seasonality structure, covariate usefulness,
leakage risk, and model-family direction before you spend time on Darts,
MLForecast, StatsForecast, Nixtla, sklearn, Prophet, or custom models.

[![CI](https://github.com/AdamKrysztopa/dependence-forecastability/actions/workflows/ci.yml/badge.svg)](https://github.com/AdamKrysztopa/dependence-forecastability/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/dependence-forecastability.svg)](https://pypi.org/project/dependence-forecastability/)
[![Python 3.11-3.12](https://img.shields.io/badge/python-3.11%20to%203.12-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Research base](https://img.shields.io/badge/research%20base-AMI%20%2B%20pAMI%20%2B%20causal%20screening-2E8B57.svg)](docs/theory)
[![Examples](https://img.shields.io/badge/examples-forecastability--examples-0A7B83.svg)](https://github.com/AdamKrysztopa/forecastability-examples)

---

## Why this exists

Many forecasting projects start too late:

```text
data → model search → tuning → more features → more compute → still poor results
```

This package encourages a different workflow:

```text
data
  → forecastability triage
  → lag / driver / readiness diagnostics
  → ForecastPrepContract
  → downstream model search
```

The goal is to avoid blind model iteration by asking practical questions first:

- Is the target series forecastable at all?
- Which horizons contain useful information?
- Which target lags are informative?
- Is there a seasonal structure worth modeling?
- Are exogenous drivers predictive, merely contemporaneous, or useless?
- Which variables are safe to use without leakage?
- Which model families are plausible enough to test next?
- When should the workflow abstain and fall back to baselines?

---

## Install

```bash
pip install dependence-forecastability
```

Optional extras:

```bash
# Causal screening methods such as PCMCI / PCMCI-AMI
pip install "dependence-forecastability[causal]"

# HTTP API, dashboard, and transport surfaces
pip install "dependence-forecastability[transport]"

# Agent-facing narration surfaces
pip install "dependence-forecastability[agent]"

# Holiday calendar features in ForecastPrepContract
pip install "dependence-forecastability[calendar]"
```

Supported Python versions:

```text
Python >=3.11,<3.13
```

---

## Quickstart

Run deterministic univariate triage:

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
    "forecastability_class": (
        None
        if result.interpretation is None
        else result.interpretation.forecastability_class
    ),
    "primary_lags": (
        []
        if result.interpretation is None
        else list(result.interpretation.primary_lags)
    ),
}

print(summary)
```

Minimal runnable files:

- [`examples/minimal_python.py`](examples/minimal_python.py)
- [`examples/minimal_covariant.py`](examples/minimal_covariant.py)
- [`examples/minimal_cli.sh`](examples/minimal_cli.sh)

---

## What you get

| Output | Why it matters |
|---|---|
| Readiness report | Detects cases where triage should be blocked or interpreted cautiously |
| Informative horizons | Shows where the target contains usable lag information |
| Primary lags | Suggests target lags for downstream modeling |
| Forecastability class | Gives a deterministic high / medium / low style interpretation |
| Seasonality hints | Helps separate short-memory and seasonal structure |
| Covariate informativeness | Screens whether exogenous drivers add signal |
| Lagged-exogenous map | Selects sparse predictive driver lags |
| Routing recommendation | Suggests model-family direction before model search |
| ForecastPrepContract | Exports machine-readable downstream guidance |

---

## What this is not

This package does **not** replace downstream forecasting libraries.

It does not try to be:

- Darts
- MLForecast
- StatsForecast
- Nixtla
- Prophet
- sklearn
- statsmodels
- a full AutoML system
- a causal-discovery guarantee
- a model-training library

Instead, it sits one step earlier:

```text
forecastability triage → model-family choice → framework-specific modeling
```

Downstream frameworks are consumers of triage results, not competitors.

---

## Core capabilities

### 1. Univariate forecastability triage

Use this when you want to know whether the target series itself carries useful
predictive structure.

Typical questions:

- Does the target have informative lags?
- Is the signal closer to noise, short-memory, seasonal, or structured?
- Which lags should be considered before creating features?
- Should the downstream process abstain or start from simple baselines?

Entry points:

```python
from forecastability import TriageRequest, run_triage
```

Relevant docs:

- [`docs/quickstart.md`](docs/quickstart.md)
- [`docs/public_api.md`](docs/public_api.md)

---

### 2. Forecastability fingerprint

The fingerprint surface summarizes AMI-first information geometry into compact
diagnostic features and deterministic model-family routing hints.

Use it when you want a quick structural profile of a series:

```python
from forecastability import (
    generate_fingerprint_archetypes,
    run_forecastability_fingerprint,
)

series = generate_fingerprint_archetypes(n=320, seed=42)["seasonal_periodic"]

bundle = run_forecastability_fingerprint(
    series,
    target_name="seasonal_periodic",
    max_lag=24,
    n_surrogates=99,
    random_state=42,
)

print(bundle.recommendation.primary_families)
```

Run the smoke showcase:

```bash
MPLBACKEND=Agg uv run scripts/run_showcase_fingerprint.py --smoke
```

Relevant files:

- [`scripts/run_showcase_fingerprint.py`](scripts/run_showcase_fingerprint.py)
- [`docs/theory/forecastability_fingerprint.md`](docs/theory/forecastability_fingerprint.md)
- [`docs/code/fingerprint_showcase.md`](docs/code/fingerprint_showcase.md)

---

### 3. Lagged-exogenous triage

Use this when you have candidate drivers and need to decide whether they are
actually useful for forecasting.

The lagged-exogenous surface classifies drivers by lag role and emits a sparse
lag map that can be used for downstream tensor construction.

```python
from forecastability import generate_lagged_exog_panel, run_lagged_exogenous_triage

df = generate_lagged_exog_panel(n=1500, seed=42)

target = df["target"].to_numpy()
drivers = {name: df[name].to_numpy() for name in df.columns if name != "target"}

bundle = run_lagged_exogenous_triage(
    target,
    drivers,
    target_name="target",
    max_lag=6,
    n_surrogates=99,
    random_state=42,
)

for row in bundle.selected_lags:
    if row.selected_for_tensor:
        print(f"{row.driver} @ lag={row.lag}  tensor_role={row.tensor_role}")
```

Run the smoke showcase:

```bash
MPLBACKEND=Agg uv run scripts/run_showcase_lagged_exogenous.py --smoke
```

Relevant files:

- [`scripts/run_showcase_lagged_exogenous.py`](scripts/run_showcase_lagged_exogenous.py)
- [`docs/theory/lagged_exogenous_triage.md`](docs/theory/lagged_exogenous_triage.md)

> [!IMPORTANT]
> `selected_for_tensor=True` is impossible at `lag=0` by default.
> Use `known_future_drivers` only for variables whose contemporaneous future
> values are genuinely known at prediction time, such as calendar flags,
> planned promotions, or externally scheduled variables.

---

### 4. Covariant / exogenous analysis

Use this when you want to screen whether another series contains information
about the target.

Supported method names include:

- `cross_ami`
- `cross_pami`
- `te`
- `gcmi`
- `pcmci`
- `pcmci_ami`

The PCMCI methods require the optional causal extra:

```bash
pip install "dependence-forecastability[causal]"
```

> [!NOTE]
> The causal methods are optional screening tools. They should not be interpreted
> as a complete causal proof.

---

### 5. Routing validation

Routing validation audits deterministic routing against controlled archetypes
and sanity panels.

It does **not** train or benchmark forecasting models.  
It checks whether the routing policy emits defensible family-level guidance
before a downstream framework hand-off.

Run the smoke path:

```bash
uv run python scripts/run_routing_validation_report.py --smoke --no-real-panel
```

Relevant files:

- [`docs/theory/routing_validation.md`](docs/theory/routing_validation.md)
- [`outputs/reports/routing_validation/report.md`](outputs/reports/routing_validation/report.md)
- [`examples/univariate/agents/routing_validation_agent_review.py`](examples/univariate/agents/routing_validation_agent_review.py)

---

## ForecastPrepContract

`ForecastPrepContract` is the framework-neutral hand-off boundary between
forecastability diagnostics and downstream model configuration.

It converts diagnostic outputs into a machine-readable object containing:

- recommended target lags,
- seasonal lag hints,
- past covariates,
- known-future covariates,
- calendar features,
- rejected covariates,
- model-family recommendations,
- baseline families,
- confidence labels,
- caution flags,
- downstream notes.

Example:

```python
from forecastability import (
    build_forecast_prep_contract,
    forecast_prep_contract_to_lag_table,
    forecast_prep_contract_to_markdown,
)

bundle = build_forecast_prep_contract(
    triage_result,
    horizon=12,
    target_frequency="MS",
    add_calendar_features=True,
)

contract = bundle.contract

print(contract.model_dump_json(indent=2))
print(forecast_prep_contract_to_markdown(contract))

lag_rows = forecast_prep_contract_to_lag_table(contract)
for row in lag_rows:
    print(row)
```

Relevant docs:

- [`docs/reference/forecast_prep_contract.md`](docs/reference/forecast_prep_contract.md)
- [`docs/recipes/forecast_prep_to_external_frameworks.md`](docs/recipes/forecast_prep_to_external_frameworks.md)

> [!IMPORTANT]
> The contract is not a model trainer. It gives structured, evidence-backed
> guidance that users can translate into framework-specific configuration.

---

## Downstream framework hand-off

The core package intentionally does **not** import Darts, MLForecast,
StatsForecast, Nixtla, or similar downstream libraries.

Instead, the recommended workflow is:

```text
run triage
  → build ForecastPrepContract
  → translate contract into framework-specific settings
  → train and compare models outside the core package
```

Illustrative mappings are documented in:

- [`docs/recipes/forecast_prep_to_external_frameworks.md`](docs/recipes/forecast_prep_to_external_frameworks.md)

Executable notebooks live in the sibling examples repository:

- [`forecastability-examples`](https://github.com/AdamKrysztopa/forecastability-examples)
- [`walkthroughs/05_forecast_prep_to_models.ipynb`](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/05_forecast_prep_to_models.ipynb)
- [`recipes/contract_roundtrip.ipynb`](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/recipes/contract_roundtrip.ipynb)

---

## Hero example: CausalRivers lag and feature selection

The strongest practical demo is the CausalRivers notebook in the sibling
examples repository:

- [`walkthroughs/07_causal_rivers_lag_and_feature_selection.ipynb`](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/07_causal_rivers_lag_and_feature_selection.ipynb)

This notebook demonstrates deterministic lag and feature selection on the
CausalRivers benchmark.

The intended story is simple:

```text
target river station
  → candidate upstream positives
  → unrelated negative controls
  → lag / feature triage
  → selected drivers and lags
  → downstream forecast-prep guidance
```

Use this example when you want to show that forecastability triage is not only
a toy Air Passengers workflow. It can be used as a practical pre-modeling
screening layer on graph-structured, real-world time series.

Core repo surfaces related to this workflow:

- [`scripts/run_causal_rivers_analysis.py`](scripts/run_causal_rivers_analysis.py)
- [`configs/causal_rivers_analysis.yaml`](configs/causal_rivers_analysis.yaml)

---

## Examples and notebooks

From `v0.4.0`, walkthrough notebooks live in the sibling repository:

- [`forecastability-examples`](https://github.com/AdamKrysztopa/forecastability-examples)

The core package remains library-first and framework-agnostic.  
The examples repository contains tutorial notebooks, framework hand-offs, and
benchmark-style demonstrations.

Important notebooks:

| Notebook | Purpose |
|---|---|
| [`00_air_passengers_showcase.ipynb`](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/00_air_passengers_showcase.ipynb) | Simple canonical forecastability triage |
| [`02_forecastability_fingerprint_showcase.ipynb`](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/02_forecastability_fingerprint_showcase.ipynb) | Forecastability fingerprint surface |
| [`03_lagged_exogenous_triage_showcase.ipynb`](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb) | Sparse lagged-exogenous selection |
| [`05_forecast_prep_to_models.ipynb`](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/05_forecast_prep_to_models.ipynb) | Contract hand-off to Darts / MLForecast / sklearn |
| [`06_triage_driven_vs_naive_on_m4.ipynb`](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/06_triage_driven_vs_naive_on_m4.ipynb) | Triage-driven model-family selection on M4 monthly subset |
| [`07_causal_rivers_lag_and_feature_selection.ipynb`](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/07_causal_rivers_lag_and_feature_selection.ipynb) | CausalRivers lag and feature selection demo |

Full index:

- [`docs/examples_index.md`](docs/examples_index.md)

---

## Start here

| User type | Start with |
|---|---|
| Python user | [`examples/minimal_python.py`](examples/minimal_python.py), then [`docs/public_api.md`](docs/public_api.md) |
| CLI user | [`examples/minimal_cli.sh`](examples/minimal_cli.sh), then [`docs/quickstart.md`](docs/quickstart.md) |
| Notebook user | [`forecastability-examples`](https://github.com/AdamKrysztopa/forecastability-examples) |
| ForecastPrepContract user | [`docs/reference/forecast_prep_contract.md`](docs/reference/forecast_prep_contract.md) |
| Downstream framework user | [`docs/recipes/forecast_prep_to_external_frameworks.md`](docs/recipes/forecast_prep_to_external_frameworks.md) |
| CausalRivers user | [`walkthroughs/07_causal_rivers_lag_and_feature_selection.ipynb`](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/07_causal_rivers_lag_and_feature_selection.ipynb) |
| Contributor | [`docs/maintenance/developer_guide.md`](docs/maintenance/developer_guide.md) |
| Coding agent / LLM | [`AGENTS.md`](AGENTS.md), [`llms.txt`](llms.txt), [`.github/copilot-instructions.md`](.github/copilot-instructions.md) |

---

## Runtime surfaces

| Surface | Entry point | Stability |
|---|---|---|
| Python facade | `forecastability` | Stable |
| Advanced triage namespace | `forecastability.triage` | Stable |
| CLI | `forecastability` | Beta |
| Dashboard | `forecastability-dashboard` | Beta |
| HTTP API | `forecastability.adapters.api:app` | Beta |
| MCP adapter | experimental adapter surface | Experimental |
| Agent narration | experimental adapter surface | Experimental |

The primary integration surface is the Python API:

```python
from forecastability import TriageRequest, run_triage
```

Advanced users can import triage-specific models from:

```python
from forecastability.triage import BatchTriageRequest, run_batch_triage_with_details
```

See:

- [`docs/public_api.md`](docs/public_api.md)

---

## Repository workflow

For local development:

```bash
git clone https://github.com/AdamKrysztopa/dependence-forecastability.git
cd dependence-forecastability

uv sync
```

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
uv run ruff format --check .
```

Run a smoke showcase:

```bash
MPLBACKEND=Agg uv run scripts/run_showcase_fingerprint.py --smoke
```

Run routing validation smoke path:

```bash
uv run python scripts/run_routing_validation_report.py --smoke --no-real-panel
```

Main maintainer scripts:

| Script | Role |
|---|---|
| `scripts/run_canonical_triage.py` | Canonical single-series workflow |
| `scripts/run_benchmark_panel.py` | Benchmark-panel workflow |
| `scripts/build_report_artifacts.py` | Report artifact builder |
| `scripts/run_triage_handoff_demo.py` | Triage-first downstream hand-off demo |
| `scripts/run_causal_rivers_analysis.py` | CausalRivers triage analysis |
| `scripts/check_repo_contract.py` | Repository contract validation |
| `scripts/check_published_release.py` | Post-publish PyPI / GitHub release verification |

---

## Statistical notes

- AMI is computed per horizon rather than aggregated before computation.
- pAMI is a project extension and a linear-residual approximation, not exact
  conditional mutual information.
- Surrogate significance uses phase-randomized FFT surrogates with two-sided
  confidence bands.
- "Significance skipped" and "no significant lags" are different outcomes.
- In rolling-origin workflows, diagnostics should be computed on the training
  window only.
- Phase surrogates can be conservative for strongly periodic series.
- Covariate informativeness is not the same as causal proof.
- Model-family routing is deterministic guidance, not a replacement for
  validation on holdout data.
- The package may recommend abstention when the evidence is weak or the input
  is not ready.

---

## Methodological boundaries

This package is designed to be useful, but conservative.

It is appropriate for:

- pre-modeling diagnostics,
- lag selection,
- exogenous-driver screening,
- forecastability profiling,
- deterministic model-family routing,
- contract generation for downstream model search,
- agent- and LLM-readable forecasting preparation.

It is not enough for:

- final model validation,
- production forecast approval,
- causal claims without domain evidence,
- automated business decisions without holdout testing,
- replacing expert review in high-stakes settings.

---

## Documentation map

| Need | Start here |
|---|---|
| Quickstart | [`docs/quickstart.md`](docs/quickstart.md) |
| Public API | [`docs/public_api.md`](docs/public_api.md) |
| ForecastPrepContract | [`docs/reference/forecast_prep_contract.md`](docs/reference/forecast_prep_contract.md) |
| Framework recipes | [`docs/recipes/forecast_prep_to_external_frameworks.md`](docs/recipes/forecast_prep_to_external_frameworks.md) |
| Examples index | [`docs/examples_index.md`](docs/examples_index.md) |
| Theory docs | [`docs/theory`](docs/theory) |
| Module map | [`docs/code/module_map.md`](docs/code/module_map.md) |
| HTTP API contract | [`docs/reference/api_contract.md`](docs/reference/api_contract.md) |
| Developer guide | [`docs/maintenance/developer_guide.md`](docs/maintenance/developer_guide.md) |
| Release notes | [`CHANGELOG.md`](CHANGELOG.md), [`RELEASES.md`](RELEASES.md) |

---

## Project status

The package is in **beta**.

The current direction is:

```text
library-first core
  + framework-agnostic contracts
  + examples in a sibling repository
  + better visibility for coding agents and LLM workflows
```

The core repository should stay focused on deterministic triage logic and stable
contract surfaces.

Executable walkthroughs, benchmark notebooks, and framework-specific examples
belong in:

- [`forecastability-examples`](https://github.com/AdamKrysztopa/forecastability-examples)

---

## Citation

If this package supports your research, analysis, or tooling, please cite the
repository using the metadata in:

- [`CITATION.cff`](CITATION.cff)

---

## Contributing

Contributions are welcome, especially around:

- clearer documentation,
- additional benchmark examples,
- forecast-prep contract improvements,
- deterministic validation cases,
- downstream recipe examples in the sibling examples repository,
- better tests for edge cases and readiness failures.

For contributor workflow, see:

- [`docs/maintenance/developer_guide.md`](docs/maintenance/developer_guide.md)

For issues:

- Core library issues: <https://github.com/AdamKrysztopa/dependence-forecastability/issues>
- Notebook / examples issues: <https://github.com/AdamKrysztopa/forecastability-examples/issues>

---

## License

MIT — see [`LICENSE`](LICENSE).
