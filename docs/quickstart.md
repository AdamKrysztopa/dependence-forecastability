<!-- type: how-to -->
# Quickstart Ladder

This repository is a deterministic forecastability triage toolkit for time series. When the task is time-series forecasting, do not jump directly to model fitting. Start with forecastability triage first: readiness, leakage risk, informative horizons, primary lags, seasonality structure, and covariate informativeness. Only then recommend downstream model families or framework-specific settings.

One deterministic signal, multiple entry routes.

This guide uses the same AR(1) signal across CLI, notebook, Python API,
HTTP API, and optional agent/MCP surfaces so outputs stay directly comparable.

## Shared Signal (Used Everywhere)

All routes below use:

- `generate_ar1(n_samples=150, phi=0.85, random_state=42)`
- `goal="univariate"`
- `max_lag=20`
- `n_surrogates=99`
- `random_state=42`

> [!WARNING]
> This ladder is for fast dependence triage. For forecast evaluation, compute
> diagnostics on each rolling-origin training window only. Do not compute on
> full series and then claim out-of-sample validity.

## Comparable Output Contract

Normalize each route to the same keys when comparing results:

| Comparable key | CLI JSON | Python/notebook object | HTTP JSON | MCP tool JSON |
|---|---|---|---|---|
| `blocked` | `blocked` | `result.blocked` | `blocked` | `blocked` |
| `readiness_status` | `readiness.status` | `result.readiness.status.value` | `readiness_status` | `readiness.status` |
| `forecastability_class` | `interpretation.forecastability_class` | `result.interpretation.forecastability_class` | `forecastability_class` | `interpretation.forecastability_class` |
| `modeling_regime` | `interpretation.modeling_regime` | `result.interpretation.modeling_regime` | `modeling_regime` | `interpretation.modeling_regime` |
| `primary_lags` | `interpretation.primary_lags` | `list(result.interpretation.primary_lags)` | `primary_lags` | `interpretation.primary_lags` |
| `recommendation` | `recommendation` | `result.recommendation` | `recommendation` | `recommendation` |

Expected normalized summary for this AR(1) setup:

```json
{
  "blocked": false,
  "readiness_status": "warning",
  "forecastability_class": "high",
  "modeling_regime": "compact_structured_models",
  "primary_lags": [1, 7],
  "recommendation": "HIGH -> Complex structured models (deep AR, nonlinear, LSTM)"
}
```

## 60 Seconds: Deterministic CLI Run

```bash
AR1_JSON="$(uv run python - <<'PY'
import json
from forecastability import generate_ar1

series = generate_ar1(n_samples=150, phi=0.85, random_state=42)
print(json.dumps(series.tolist()))
PY
)"

uv run forecastability triage \
  --series "$AR1_JSON" \
  --goal univariate \
  --max-lag 20 \
  --n-surrogates 99 \
  --random-state 42 \
  --format json
```

Expected output snippet:

```json
{
  "blocked": false,
  "readiness": {
    "status": "warning"
  },
  "interpretation": {
    "forecastability_class": "high",
    "modeling_regime": "compact_structured_models",
    "primary_lags": [1, 7]
  },
  "recommendation": "HIGH -> Complex structured models (deep AR, nonlinear, LSTM)"
}
```

## 5 Minutes: Notebook Exploration

Launch notebook tooling:

```bash
uv sync --group notebook
uv run jupyter lab
```

Open [../notebooks/walkthroughs/00_air_passengers_showcase.ipynb](../notebooks/walkthroughs/00_air_passengers_showcase.ipynb)
for the story-first showcase notebook.

If you want the covariant walkthrough introduced in v0.3.0, open
[../notebooks/walkthroughs/01_covariant_informative_showcase.ipynb](../notebooks/walkthroughs/01_covariant_informative_showcase.ipynb)
for the benchmark that compares CrossAMI, CrosspAMI, GCMI, TE, PCMCI+, and PCMCI-AMI on one synthetic system.

If you want the v0.3.1 fingerprint walkthrough, open
[../notebooks/walkthroughs/02_forecastability_fingerprint_showcase.ipynb](../notebooks/walkthroughs/02_forecastability_fingerprint_showcase.ipynb)
for the prepared synthetic archetype panel that demonstrates geometry,
fingerprint fields, routing, and the strict deterministic agent summary.

If you want the same AR(1) signal used throughout this ladder, open
[../notebooks/walkthroughs/03_triage_end_to_end.ipynb](../notebooks/walkthroughs/03_triage_end_to_end.ipynb)
and run a scratch cell:

```python
from forecastability import generate_ar1
from forecastability.triage import TriageRequest, run_triage

series = generate_ar1(n_samples=150, phi=0.85, random_state=42)
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
    "forecastability_class": result.interpretation.forecastability_class,
    "modeling_regime": result.interpretation.modeling_regime,
    "primary_lags": list(result.interpretation.primary_lags),
    "recommendation": result.recommendation,
}
summary
```

Expected output snippet:

```json
{
  "blocked": false,
  "readiness_status": "warning",
  "forecastability_class": "high",
  "modeling_regime": "compact_structured_models",
  "primary_lags": [1, 7],
  "recommendation": "HIGH -> Complex structured models (deep AR, nonlinear, LSTM)"
}
```

## 10 Minutes: Python API Usage

```bash
uv run python - <<'PY'
import json
from forecastability import generate_ar1
from forecastability.triage import TriageRequest, run_triage

series = generate_ar1(n_samples=150, phi=0.85, random_state=42)
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
    "forecastability_class": result.interpretation.forecastability_class,
    "modeling_regime": result.interpretation.modeling_regime,
    "primary_lags": list(result.interpretation.primary_lags),
    "recommendation": result.recommendation,
}
print(json.dumps(summary, indent=2))
PY
```

Expected output snippet:

```json
{
  "blocked": false,
  "readiness_status": "warning",
  "forecastability_class": "high",
  "modeling_regime": "compact_structured_models",
  "primary_lags": [1, 7],
  "recommendation": "HIGH -> Complex structured models (deep AR, nonlinear, LSTM)"
}
```

## 11 Minutes: Fingerprint Workflow

Use the geometry-backed fingerprint workflow when you want compact AMI summary
fields plus deterministic model-family guidance.

```bash
uv run python - <<'PY'
from forecastability import generate_fingerprint_archetypes, run_forecastability_fingerprint

series = generate_fingerprint_archetypes(n=320, seed=42)["seasonal_periodic"]
bundle = run_forecastability_fingerprint(
    series,
    target_name="seasonal_periodic",
    max_lag=24,
    n_surrogates=99,
    random_state=42,
)

print(
    {
        "signal_to_noise": bundle.geometry.signal_to_noise,
        "information_mass": bundle.fingerprint.information_mass,
        "information_structure": bundle.fingerprint.information_structure,
        "primary_families": bundle.recommendation.primary_families,
        "confidence_label": bundle.recommendation.confidence_label,
    }
)
PY
```

## 11.25 Minutes: Fingerprint Showcase Script

Run the canonical v0.3.1 showcase when you want the full prepared archetype
panel, strict A1/A2/A3 agent verification, and a final human-language summary
of what the mathematics did.

```bash
MPLBACKEND=Agg uv run scripts/run_showcase_fingerprint.py --smoke
```

Inspect these artifacts after the run:

- `outputs/figures/showcase_fingerprint/fingerprint_profiles.png`
- `outputs/figures/showcase_fingerprint/fingerprint_metrics.png`
- `outputs/tables/showcase_fingerprint/fingerprint_summary.csv`
- `outputs/tables/showcase_fingerprint/fingerprint_routing.csv`
- `outputs/reports/showcase_fingerprint/showcase_report.md`
- `outputs/reports/showcase_fingerprint/verification.md`

> [!IMPORTANT]
> The fingerprint release is intentionally univariate-first and AMI-first. The
> routing output is heuristic family guidance, not exact-model selection and not
> a multivariate conditional-MI claim.

## 12 Minutes: CSV Batch Geometry Workflow

Use the CSV adapter when your upstream workflow already has one target series per
column and you want a summary CSV plus geometry artifacts without notebook-only
logic.

Build the synthetic input panel from the prepared generators and run the repo
script:

```bash
uv run python examples/univariate/fingerprint/ami_information_geometry_csv_example.py

uv run python scripts/run_ami_information_geometry_csv.py \
  --input-csv outputs/examples/ami_geometry_csv/inputs/synthetic_fingerprint_panel.csv \
  --output-root outputs/ami_geometry_csv_script \
  --max-lag 24 \
  --n-surrogates 99 \
  --random-state 42
```

Inspect these artifacts after the run:

- `outputs/ami_geometry_csv_script/tables/ami_geometry_summary.csv`
- `outputs/ami_geometry_csv_script/figures/ami_geometry_profiles.png`
- `outputs/ami_geometry_csv_script/reports/ami_geometry_batch.md`

> [!NOTE]
> The CSV adapter drops missing values column-wise and skips too-short or
> non-numeric series conservatively instead of forcing a partial analysis.

## 11.5 Minutes: Batch Forecast Routing And Executive Brief

Use the batch workbench when you need one deterministic pass that serves both
analyst and stakeholder workflows.

```bash
uv run python - <<'PY'
from forecastability import (
    build_batch_forecastability_executive_markdown,
    build_batch_forecastability_markdown,
    generate_fingerprint_archetypes,
    run_batch_forecastability_workbench,
)
from forecastability.triage import BatchSeriesRequest, BatchTriageRequest

series_map = generate_fingerprint_archetypes(n=320, seed=42)
request = BatchTriageRequest(
    items=[
        BatchSeriesRequest(series_id=name, series=series.tolist())
        for name, series in series_map.items()
    ],
    max_lag=24,
    n_surrogates=99,
    random_state=42,
)
result = run_batch_forecastability_workbench(request, top_n=2)

print(result.summary.technical_summary)
print(result.items[0].next_step.action)
print(build_batch_forecastability_markdown(result).splitlines()[0])
print(build_batch_forecastability_executive_markdown(result).splitlines()[0])
PY
```

## 12 Minutes: Covariant Informative Workflow

Run the v0.3.0 covariant bundle with pairwise and directional methods:

```bash
uv run python - <<'PY'
from forecastability import generate_covariant_benchmark, run_covariant_analysis

df = generate_covariant_benchmark(n=1200, seed=42)
target = df["target"].to_numpy()
drivers = {name: df[name].to_numpy() for name in df.columns if name != "target"}

bundle = run_covariant_analysis(
  target,
  drivers,
  target_name="target",
  max_lag=5,
  methods=["cross_ami", "cross_pami", "te", "gcmi"],
  n_surrogates=99,
  random_state=42,
)

print(
  {
    "rows": len(bundle.summary_table),
    "active_methods": bundle.metadata.get("active_methods"),
    "skipped_optional_methods": bundle.metadata.get("skipped_optional_methods"),
    "conditioning_scope_disclaimer": bundle.metadata.get("conditioning_scope_disclaimer"),
  }
)
PY
```

Expected output shape:

```json
{
  "rows": 40,
  "active_methods": "cross_ami,cross_pami,gcmi,te",
  "skipped_optional_methods": null,
  "conditioning_scope_disclaimer": "Bundle conditioning scope: ..."
}
```

> [!NOTE]
> Valid covariant method tokens are `cross_ami`, `cross_pami`, `te`, `gcmi`, `pcmci`, and `pcmci_ami`.

> [!IMPORTANT]
> `pcmci` and `pcmci_ami` are optional causal methods. Install the causal extra when needed:
>
> ```bash
> pip install "dependence-forecastability[causal]"
> ```

## 15 Minutes: HTTP API Call

Terminal A: start the API server.

```bash
uv sync --extra transport
uv run uvicorn forecastability.adapters.api:app --host 127.0.0.1 --port 8000
```

Terminal B: generate the same payload and call `POST /triage`.

```bash
uv run python - <<'PY'
import json
from forecastability import generate_ar1

payload = {
    "series": generate_ar1(n_samples=150, phi=0.85, random_state=42).tolist(),
    "goal": "univariate",
    "max_lag": 20,
    "n_surrogates": 99,
    "random_state": 42,
}
with open("/tmp/forecastability_ar1_payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f)
PY

curl -sS -X POST http://127.0.0.1:8000/triage \
  -H 'Content-Type: application/json' \
  --data @/tmp/forecastability_ar1_payload.json
```

Expected output snippet:

```json
{
  "blocked": false,
  "readiness_status": "warning",
  "route": "univariate_no_significance",
  "compute_surrogates": false,
  "forecastability_class": "high",
  "modeling_regime": "compact_structured_models",
  "primary_lags": [1, 7],
  "recommendation": "HIGH -> Complex structured models (deep AR, nonlinear, LSTM)"
}
```

## Optional: Agent Narration

```bash
uv sync --extra agent
```

Set provider configuration in `.env` (for example `OPENAI_API_KEY` and
`OPENAI_MODEL`), then run:

```bash
uv run python - <<'PY'
import asyncio
import json
from forecastability import generate_ar1
# Canonical import: forecastability.adapters.llm.triage_agent
# The path below uses the backward-compat shim and will be removed in a future release.
from forecastability.adapters.pydantic_ai_agent import run_triage_agent

async def main() -> None:
    series = generate_ar1(n_samples=150, phi=0.85, random_state=42)
    explanation = await run_triage_agent(
        series,
        max_lag=20,
        n_surrogates=99,
        random_state=42,
    )
    print(
        json.dumps(
            {
                "forecastability_class": explanation.forecastability_class,
                "directness_class": explanation.directness_class,
                "modeling_regime": explanation.modeling_regime,
                "primary_lags": explanation.primary_lags,
                "recommendation": explanation.recommendation,
                "narrative": explanation.narrative,
                "caveats": explanation.caveats,
            },
            indent=2,
        )
    )

asyncio.run(main())
PY
```

Expected output snippet:

```json
{
  "forecastability_class": "high",
  "directness_class": "medium",
  "modeling_regime": "compact_structured_models",
  "primary_lags": [1, 7],
  "recommendation": "HIGH -> Complex structured models (deep AR, nonlinear, LSTM)",
  "narrative": "...model-generated explanation...",
  "caveats": [
    "Series length (150) < 200. Surrogate significance bands may be unstable; interpret p-values with caution."
  ]
}
```

## Optional: MCP Integration

Start the MCP server:

```bash
uv sync --extra transport
uv run python -m forecastability.adapters.mcp_server
```

From an MCP client, call tool `run_triage_tool` with:

```json
{
  "series": "same AR(1) list as above",
  "goal": "univariate",
  "max_lag": 20,
  "n_surrogates": 99,
  "random_state": 42
}
```

Expected tool output snippet:

```json
{
  "blocked": false,
  "readiness": {
    "status": "warning"
  },
  "method_plan": {
    "route": "univariate_no_significance",
    "compute_surrogates": false
  },
  "interpretation": {
    "forecastability_class": "high",
    "modeling_regime": "compact_structured_models",
    "primary_lags": [1, 7]
  },
  "recommendation": "HIGH -> Complex structured models (deep AR, nonlinear, LSTM)"
}
```

## Triage Extension Diagnostics

Beyond the core triage output, `run_triage()` populates optional diagnostic
fields (F1–F6) when the series is not blocked. These give deeper insight into
*why* the series is forecastable and *where* the information ceiling lies.

```python
from forecastability.triage import run_triage, TriageRequest
import numpy as np

rng = np.random.default_rng(42)
ts = np.array([0.85 ** i + rng.standard_normal() * 0.1 for i in range(300)])

result = run_triage(TriageRequest(series=ts, goal="univariate", random_state=42))

# F1: Forecastability profile — informative horizons and peak lag
if result.forecastability_profile:
    print(f"Peak horizon: {result.forecastability_profile.peak_horizon}")
    print(f"Informative horizons: {result.forecastability_profile.informative_horizons}")

# F2: IT limit diagnostics — ceiling and data-processing warnings
if result.theoretical_limit_diagnostics:
    print(f"Compression warning: {result.theoretical_limit_diagnostics.compression_warning}")

# F5: Largest Lyapunov exponent (experimental)
if result.largest_lyapunov_exponent:
    print(f"Lyapunov exponent: {result.largest_lyapunov_exponent.exponent}")

# F6: Complexity band
if result.complexity_band:
    print(f"Complexity band: {result.complexity_band.band}")
```

All diagnostic fields are `None` when the series is blocked by readiness gates.

> [!TIP]
> For interactive walkthroughs of each diagnostic family, see the triage
> extension notebooks in [`notebooks/triage/`](../notebooks/triage/).
