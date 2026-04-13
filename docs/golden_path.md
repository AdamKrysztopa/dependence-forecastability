<!-- type: how-to -->
# Golden Path

The opinionated path from install to first trustworthy forecastability output.

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.
CLI, API, notebooks, MCP, and agents are optional access or narration layers around the same deterministic outputs.
Follow this path first before exploring those layers.

---

## 1. Install

Install and sync the project using `uv`. Full install details are in [quickstart.md](quickstart.md) and the top-level [README](../README.md).

```bash
uv sync
```

> [!NOTE]
> This path uses the `forecastability` package already present in the repo.
> Do not set up a separate install until the PyPI release is available.

---

## 2. Run one deterministic example

Run the canonical AR(1) signal through `run_triage()`. This is the primary deterministic path.

```python
import numpy as np
from forecastability import generate_ar1
from forecastability.triage import TriageRequest, run_triage

# Canonical AR(1) signal: n=150, phi=0.85, random_state=42
series = generate_ar1(n_samples=150, phi=0.85, random_state=42)

result = run_triage(
    TriageRequest(
        series=series,
        goal="univariate",
        max_lag=20,
        n_surrogates=99,        # minimum for significance bands
        random_state=42,
    )
)
```

> [!IMPORTANT]
> Surrogate significance is optional, conditional on feasible sample size, and requires at least 99 surrogates.
> Setting `n_surrogates=0` skips significance bands — that is a valid choice, not a shortcut.

---

## 3. Understand the result

The triage result is a structured deterministic payload. Extract the key fields:

```python
summary = {
    "blocked": result.blocked,
    "readiness_status": result.readiness.status.value,
    "forecastability_class": result.interpretation.forecastability_class,
    "modeling_regime": result.interpretation.modeling_regime,
    "primary_lags": list(result.interpretation.primary_lags),
    "recommendation": result.recommendation,
}
print(summary)
```

Expected output for the canonical AR(1) setup:

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

### Field guide

| Field | Meaning |
|---|---|
| `blocked` | `true` if triage could not complete (e.g. series too short, degenerate) |
| `readiness_status` | Data readiness for forecasting: `ok`, `warning`, or `blocked` |
| `forecastability_class` | AMI-based triage outcome: `high`, `medium`, `low`, or `none` |
| `modeling_regime` | Recommended model family based on lag structure and strength |
| `primary_lags` | Informative lag indices with significant AMI |
| `recommendation` | Human-readable recommendation string |

> [!NOTE]
> `blocked=true` is a distinct outcome from `forecastability_class="none"`. A blocked result means triage
> could not run; a `none` class means triage ran and found no forecastable structure.

---

## 4. Explore deeper

Once you have a trustworthy first result, explore the walkthrough notebooks to understand the
AMI horizon profile, pAMI (project extension) as approximate direct-dependence diagnostic,
and the full triage chain.

**Recommended next step:**

```bash
uv sync --group notebook
uv run jupyter lab
```

Open `notebooks/triage/01_forecastability_profile_walkthrough.ipynb`.

For a full end-to-end triage walkthrough, see `notebooks/walkthroughs/03_triage_end_to_end.ipynb`.

For the multi-surface comparison (CLI / API / notebook / MCP), see [quickstart.md](quickstart.md).

---

## 5. Optional integrations (not the default path)

Use these only after the deterministic path is clear.

| Surface | Stability | When to use |
|---|---|---|
| **CLI** (`forecastability triage`) | beta | Scripting, one-off runs, shell pipelines |
| **HTTP API** (`uvicorn forecastability.server:app`) | beta | Service integration, remote calls |
| **MCP server** | experimental | Agent orchestration, LLM-tool integrations |
| **Agent layer** | experimental | LLM narration over deterministic outputs |

> [!WARNING]
> Largest Lyapunov exponent is experimental and excluded from automated triage decisions.
> It appears in F5 diagnostics and extended notebooks but must not influence triage outcomes.

> [!WARNING]
> In rolling-origin evaluation, diagnostics are computed on train windows only and scoring
> on post-origin holdout only. Do not compute diagnostics on the full series and claim
> out-of-sample validity.

For CLI and HTTP API usage, see [quickstart.md](quickstart.md).
For MCP and agent integration, see [agent_layer.md](agent_layer.md) and [api_contract.md](api_contract.md).
For stability guarantees on each surface, see [versioning.md](versioning.md).
