<!-- type: how-to -->
# Golden Path

The opinionated path from install to a trustworthy first result in the live repository.

_Last verified for release 0.2.0 consolidation on 2026-04-14._

Follow this path before you reach for the CLI, API, dashboard, MCP, or agent layers.

## 1. Choose The Right Install Context

If you want the published package surface, install from PyPI.

```bash
pip install dependence-forecastability
```

If you are working in the repository, sync the local environment.

```bash
uv sync
```

## 2. Run One Deterministic Triage Call

Use the stable package facade and a simple generated series.

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
```

> [!IMPORTANT]
> AMI is computed per horizon. pAMI is a project extension that uses a linear-residual approximation rather than exact conditional mutual information.

## 3. Read The Minimum Trust Fields

Start with the fields that tell you whether the result is usable and whether significance was actually computed.

```python
summary = {
    "blocked": result.blocked,
    "readiness_status": result.readiness.status.value,
    "compute_surrogates": None if result.method_plan is None else result.method_plan.compute_surrogates,
    "forecastability_class": None if result.interpretation is None else result.interpretation.forecastability_class,
    "primary_lags": [] if result.interpretation is None else list(result.interpretation.primary_lags),
    "recommendation": result.recommendation,
}
print(summary)
```

Interpret those fields in this order.

| Field | What it tells you |
| --- | --- |
| `blocked` | Whether triage completed at all |
| `readiness_status` | Whether the data is clear, warning-level, or blocked |
| `compute_surrogates` | Whether significance was actually computed |
| `forecastability_class` | High-level interpretation when triage completed |
| `primary_lags` | Informative lags identified by the deterministic workflow |

> [!NOTE]
> `blocked` is different from “no forecastable structure.” A blocked result means the workflow could not support the requested computation.
> [!NOTE]
> When `compute_surrogates` is `false`, significance was skipped or suppressed. That is different from a run where surrogates were computed and no lags were significant.
> [!CAUTION]
> Phase-randomized FFT surrogates preserve the power spectrum. For highly periodic series, they can make significance tests conservative or uninformative even when the underlying series is obviously structured.

## 4. Follow The Canonical Notebook Path

Use the live notebooks directly.

1. Read [notebooks/README.md](notebooks/README.md).
2. Run [../notebooks/walkthroughs/00_air_passengers_showcase.ipynb](../notebooks/walkthroughs/00_air_passengers_showcase.ipynb).
3. Continue through walkthrough notebooks `01` to `04`.
4. Use the `notebooks/triage/` notebooks only after the walkthroughs; they are deep dives, not first-stop onboarding.

## 5. Use The Maintainer Workflows When You Need Repo Outputs

These are the repository workflows that align with the current codebase.

| Workflow | Command |
| --- | --- |
| Canonical triage artifacts | `uv run python scripts/run_canonical_triage.py` |
| Benchmark panel | `uv run python scripts/run_benchmark_panel.py` |
| Report artifacts | `uv run python scripts/build_report_artifacts.py` |

The main checked-in artifact surfaces are:

- `outputs/json/canonical_examples_summary.json` and related canonical JSON outputs
- `outputs/tables/*.csv`
- `outputs/reports/*.md`

Treat those as reference artifacts, not guaranteed-fresh build outputs.

## 6. Add Optional Surfaces Only After The Core Path Is Clear

| Surface | Entry point | Stability |
| --- | --- | --- |
| CLI | `forecastability` | Beta |
| HTTP API | `forecastability.adapters.api:app` | Beta |
| Dashboard | `forecastability-dashboard` | Beta |
| MCP server | adapter surface | Experimental |
| Agent narration | adapter surface | Experimental |

> [!WARNING]
> In rolling-origin evaluation, diagnostics are computed on train windows only and scoring on post-origin holdout only.

For the multi-surface walkthrough, see [quickstart.md](quickstart.md). For the exact HTTP contract, see [api_contract.md](api_contract.md).
