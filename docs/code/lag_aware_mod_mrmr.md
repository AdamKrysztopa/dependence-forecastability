<!-- type: reference -->
# Lag-Aware ModMRMR Code Map

Developer reference for the shipped Lag-Aware ModMRMR surface.

The public entry point is `run_lag_aware_mod_mrmr()`, re-exported from both the
stable `forecastability` facade and `forecastability.triage`. The implementation
stays inside the core deterministic forecastability-triage boundary and stops at
the `ForecastPrepContract` hand-off.

## Surface Map

| Surface | File target | Acceptance-oriented note |
| --- | --- | --- |
| Public facades | `src/forecastability/__init__.py`, `src/forecastability/triage/__init__.py` | Re-export the live `run_lag_aware_mod_mrmr()` entry point together with the frozen result models. |
| Domain contracts | `src/forecastability/triage/lag_aware_mod_mrmr.py` | Frozen Pydantic models define config, legal candidates, blocked candidates, selected rows, rejected rows, scorer diagnostics, and the final result payload. |
| Lag-domain builder | `src/forecastability/services/lag_aware_mod_mrmr_domain.py` | Enforces `lag >= forecast_horizon + availability_margin` for measured covariates before scoring and labels known-future bypass rows explicitly. |
| Scorer service | `src/forecastability/services/lag_aware_mod_mrmr_scorers.py` | Owns the pairwise scorer protocol, normalizers, and shipped backends including `mutual_info_sklearn`, `spearman_abs`, `gcmi`, and the Catt-style `catt_knn_mi` KSG scorer. |
| Selector service | `src/forecastability/services/lag_aware_mod_mrmr_selector.py` | Implements deterministic greedy ModMRMR with multiplicative maximum-similarity suppression against the already-selected set only. |
| Use case | `src/forecastability/use_cases/lag_aware_mod_mrmr.py` | Orchestrates domain building, greedy selection, and typed result assembly; returns `LagAwareModMRMRResult`. |
| Forecast-prep lagged covariate service | `src/forecastability/services/forecast_prep_lagged_covariates.py` | Maps selected lag-aware rows into `ForecastPrepContract.covariate_rows`, exploded lag tables, and markdown tables without inventing fallback lag-one rows when real sparse lags exist. |
| Forecast-prep use case glue | `src/forecastability/use_cases/build_forecast_prep_contract.py` | Copies lag-aware covariate rows into the contract, keeps `past_covariates` and `future_covariates` consistent with those rows, and preserves target-history context when present. |
| Showcase scripts | `scripts/run_showcase_lag_aware_mod_mrmr.py`, `scripts/run_showcase_lag_aware_catt_mod_mrmr.py` | Canonical end-to-end smoke paths that write deterministic JSON, tables, figures, and markdown under `outputs/`. |
| Regression tests | `tests/test_lag_aware_mod_mrmr.py`, `tests/test_lag_aware_mod_mrmr_regression.py`, `tests/test_forecast_prep_lagged_covariates.py` | Guard legality boundaries, formula semantics, deterministic tie-breaking, fixture drift, and forecast-prep row preservation. |
| Frozen fixtures | `docs/fixtures/lag_aware_mod_mrmr/expected/*.json` | Preserve expected outputs for forecast-horizon legality, known-future bypass, duplicate suppression, target-history novelty, and redundancy-behavior checks. |
| Fixture rebuild script | `scripts/rebuild_lag_aware_mod_mrmr_regression_fixtures.py` | Rebuilds fixture outputs and can verify them against the frozen expected artifacts. |

## Acceptance-Oriented Notes

- No illegal measured lag should reach the scorer. If a lag is below the cutoff
  for an ordinary covariate, the row belongs in `blocked`, not `selected` or
  `rejected`.
- Known-future bypass must stay explicit. When `is_known_future=True`, the row
  should also preserve `known_future_provenance` and should remain a future-axis
  covariate in forecast-prep exports.
- Maximum-similarity suppression is against the already-selected set only. A
  candidate is not penalized against the untouched candidate pool.
- The selector backend is swappable, but the legality rules and greedy logic are
  not. `catt_knn_mi` changes scoring fidelity, not selection semantics.
- Forecast-prep export must keep the real sparse lag choices. The contract path
  should expose actual `selected_lags` and `lagged_feature_names` rather than a
  generic one-lag-per-driver fallback.

## Smoke Path

Use the showcase scripts for end-to-end smoke checks and the rebuild script for
fixture drift checks.

```bash
MPLBACKEND=Agg uv run scripts/run_showcase_lag_aware_mod_mrmr.py --smoke --quiet
MPLBACKEND=Agg uv run scripts/run_showcase_lag_aware_catt_mod_mrmr.py --smoke --quiet
uv run python scripts/rebuild_lag_aware_mod_mrmr_regression_fixtures.py --verify
```

The first showcase uses the faster baseline scorer mix. The second runs the
Catt-style KSG scorer path. Both stay within the core repo and are the intended
script-first narration surfaces for this feature.

## Boundary Conditions

This surface intentionally does not add framework adapters, notebook-owned core
logic, or `to_<framework>_spec()` helpers. The supported hand-off boundary is
the typed `ForecastPrepContract`; framework-specific translation belongs in the
recipe layer, not in the package API.