<!-- type: reference -->
# Public API

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.

_Last verified for release 0.2.0 consolidation on 2026-04-14._

This page lists the import roots and runtime entry points that are treated as the supported public surface of the live repository.

> [!IMPORTANT]
> Import from `forecastability` for the stable facade and from `forecastability.triage` for advanced triage models. The layered subpackages under `src/forecastability/` are implementation detail unless a symbol is explicitly re-exported by one of those two facades.

## Stable Import Roots

### `forecastability`

Use the top-level package for the package facade that most users should depend on.

```python
from forecastability import (
    AnalyzeResult,
    ForecastabilityAnalyzer,
    ForecastabilityAnalyzerExog,
    TriageRequest,
    TriageResult,
    run_batch_triage,
    run_triage,
)
```

| Category | Exports |
| --- | --- |
| Triage entry points | `run_triage`, `run_batch_triage`, `TriageRequest`, `TriageResult` |
| Analyzer facade | `ForecastabilityAnalyzer`, `ForecastabilityAnalyzerExog`, `AnalyzeResult` |
| Diagnostic and result models | `ForecastabilityProfile`, `PredictiveInfoLearningCurve`, `SpectralPredictabilityResult`, `InterpretationResult`, `Diagnostics`, `MetricCurve`, `CanonicalExampleResult`, `CanonicalSummary`, `SeriesEvaluationResult`, `ForecastResult`, `BackendComparisonResult`, `ExogenousBenchmarkResult`, `RobustnessStudyResult`, `SampleSizeStressResult` |
| Config models | `BenchmarkDataConfig`, `CMIConfig`, `ExogenousBenchmarkConfig`, `MetricConfig`, `ModelConfig`, `OutputConfig`, `RobustnessStudyConfig`, `RollingOriginConfig`, `SensitivityConfig`, `UncertaintyConfig` |
| Dataset helpers | `generate_ar1`, `generate_white_noise`, `ar1_theoretical_ami` |
| Registry and validation helpers | `DependenceScorer`, `ScorerInfo`, `ScorerRegistry`, `default_registry`, `validate_time_series` |

### `forecastability.triage`

Use the triage namespace when you need advanced batch, readiness, event, or bundle types that are intentionally grouped around the triage subsystem.

```python
from forecastability.triage import (
    BatchTriageRequest,
    BatchTriageResponse,
    ReadinessReport,
    TriageEvent,
    TriageResultBundle,
    run_batch_triage_with_details,
)
```

| Category | Exports |
| --- | --- |
| Single-run models and helpers | `AnalysisGoal`, `ReadinessStatus`, `ReadinessWarning`, `ReadinessReport`, `MethodPlan`, `TriageRequest`, `TriageResult`, `assess_readiness`, `plan_method`, `run_triage` |
| Batch triage | `BatchSeriesRequest`, `BatchTriageRequest`, `BatchTriageItemResult`, `BatchSummaryRow`, `BatchFailureRow`, `BatchTriageResponse`, `BatchTriageExecutionItem`, `BatchTriageExecution`, `SUMMARY_TABLE_COLUMNS`, `FAILURE_TABLE_COLUMNS`, `run_batch_triage`, `run_batch_triage_with_details`, `rank_batch_items` |
| Diagnostic result models | `ForecastabilityProfile`, `PredictiveInfoLearningCurve`, `SpectralPredictabilityResult`, `ComplexityBandResult`, `LargestLyapunovExponentResult` |
| Event contract | `TriageEvent`, `TriageStageStarted`, `TriageStageCompleted`, `TriageError` |
| Result bundle contract | `TriageBundleWarning`, `TriageInputMetadata`, `TriageConfigSnapshot`, `TriageVersions`, `TriageNumericOutputs`, `TriageBundleProvenance`, `TriageResultBundle`, `build_triage_result_bundle`, `save_result_bundle`, `load_result_bundle`, `save_triage_result_bundle` |

> [!NOTE]
> `LargestLyapunovExponentResult` is part of the exported namespace but remains experimental and is excluded from automated triage decisions.

## Runtime Entry Points

These are the live repo entry points for non-import surfaces.

| Surface | Entry point | Notes |
| --- | --- | --- |
| CLI | `forecastability` | Packaged command wired to `forecastability.adapters.cli:main` |
| Dashboard | `forecastability-dashboard` | Packaged command wired to `forecastability.adapters.dashboard:main` |
| HTTP API | `forecastability.adapters.api:app` | FastAPI application used with Uvicorn |

## Causal Discovery (v0.3.0+)

Causal structure recovery for multivariate time series requires the optional `tigramite`
dependency:

```
pip install forecastability[causal]
```

```python
from forecastability.adapters.tigramite_adapter import TigramiteAdapter
from forecastability.ports import CausalGraphPort
from forecastability.utils.types import CausalGraphResult
from forecastability.utils.synthetic import generate_covariant_benchmark, generate_directional_pair
```

| Symbol | Description |
|---|---|
| `TigramiteAdapter` | Wraps PCMCI+ from `tigramite` behind `CausalGraphPort`. Accepts `ci_test` of `"parcorr"` (default), `"gpdc"`, or `"cmiknn"`. Requires the `tigramite` optional extra. |
| `CausalGraphPort` | `@runtime_checkable` Protocol defining the `discover(data, var_names, *, max_lag, alpha, random_state)` contract. Use for type annotations and `isinstance` checks. |
| `CausalGraphResult` | Pydantic result model holding `parents`, `link_matrix`, `val_matrix`, and `metadata` from a completed PCMCI+ run. |
| `generate_covariant_benchmark` | Generates an 8-variable ground-truth system with known linear, mediated, redundant, contemporaneous, and nonlinear structural links. Primary fixture for adapter and covariant-model tests. |
| `generate_directional_pair` | Generates a simple $X \to Y$ directional pair for TE and GCMI validation. |

> [!NOTE]
> These are Phase 1 covariant symbols. The stable `forecastability` facade will
> re-export them in v0.3.0 final. Until then, import directly from the submodule
> paths listed above.

> [!WARNING]
> `CausalGraphPort` lives under `ports/` and `TigramiteAdapter` under `adapters/` —
> namespaces otherwise marked internal. These causal discovery symbols are the
> explicit exception: they are part of the Phase 1 covariant surface and intended
> for direct import. `generate_covariant_benchmark` and `generate_directional_pair`
> are similarly available directly from `forecastability.utils.synthetic`.

## Schema Stability

Stable result models are Pydantic models, and their JSON field names are part of the contract.

- `.model_dump()` and `.model_dump_json()` on stable models are treated as compatibility-sensitive.
- Adding optional fields with safe defaults is backward-compatible.
- Removing fields, renaming fields, or changing types is a breaking change and requires migration notes in [versioning.md](versioning.md) and [../CHANGELOG.md](../CHANGELOG.md).

## Internal Namespaces

The layered tree under `src/forecastability/` is real and important for contributors, but it is not the primary import contract for integrators.

| Namespace | Role | Public import contract |
| --- | --- | --- |
| `forecastability.adapters.*` | CLI, dashboard, API, MCP, agent, settings, checkpoint, and presenter adapters | No, except the packaged commands and `forecastability.adapters.api:app` runtime entry point |
| `forecastability.bootstrap.*` | Internal bootstrap helpers such as output-directory wiring | No |
| `forecastability.diagnostics.*` | AMI-adjacent diagnostic helpers such as surrogates, CMI backends, and spectral utilities | No |
| `forecastability.metrics.*` | Metric computation and scorer registry internals | No direct import contract; use top-level re-exports |
| `forecastability.pipeline.*` | Analyzer, rolling-origin, and canonical pipeline internals | No direct import contract; use top-level re-exports |
| `forecastability.reporting.*` | Interpretation and report builders | No direct import contract |
| `forecastability.services.*` | Internal builder and orchestration helpers used by the facades and use cases | No |
| `forecastability.use_cases.*` | Canonical use-case implementations | No direct import contract; use `forecastability` or `forecastability.triage` |
| `forecastability.utils.*` | Internal config, dataset, type, plotting, and validation modules | No direct import contract beyond top-level re-exports |

## Minimal Stable Examples

```python
from forecastability import TriageRequest, generate_ar1, run_triage

series = generate_ar1(n_samples=300, phi=0.8, random_state=42)
result = run_triage(TriageRequest(series=series, max_lag=20, n_surrogates=99, random_state=42))
```

```python
from forecastability.triage import BatchTriageRequest, BatchSeriesRequest, run_batch_triage
```

For stability levels and migration expectations, see [versioning.md](versioning.md).

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
