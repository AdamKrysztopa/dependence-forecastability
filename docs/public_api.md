<!-- type: reference -->
# Public API Guide

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.

This page lists all stable import paths an integrator should use. Symbols not listed here are
internal and may change without notice.

> [!IMPORTANT]
> Only import from the two stable entry points: the top-level `forecastability` package and its
> `forecastability.triage` subpackage. All other subpackages are internal.

For stability levels and semantic versioning policy, see [versioning.md](versioning.md).

---

## Stable import paths

### Core triage entry points

Available from `forecastability.triage`:

```python
from forecastability.triage import run_triage         # run one triage
from forecastability.triage import run_batch_triage   # run a batch
```

`run_triage` accepts a `TriageRequest` and returns a `TriageResult`.
`run_batch_triage` accepts a `BatchTriageRequest` and returns a `BatchTriageResponse`.

> [!NOTE]
> These functions are re-exported by `forecastability.triage` for convenience. A future release
> will also expose them from the top-level `forecastability` package directly.

### Analyzer

Available from the top-level `forecastability` package:

```python
from forecastability import ForecastabilityAnalyzer      # univariate AMI/pAMI analyzer
from forecastability import ForecastabilityAnalyzerExog  # exogenous (cross-AMI/pAMI) analyzer
from forecastability import AnalyzeResult                # analyzer output container
```

### Triage request and result models

Available from `forecastability.triage`:

```python
from forecastability.triage import TriageRequest         # input to run_triage()
from forecastability.triage import TriageResult          # output of run_triage()
from forecastability.triage import ReadinessReport       # pre-triage feasibility report
from forecastability.triage import ReadinessStatus       # enum: READY / BLOCKED / DEGRADED
from forecastability.triage import ReadinessWarning      # individual readiness warning
from forecastability.triage import MethodPlan            # selected computation strategy
from forecastability.triage import AnalysisGoal          # enum driving method selection
```

### Triage diagnostic result types

Available from the top-level `forecastability` package:

```python
from forecastability import ForecastabilityProfile         # F1 — AMI/pAMI horizon profile
from forecastability import SpectralPredictabilityResult   # F4 — spectral predictability score Ω
from forecastability import PredictiveInfoLearningCurve    # F3 — EvoRate-style lookback analysis
```

Also available from `forecastability.triage`:

```python
from forecastability.triage import ComplexityBandResult          # F6 — entropy/complexity band
from forecastability.triage import LargestLyapunovExponentResult # F5 — experimental LLE
```

> [!CAUTION]
> `LargestLyapunovExponentResult` corresponds to F5. Largest Lyapunov exponent is experimental
> and excluded from automated triage decisions. See [diagnostics_matrix.md](diagnostics_matrix.md).

### Result types (analyzer and canonical workflows)

Available from the top-level `forecastability` package:

```python
from forecastability import InterpretationResult       # interpretation of one canonical result
from forecastability import Diagnostics                # raw AMI/pAMI numeric payloads
from forecastability import CanonicalExampleResult     # full single-series canonical run output
from forecastability import CanonicalSummary           # cross-series summary
from forecastability import SeriesEvaluationResult     # one rolling-origin evaluation row
from forecastability import ForecastResult             # model forecast and error record
from forecastability import MetricCurve                # lag-indexed metric curve
from forecastability import BackendComparisonResult    # pAMI backend comparison
from forecastability import ExogenousBenchmarkResult   # exogenous benchmark panel output
from forecastability import RobustnessStudyResult      # robustness study output
from forecastability import SampleSizeStressResult     # sample-size stress test output
```

### Triage batch and comparison models

Available from `forecastability.triage`:

```python
from forecastability.triage import BatchTriageRequest        # input to run_batch_triage()
from forecastability.triage import BatchTriageResponse       # output of run_batch_triage()
from forecastability.triage import BatchSeriesRequest        # one series in a batch
from forecastability.triage import BatchSummaryRow           # one ranked summary row
from forecastability.triage import BatchFailureRow           # one failure row
from forecastability.triage import BatchTriageExecution      # full execution record
from forecastability.triage import BatchTriageExecutionItem  # one execution item
from forecastability.triage import BatchTriageItemResult     # one item result container
```

Column name constants:

```python
from forecastability.triage import SUMMARY_TABLE_COLUMNS  # column list for summary DataFrame
from forecastability.triage import FAILURE_TABLE_COLUMNS  # column list for failure DataFrame
```

### Triage result bundle (serializable snapshots)

Available from `forecastability.triage`:

```python
from forecastability.triage import TriageResultBundle      # full serializable snapshot
from forecastability.triage import TriageNumericOutputs    # numeric payload extracted from result
from forecastability.triage import TriageConfigSnapshot    # config frozen at run time
from forecastability.triage import TriageInputMetadata     # input series metadata
from forecastability.triage import TriageBundleProvenance  # provenance record
from forecastability.triage import TriageBundleWarning     # provenance warning
from forecastability.triage import TriageVersions          # package version pins

from forecastability.triage import save_result_bundle         # write bundle to disk
from forecastability.triage import load_result_bundle         # read bundle from disk
from forecastability.triage import save_triage_result_bundle  # convenience wrapper
from forecastability.triage import build_triage_result_bundle # construct bundle from result
```

### Triage events (observability)

Available from `forecastability.triage` for streaming or audit consumers:

```python
from forecastability.triage import TriageEvent          # base event type
from forecastability.triage import TriageStageStarted   # stage-start signal
from forecastability.triage import TriageStageCompleted # stage-complete signal
from forecastability.triage import TriageError          # stage-failure signal
```

### Scorer registry

Available from the top-level `forecastability` package:

```python
from forecastability import DependenceScorer  # protocol for univariate diagnostic scorers
from forecastability import ScorerInfo        # scorer metadata
from forecastability import ScorerRegistry    # registry of available scorers
from forecastability import default_registry  # pre-populated default registry instance
```

### Config models

Available from the top-level `forecastability` package:

```python
from forecastability import CMIConfig               # CMI computation settings
from forecastability import MetricConfig            # metric settings
from forecastability import ModelConfig             # model settings
from forecastability import OutputConfig            # output path settings
from forecastability import RollingOriginConfig     # rolling-origin split settings
from forecastability import SensitivityConfig       # sensitivity analysis settings
from forecastability import UncertaintyConfig       # uncertainty settings
from forecastability import BenchmarkDataConfig     # benchmark data settings
from forecastability import ExogenousBenchmarkConfig # exogenous benchmark settings
from forecastability import RobustnessStudyConfig   # robustness study settings
```

### Dataset helpers

Available from the top-level `forecastability` package:

```python
from forecastability import generate_ar1             # generate AR(1) test series
from forecastability import generate_white_noise     # generate white noise series
from forecastability import ar1_theoretical_ami      # theoretical AMI curve for AR(1)
```

### Validation

Available from the top-level `forecastability` package:

```python
from forecastability import validate_time_series  # validate a numpy series at the boundary
```

---

## What NOT to import

The following subpackages are **internal**. Their contents may be renamed, moved, or removed
without notice in any release:

| Internal subpackage | Why |
|---|---|
| `forecastability.adapters.*` | Infrastructure adapters (CLI, HTTP, MCP, LLM) |
| `forecastability.services.*` | Pipeline orchestration services |
| `forecastability.ports.*` | Port protocols and impls |
| `forecastability.use_cases.*` | Use-case implementations — import via `forecastability.triage` instead |
| `forecastability.triage.models` | Import from `forecastability.triage` directly |
| `forecastability.triage.batch_models` | Import from `forecastability.triage` directly |

Specific files that are not part of the public API:

- `adapters/pydantic_ai_agent.py` — deprecated shim; will be removed
- `adapters/llm/` — experimental LLM adapter internals
- `adapters/mcp_server.py` — MCP server adapter (experimental surface)
- `adapters/cli.py` — CLI entrypoint (beta surface)
- `use_cases/requests.py` — internal request types for agent seams, explicitly not exported

---

## Stability contract

| Symbol group | Stability | Notes |
|---|---|---|
| `run_triage`, `run_batch_triage` | **stable** | Core deterministic triage; will not break across MINOR + PATCH |
| `ForecastabilityAnalyzer`, `ForecastabilityAnalyzerExog`, `AnalyzeResult` | **stable** | Analyzer public API; compatibility-sensitive |
| `TriageRequest`, `TriageResult`, `ReadinessReport`, `MethodPlan` | **stable** | Triage I/O models; JSON field names are part of the contract |
| `ForecastabilityProfile`, `SpectralPredictabilityResult`, `PredictiveInfoLearningCurve`, `ComplexityBandResult` | **stable** | Diagnostic result types F1, F3, F4, F6 |
| `BatchTriageRequest`, `BatchTriageResponse`, batch row models | **stable** | F7 batch triage; diagnostic columns are contract-sensitive |
| `TriageResultBundle` and bundle subtypes | **stable** | Serializable snapshot contract; JSON field names stable |
| `DependenceScorer` protocol, `ScorerRegistry`, `default_registry` | **stable** | Scorer extension point |
| `InterpretationResult`, `Diagnostics`, and top-level result types | **stable** | Canonical workflow outputs |
| Config models (`CMIConfig`, `RollingOriginConfig`, etc.) | **stable** | Settings models for pipeline configuration |
| `TriageEvent` hierarchy | **stable** | Observability event contract |
| `LargestLyapunovExponentResult` | **experimental** | F5: numerically fragile; no stability guarantee; excluded from automated triage |
| CLI surface (`forecastability triage`, `forecastability list-scorers`) | **beta** | Usable but option and output details may still be refined |
| HTTP API (FastAPI + SSE) | **beta** | Endpoint and stream payload details may evolve |
| MCP server tools | **experimental** | Tool names and payloads may change |
| Agent layer (`adapters/pydantic_ai_agent.py`) | **experimental** | Deprecated shim; will be removed |

Cross-reference: [versioning.md](versioning.md) for the full stability table and semantic
versioning policy.

---

## Payload and schema stability

All stable result types are Pydantic models. Their JSON field names are part of the stability
contract:

- Serialising with `.model_dump()` or `.model_dump_json()` produces a stable field set for
  stable types.
- Adding optional fields with `None` defaults is considered backward-compatible.
- Removing fields or changing field types is a breaking change requiring a `Migration notes`
  entry in `CHANGELOG.md`.

```python
result: TriageResult = run_triage(request)

# Stable serialisation — field names will not change in MINOR/PATCH releases
payload = result.model_dump()

# Round-trip deserialisation
restored = TriageResult.model_validate(payload)
```

---

## Backward-compatible import paths

`forecastability.triage` re-exports `run_triage` and `run_batch_triage` as the stable import
path today. A future release will also provide these at the top-level `forecastability` package:

| Import (today — stable) | Planned top-level alias | Notes |
|---|---|---|
| `from forecastability.triage import run_triage` | `from forecastability import run_triage` | Planned; not yet available |
| `from forecastability.triage import run_batch_triage` | `from forecastability import run_batch_triage` | Planned; not yet available |

> [!TIP]
> Use `from forecastability.triage import run_triage` in new code. When the top-level alias is
> added it will be a purely additive change — your existing imports will continue to work.

---

## Not in the public API

The following are explicitly out of scope for the stability contract:

- **`adapters/pydantic_ai_agent.py`** — deprecated shim; do not use in new integrations.
- **`adapters/llm/`** — experimental LLM narration adapters.
- **`adapters/mcp_server.py`** — MCP server tool schemas; part of the experimental MCP surface.
- **`adapters/cli.py`** — CLI entrypoint internals; the user-facing commands are the stable
  surface, not the adapter code behind them.
- **`services/`** — internal pipeline orchestration; may be refactored at any time.
- **`ports/`** — port protocols and implementations; internal hexagonal boundary.
- **`use_cases/requests.py`** — internal agent seam request types; explicitly not exported.

> [!NOTE]
> CLI, API, notebooks, MCP, and agents are optional access or narration layers around the same
> deterministic outputs. The Python import API documented here is the primary integration surface
> for programmatic use.
