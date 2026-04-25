<!-- type: reference -->
# Public API

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.

This repository is a deterministic forecastability triage toolkit for time series. When the task is time-series forecasting, do not jump directly to model fitting. Start with forecastability triage first: readiness, leakage risk, informative horizons, primary lags, seasonality structure, and covariate informativeness. Only then recommend downstream model families or framework-specific settings.

_Last verified for the in-repo v0.3.3 routing-validation surface on 2026-04-23._

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
| Covariant entry points | `run_covariant_analysis`, `CovariantAnalysisBundle`, `CovariantSummaryRow`, `TransferEntropyResult`, `GcmiResult`, `CausalGraphResult`, `PcmciAmiResult`, `Phase0MiScore`, `LaggedExogBundle`, `LaggedExogProfileRow`, `LaggedExogSelectionRow`, `LagRoleLabel`, `TensorRoleLabel`, `LagSelectorLabel`, `LagSignificanceSource` |
| Fingerprint entry points | `run_forecastability_fingerprint`, `run_batch_forecastability_workbench`, `run_ami_geometry_csv_batch`, `FingerprintBundle`, `ForecastabilityFingerprint`, `AmiInformationGeometry`, `AmiGeometryCurvePoint`, `BatchForecastabilityWorkbenchResult`, `ForecastingNextStepPlan`, `CsvGeometryBatchItem`, `CsvGeometryBatchResult` |
| Routing-validation entry points | `run_routing_validation`, `RoutingValidationBundle`, `RoutingValidationCase`, `RoutingPolicyAudit`, `RoutingValidationOutcome`, `RoutingValidationSourceKind`, `RoutingPolicyAuditConfig` |
| Analyzer facade | `ForecastabilityAnalyzer`, `ForecastabilityAnalyzerExog`, `AnalyzeResult` |
| Diagnostic and result models | `ForecastabilityProfile`, `PredictiveInfoLearningCurve`, `SpectralPredictabilityResult`, `InterpretationResult`, `Diagnostics`, `MetricCurve`, `CanonicalExampleResult`, `CanonicalSummary`, `SeriesEvaluationResult`, `ForecastResult`, `BackendComparisonResult`, `ExogenousBenchmarkResult`, `RobustnessStudyResult`, `SampleSizeStressResult` |
| Config models | `BenchmarkDataConfig`, `CMIConfig`, `ExogenousBenchmarkConfig`, `MetricConfig`, `ModelConfig`, `OutputConfig`, `RobustnessStudyConfig`, `RollingOriginConfig`, `SensitivityConfig`, `UncertaintyConfig` |
| Dataset helpers | `generate_ar1`, `generate_white_noise`, `ar1_theoretical_ami`, `generate_lagged_exog_panel`, `generate_known_future_calendar_pair`, `generate_contemporaneous_only_pair` |
| Registry and validation helpers | `DependenceScorer`, `ScorerInfo`, `ScorerRegistry`, `default_registry`, `validate_time_series` |

## Fingerprint Surface

Use `run_forecastability_fingerprint` when you want the compact forecastability
fingerprint, AMI information geometry, and deterministic routing in one bundle.

```python
from forecastability import generate_fingerprint_archetypes, run_forecastability_fingerprint

series = generate_fingerprint_archetypes(n=320, seed=42)["seasonal_periodic"]
bundle = run_forecastability_fingerprint(
    series,
    target_name="seasonal_periodic",
    max_lag=24,
    n_surrogates=99,
    random_state=42,
)
```

Key returned objects:

- `bundle.geometry`: corrected-profile geometry, `signal_to_noise`, geometry structure, geometry horizon
- `bundle.fingerprint`: compact fingerprint fields (`information_mass`, `information_horizon`, `information_structure`, `nonlinear_share`, `signal_to_noise`)
- `bundle.recommendation`: deterministic model-family guidance and caution flags

> [!NOTE]
> `bundle.recommendation.confidence_label` is widened additively in v0.3.3.
> The original `high`, `medium`, and `low` meanings remain unchanged, and the
> new `abstain` value is emitted only when the routing policy returns zero
> primary families.

## Routing Validation Surface (v0.3.3+)

Use `run_routing_validation` when you need a typed audit of deterministic
family routing across the synthetic validation panel and, optionally, the
real-series sanity panel.

```python
from forecastability import RoutingPolicyAuditConfig, run_routing_validation

bundle = run_routing_validation(
    n_per_archetype=200,
    real_panel_path=None,
    config=RoutingPolicyAuditConfig(),
)
```

Key returned objects:

- `bundle.cases[*]`: per-case expected families, observed families, outcome, calibrated confidence label, threshold margin, and rule-stability
- `bundle.audit`: aggregate `pass` / `downgrade` / `fail` / `abstain` counts
- `bundle.config`: frozen versioned scalars used for the audit and calibration run

Operational notes:

- `RoutingValidationBundle` is additive on the stable `forecastability` facade.
- `RoutingValidationCase.confidence_label` and routed recommendation confidence labels now admit the additive `abstain` value.
- The canonical clean-checkout report command is `uv run python scripts/run_routing_validation_report.py --smoke --no-real-panel`.
- The report script writes the canonical markdown report to `outputs/reports/routing_validation/report.md`; the saved JSON bundle and report manifest live under `outputs/json/routing_validation/`.
- The deterministic-first agent example is `examples/univariate/agents/routing_validation_agent_review.py`; it recomputes a fresh deterministic bundle, and the saved report artifacts are authoritative for exact smoke-report counts.
- The optional live path remains downstream of the deterministic bundle.

For the outcome semantics and calibration math, see
[docs/theory/routing_validation.md](theory/routing_validation.md).

## CSV Geometry Batch Surface

Use `run_ami_geometry_csv_batch` when you want the deterministic fingerprint
workflow over a one-series-per-column CSV file with adapter-owned summary and
artifact writing.

```python
from pathlib import Path

from forecastability import run_ami_geometry_csv_batch

result = run_ami_geometry_csv_batch(
    Path("outputs/examples/ami_geometry_csv/inputs/synthetic_fingerprint_panel.csv"),
    output_root=Path("outputs/examples/ami_geometry_csv"),
    max_lag=24,
    n_surrogates=99,
    random_state=42,
)
```

Key returned objects:

- `result.items[*].bundle`: full deterministic bundle when the series is analyzable
- `result.items[*].skip_reason`: stable reason when a series is skipped conservatively
- `result.summary_csv_path`, `result.figure_path`, `result.markdown_path`: emitted adapter artifacts

## Batch Forecastability Workbench

Use `run_batch_forecastability_workbench` when you want one deterministic batch
pass that combines:

- triage ranking
- geometry-backed fingerprint routing
- per-series next-step forecasting plans
- batch-level technical and executive reporting inputs

```python
from forecastability import (
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
```

Key returned objects:

- `result.items[*].triage_item`: ranked batch triage outcome
- `result.items[*].fingerprint_bundle`: geometry + fingerprint + routing when analyzable
- `result.items[*].next_step`: deterministic next-step forecasting plan
- `result.summary`: batch counts plus technical/executive summary strings

## Covariant Method Surface

Use `run_covariant_analysis` when you need a unified lag-by-driver table across pairwise, directional, and causal-discovery methods.

```python
from forecastability import generate_covariant_benchmark, run_covariant_analysis

df = generate_covariant_benchmark(n=1200, seed=42)
target = df["target"].to_numpy()
drivers = {name: df[name].to_numpy() for name in df.columns if name != "target"}

bundle = run_covariant_analysis(
  target,
  drivers,
  max_lag=5,
  methods=["cross_ami", "cross_pami", "te", "gcmi"],
  n_surrogates=99,
  random_state=42,
)
```

| Method token | What it computes | Conditioning scope tag |
| --- | --- | --- |
| `cross_ami` | Pairwise lagged CrossAMI curve | `none` |
| `cross_pami` | Target-history-conditioned lagged CrosspAMI curve | `target_only` |
| `te` | Transfer entropy curve (lagged directional dependence) | `target_only` |
| `gcmi` | Gaussian copula mutual information curve | `none` |
| `pcmci` | PCMCI+ parent graph (optional) | `full_mci` |
| `pcmci_ami` | PCMCI-AMI-Hybrid result (optional) | `full_mci` |

> [!IMPORTANT]
> `n_surrogates` must be at least 99 for covariant runs because the bundle includes phase-surrogate significance semantics for CrossAMI rows.

## Lagged-Exogenous Triage Surface (v0.3.2+)

Use `run_lagged_exogenous_triage` when you need to classify each exogenous
driver as contemporaneous (multivariate diagnostic) or predictively useful at
specific lags, and to obtain a sparse lag map for forecasting tensor construction.

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

# Inspect the sparse selected lags
for row in bundle.selected_lags:
    if row.selected_for_tensor:
        print(f"  {row.driver} @ lag={row.lag}  tensor_role={row.tensor_role}")
```

Known-future opt-in (e.g. calendar features whose $k=0$ value is available at prediction time):

```python
bundle = run_lagged_exogenous_triage(
    target,
    drivers,
    target_name="target",
    max_lag=6,
    n_surrogates=99,
    random_state=42,
    known_future_drivers={"holiday_flag": True},
)
```

CLI equivalent (smoke run):

```bash
MPLBACKEND=Agg uv run scripts/run_showcase_lagged_exogenous.py --smoke
```

| Type | Description |
| --- | --- |
| `LaggedExogBundle` | Composite typed output: profile rows, selection rows, driver list, known-future list |
| `LaggedExogProfileRow` | One lag-domain diagnostic row — correlation, cross_ami, cross_pami, lag_role, tensor_role, significance |
| `LaggedExogSelectionRow` | One sparse selection row — `selected_for_tensor`, `selector_name`, `tensor_role` |
| `LagRoleLabel` | `Literal["instant", "predictive"]` — chronological role at this lag |
| `TensorRoleLabel` | `Literal["diagnostic", "predictive", "known_future"]` — tensor-eligibility classification |
| `LagSelectorLabel` | `Literal["xcorr_top_k", "xami_sparse"]` — which selector produced the row |
| `LagSignificanceSource` | `Literal["phase_surrogate_xami", "phase_surrogate_xcorr", "not_computed"]` |

> [!IMPORTANT]
> `selected_for_tensor=True` is impossible at `lag=0` by default. Use `known_future_drivers`
> to opt in for features whose contemporaneous value is legitimately available at prediction time.
> [!NOTE]
> `lag_role="instant"` rows at `lag=0` are diagnostic. They document contemporaneous association
> but do not enter forecasting tensors without the `known_future_drivers` opt-in.

For method semantics, DTW omission rationale, and the sparse selector algorithm, see
[docs/theory/lagged_exogenous_triage.md](theory/lagged_exogenous_triage.md).

For the walkthrough notebook, open
[notebooks/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb](../../notebooks/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb).

> [!NOTE]
> Optional causal methods (`pcmci`, `pcmci_ami`) are skipped when causal dependencies are unavailable; the bundle records skipped methods in `metadata`.

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

## Forecast Prep Contract (v0.3.4+)

After triage, use `build_forecast_prep_contract` to convert triage outputs into a typed,
machine-readable hand-off contract for downstream model families.

```python
from forecastability import ForecastPrepContract
from forecastability import LagRecommendation
from forecastability import CovariateRecommendation
from forecastability import FamilyRecommendation
from forecastability import build_forecast_prep_contract
from forecastability import forecast_prep_contract_to_markdown
from forecastability import forecast_prep_contract_to_lag_table
from forecastability.triage import ForecastPrepBundle
```

| Symbol | Description |
| --- | --- |
| `ForecastPrepContract` | Top-level typed result container for a completed forecast prep triage hand-off. Stable Pydantic model; use `.model_dump()` / `.model_dump_json()` as the canonical Python-dict and JSON export surfaces. |
| `LagRecommendation` | Typed lag recommendation row: driver name, lag offset, tensor role, and significance source. |
| `CovariateRecommendation` | Typed covariate recommendation: driver name, recommended role, and supporting evidence. |
| `FamilyRecommendation` | Typed model-family recommendation: family name, confidence label, and caution flags. |
| `build_forecast_prep_contract` | Use case that accepts a `TriageResult` plus horizon, frequency, and calendar options and returns a `ForecastPrepContract`. Re-exported from `forecastability` and `forecastability.triage`. |
| `forecast_prep_contract_to_markdown` | Framework-agnostic Markdown exporter for a `ForecastPrepContract`. Re-exported from `forecastability` and `forecastability.triage`. |
| `forecast_prep_contract_to_lag_table` | Framework-agnostic lag-table exporter for a `ForecastPrepContract`. Re-exported from `forecastability` and `forecastability.triage`. |
| `ForecastPrepBundle` | Composite bundle wrapping a `TriageResult` and the derived `ForecastPrepContract`. Available from `forecastability.triage`. |

> [!IMPORTANT]
> The contract is a **hand-off boundary**. It never imports any downstream library.
> Framework-specific wiring belongs in `docs/recipes/**` and (from v0.4.0) in the sibling
> `forecastability-examples` repository.

## Runtime Entry Points

These are the live repo entry points for non-import surfaces.

| Surface | Entry point | Notes |
| --- | --- | --- |
| CLI | `forecastability` | Packaged command wired to `forecastability.adapters.cli:main` |
| Dashboard | `forecastability-dashboard` | Packaged command wired to `forecastability.adapters.dashboard:main` |
| HTTP API | `forecastability.adapters.api:app` | FastAPI application used with Uvicorn |
| CSV script | `scripts/run_ami_information_geometry_csv.py` | Repo script for one-series-per-column CSV batch geometry runs |
| Fingerprint showcase script | `scripts/run_showcase_fingerprint.py` | Canonical v0.3.1 prepared-archetype showcase with strict A1/A2/A3 verification |
| Routing validation report script | `scripts/run_routing_validation_report.py` | Canonical v0.3.3 report surface; use `--smoke --no-real-panel` for the clean-checkout path |

## Causal Discovery (v0.3.0+)

Causal structure recovery for multivariate time series requires the optional `tigramite`
dependency:

```bash
pip install "dependence-forecastability[causal]"
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
| `CausalGraphFullPort` | `@runtime_checkable` Protocol extending the causal-discovery boundary with `discover_full(...) -> PcmciAmiResult` for the PCMCI-AMI hybrid path while still supporting `discover(...)`. |
| `CausalGraphResult` | Pydantic result model holding `parents`, `link_matrix`, `val_matrix`, and `metadata` from a completed PCMCI+ run. |
| `generate_covariant_benchmark` | Generates an 8-variable ground-truth system with known linear, mediated, redundant, contemporaneous, and nonlinear structural links. Primary fixture for adapter and covariant-model tests. |
| `generate_directional_pair` | Generates a simple $X \to Y$ directional pair for TE and GCMI validation. |

> [!WARNING]
> `CausalGraphPort` and `CausalGraphFullPort` live under `ports/` and `TigramiteAdapter` under `adapters/` —
> namespaces otherwise marked internal. These causal discovery symbols are the
> explicit exception: they are part of the Phase 1 covariant surface and intended
> for direct import. `generate_covariant_benchmark` and `generate_directional_pair`
> are now also part of the stable facade surface via top-level `forecastability`
> re-exports (with `forecastability.utils.synthetic` remaining valid).

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
