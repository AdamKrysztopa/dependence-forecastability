# Library Reference (`src/forecastability`)

This is the code-level map of modules in `src/forecastability`, using exact module naming.

## `__init__.py`
- Package exports for core configs, types, and class API.

## `analyzer.py`
- `ForecastabilityAnalyzer`: method-independent analyzer with scorer registry. Backward-compatible AMI/pAMI methods plus generic `compute_raw()`, `compute_partial()`, and `compute_significance_generic()`. Exposes `list_scorers()` and `register_scorer()` for runtime introspection and custom scorer registration.
- `ForecastabilityAnalyzerExog`: extension of `ForecastabilityAnalyzer` that adds optional exogenous-series support. With `exog=None`, behavior matches ACF-style auto-dependence; with `exog=...`, raw/partial curves become CCF-style cross-dependence (`exog_t -> target_{t+h}`).
- `AnalyzeResult`: structured return object with fields `raw`, `partial`, `sig_raw_lags`, `sig_partial_lags`, `recommendation`, and `method`.

## `scorers.py`
- `DependenceScorer`: Protocol for dependence scoring functions (`past`, `future` → non-negative scalar).
- `ScorerInfo`: Metadata dataclass for registered scorers (`name`, `scorer`, `family`, `description`).
- `ScorerRegistry`: Named registry with `register()`, `get()`, `list_scorers()`, and `register_scorer()` decorator.
- `default_registry()`: Factory returning a pre-populated registry with five built-in scorers.
- Built-in scorers: `mi` (kNN MI), `pearson` (abs. Pearson), `spearman` (abs. Spearman), `kendall` (abs. Kendall τ-b), `distance` (Székely/Rizzo energy-distance correlation).

## `config.py`
- `MetricConfig`: AMI/pAMI metric settings (`k`, surrogates, lags, seeds).
- `RollingOriginConfig`: rolling-origin defaults (`n_origins=10`, horizons).
- `OutputConfig`: output directory creation and management.
- `CMIConfig`: backend selection for conditional-MI approximation.
- `BenchmarkDataConfig`: benchmark source/frequency/cache configuration.
- `ModelConfig`: baseline/optional model toggles.
- `UncertaintyConfig`: bootstrap uncertainty settings.
- `SensitivityConfig`: `k`-grid sensitivity settings.

## `types.py`
- `MetricCurve`
- `CanonicalExampleResult`
- `ForecastResult`
- `SeriesEvaluationResult`
- `InterpretationResult`

## `validation.py`
- `validate_time_series`: validates length, finite values, non-constant behavior.

## `datasets.py`
- Canonical generators/loaders:
  - `generate_sine_wave`
  - `load_air_passengers`
  - `generate_henon_map`
  - `generate_simulated_stock_returns`
- Extension dataset utilities:
  - `m4_seasonal_period`
  - `load_m4_subset`

## `metrics.py`
- `compute_ami`: horizon-specific AMI curve.
- `compute_pami_linear_residual`: baseline pAMI estimator (linear residualization + MI).

## `cmi.py`
- Residualization backends:
  - `LinearResidualBackend`
  - `RandomForestResidualBackend`
- `compute_pami_with_backend`: pluggable pAMI computation (`linear_residual`, `rf_residual`).

## `surrogates.py`
- `phase_surrogates`: phase-randomized surrogate generation.
- `compute_significance_bands`: surrogate significance intervals.

## `rolling_origin.py`
- `RollingSplit`
- `build_expanding_window_splits`: expanding-window rolling-origin splits.

## `models.py`
- Error metric:
  - `smape`
- Baselines:
  - `forecast_naive`
  - `forecast_seasonal_naive`
  - `forecast_ets`
- Optional integrations with fallback:
  - `forecast_lightgbm_autoreg`
  - `forecast_nbeats`
- Lightweight fallback/auxiliary:
  - `forecast_linear_autoreg`

## `pipeline.py`
- `run_canonical_example`: AMI/pAMI + significance for a canonical series.
- `run_rolling_origin_evaluation`: train-only diagnostics and holdout-only scoring.

## `aggregation.py`
- `summarize_canonical_result`
- `build_horizon_table`
- `compute_rank_associations`
- `add_terciles`
- `summarize_terciles`
- `summarize_frequency_panels`

## `interpretation.py`
- `interpret_canonical_result`: deterministic Pattern A-E interpretation logic.

## `plots.py`
- Canonical plots:
  - `plot_ami_with_band`
  - `plot_pami_with_band`
  - `plot_ami_pami_overlay`
  - `plot_ami_minus_pami`
  - `plot_canonical_result`
  - `save_all_canonical_plots`
- Benchmark/extension plots:
  - `plot_rank_association_bars`
  - `plot_frequency_panel`

## `extensions.py`
- `compute_k_sensitivity`
- `bootstrap_descriptor_uncertainty`

## `reporting.py`
- Canonical outputs:
  - `save_canonical_result_json`
  - `build_canonical_markdown`
  - `save_canonical_markdown`
- Benchmark/report outputs:
  - `build_benchmark_markdown`
  - `build_frequency_panel_markdown`
  - `build_linkedin_post`
  - `mandatory_caveats`
