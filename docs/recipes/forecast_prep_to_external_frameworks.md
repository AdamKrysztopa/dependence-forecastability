<!-- type: how-to -->
# Wiring the Forecast Prep Contract into External Frameworks

> [!IMPORTANT]
> **Illustrative recipes — not part of the supported package API.**
> The code snippets on this page show how a user *could* translate a
> `ForecastPrepContract` into framework-specific configuration in their own
> code. They are illustrative only and are **never executed by core CI**.
> The core `forecastability` package is framework-agnostic and does not import
> `darts`, `mlforecast`, `statsforecast`, or `nixtla` in any tier (runtime,
> optional extras, dev, CI). See the repository scope directive at
> [docs/plan/aux_documents/developer_instruction_repo_scope.md](../plan/aux_documents/developer_instruction_repo_scope.md).

---

## Prerequisites

Run triage and build a contract before using the snippets below:

```python
from forecastability import run_triage, TriageRequest, build_forecast_prep_contract

request = TriageRequest(series=my_series)
triage_result = run_triage(request)
bundle = build_forecast_prep_contract(
    triage_result,
    horizon=12,
    target_frequency="MS",
    add_calendar_features=True,
)
contract = bundle.contract
```

All fields referenced in the snippets (`contract.recommended_target_lags`,
`contract.past_covariates`, etc.) are documented in
[docs/forecast_prep_contract.md](../forecast_prep_contract.md).

---

## Map a contract to MLForecast

> [!NOTE]
> Illustrative recipe. `mlforecast` is not a dependency of this package.
> Install it separately (`pip install mlforecast`) before running this snippet.

```python
# ILLUSTRATIVE RECIPE — not part of the forecastability package API
import mlforecast
from mlforecast import MLForecast
from mlforecast.target_transforms import Differences
from window_ops.rolling import rolling_mean
import lightgbm as lgb

# --- Axis A: target lags ---
# recommended_target_lags contains direct and secondary lags (all >= 1)
target_lags = contract.recommended_target_lags + contract.recommended_seasonal_lags

# --- Axis B: past covariates ---
# past_covariates are driver columns selected with selected_for_tensor=True, lag >= 1.
# The richer ForecastPrepBundle.covariate_rows carries per-driver selected_lags.
# Here we use lag=1 as a conservative default for each past covariate.
lag_transforms: dict[str, list] = {}
for driver in contract.past_covariates:
    # For fine-grained control, read selected_lags from the bundle's covariate_rows:
    #   row = next(r for r in bundle.covariate_rows if r.name == driver)
    #   lags = row.selected_lags  # sparse predictive lags >= 1
    lag_transforms[driver] = [(rolling_mean, 1)]

# --- Axis C: future covariates (including calendar columns) ---
# future_covariates lists all columns known for the entire forecast horizon.
# calendar_features is the subset auto-generated with the _calendar__ prefix.
# MLForecast accepts future exogenous columns as part of the X_df passed at
# predict time; make sure all future_covariates are present in that DataFrame.
future_exog_cols = contract.future_covariates  # includes calendar columns if any

# --- Transformation hints ---
# transformation_hints carries free-text recommendations; apply them manually.
# Example: "difference_once" → wrap with Differences([1])
target_transforms = [Differences([1])] if "difference_once" in contract.transformation_hints else []

model = MLForecast(
    models=[lgb.LGBMRegressor()],
    freq=contract.target_frequency or "MS",
    lags=target_lags or [1],
    lag_transforms=lag_transforms or {},
    target_transforms=target_transforms or [],
)

# Fit: pass past_covariates and future_covariates columns in X_df
# model.fit(df, id_col="unique_id", time_col="ds", target_col="y", ...)
```

---

## Map a contract to Darts

> [!NOTE]
> Illustrative recipe. `darts` is not a dependency of this package.
> Install it separately (`pip install darts`) before running this snippet.

```python
# ILLUSTRATIVE RECIPE — not part of the forecastability package API
from darts.models import LightGBMModel

# --- Axis A: target lags ---
# recommended_target_lags and recommended_seasonal_lags are all >= 1.
# Darts expects a list of strictly positive integers for the `lags` parameter.
target_lags = sorted(
    set(contract.recommended_target_lags) | set(contract.recommended_seasonal_lags)
) or [1]

# --- Axis B: past covariates ---
# Use selected_for_tensor=True rows only (those in contract.past_covariates).
# The per-driver sparse lag sets live in bundle.covariate_rows.selected_lags.
# Darts `lags_past_covariates` accepts a single int (applied to all past columns)
# or a dict mapping column name -> list[int].
lags_past_covariates: dict[str, list[int]] = {}
for row in bundle.covariate_rows:
    if row.role == "past" and row.selected_lags:
        # selected_lags already enforces lag >= 1 for past rows
        lags_past_covariates[row.name] = sorted(row.selected_lags)

# --- Axis C: future covariates ---
# lag = 0 is ONLY allowed for columns in known_future_drivers or calendar features.
# Darts `lags_future_covariates` is typically [0] for known-future columns.
# Do NOT include any column that is not in contract.future_covariates here.
lags_future_covariates = {col: [0] for col in contract.future_covariates}

# Separate calendar columns from user-declared known-future columns if needed.
calendar_cols = contract.calendar_features  # start with _calendar__
user_future_cols = [c for c in contract.future_covariates if c not in calendar_cols]

model = LightGBMModel(
    lags=target_lags,
    lags_past_covariates=lags_past_covariates or None,
    lags_future_covariates=lags_future_covariates or None,
    output_chunk_length=contract.horizon or 1,
)

# At fit/predict time:
#   past_covariates_series  → TimeSeries from contract.past_covariates columns
#   future_covariates_series → TimeSeries from contract.future_covariates columns
#                              (must extend at least `horizon` steps beyond the training end)
# model.fit(
#     target_series,
#     past_covariates=past_cov_series,
#     future_covariates=future_cov_series,
# )
```

---

## Map a contract to Nixtla / StatsForecast

> [!NOTE]
> Illustrative recipe. `statsforecast` and `nixtla` are not dependencies of
> this package. Install separately (`pip install statsforecast`) before running.

```python
# ILLUSTRATIVE RECIPE — not part of the forecastability package API
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, SeasonalNaive

# --- Model frequency ---
# contract.target_frequency follows pandas offset alias conventions (e.g., "MS", "D").
freq = contract.target_frequency or "MS"

# --- Model family selection ---
# recommended_families carries evidence-based suggestions; baseline_families
# are always included for benchmarking.
# Map family strings to StatsForecast model objects manually.
_family_map = {
    "arima": AutoARIMA(season_length=12),
    "seasonal_naive": SeasonalNaive(season_length=12),
    "naive": SeasonalNaive(season_length=1),
}
models = [
    _family_map[f]
    for f in (contract.recommended_families + contract.baseline_families)
    if f in _family_map
] or [SeasonalNaive(season_length=12)]

sf = StatsForecast(models=models, freq=freq)

# --- Exogenous columns ---
# StatsForecast passes exogenous columns as X_df at fit time and X_future_df
# at predict time.
#
# past_covariates → X_df (observed covariates aligned with training index)
# future_covariates → X_future_df (covariates known for the forecast horizon,
#                     including calendar columns from contract.calendar_features)
#
# Calendar columns (_calendar__*) are already deterministically named and can
# be generated for the forecast horizon by rerunning the calendar feature
# service on the horizon DatetimeIndex.

# sf.fit(
#     df,           # long format with "unique_id", "ds", "y" columns
#     X_df=past_X,  # past exogenous; columns must match contract.past_covariates
# )
# sf.predict(
#     h=contract.horizon or 12,
#     X_df=future_X,  # future exogenous; columns must match contract.future_covariates
# )
```

---

## Why these are recipes, not adapters

- **The core package is framework-agnostic** per the repository scope directive
  ([docs/plan/aux_documents/developer_instruction_repo_scope.md](../plan/aux_documents/developer_instruction_repo_scope.md)).
  This is a binding architectural constraint, not a preference.
- **Framework-specific adapters would introduce prohibited dependencies.**
  Adding `darts`, `mlforecast`, `statsforecast`, or `nixtla` as runtime,
  optional-extra, dev, or CI dependencies of the core repository is forbidden.
  The `ForecastPrepContract` hand-off boundary stops at a framework-neutral
  Pydantic model.
- **The contract hand-off boundary is deliberate.** `ForecastPrepContract`
  provides evidence-backed structured outputs (`recommended_target_lags`,
  `past_covariates`, `future_covariates`, `confidence_label`, `caution_flags`)
  so users can make informed translation decisions rather than blind
  model-fitting calls.
- **Executable end-to-end demos ship in the sibling `forecastability-examples`
  repository from v0.4.0.** The notebook and runner that were originally
  planned for this release were descoped; see the
  [v0.4.0 examples-repository split plan](../plan/v0_4_0_examples_repo_split_ultimate_plan.md).
- **These snippets are documentation, not tested code.** They are never
  executed by core CI and are not part of the package test suite. They are
  provided to illustrate the translation pattern, not to guarantee that any
  particular framework version is compatible.
