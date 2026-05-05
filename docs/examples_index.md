<!-- type: reference -->

# Examples Index

All runnable notebooks for the `forecastability` toolkit live in the sibling
[`forecastability-examples`](https://github.com/AdamKrysztopa/forecastability-examples)
repository. The tables below catalogue every notebook by section, with a direct
link to the source file on GitHub.

> [!NOTE]
> Notebooks that require external data (M4 monthly, CausalRivers) gate on a
> cached fetch step. Run `python scripts/download_data.py` (M4) or
> `python scripts/download_causal_rivers.py` (CausalRivers) in the sibling
> repo before executing those notebooks locally.

## Core-Repo Lag-Aware Showcase Scripts

The core repo keeps the canonical Lag-Aware ModMRMR smoke paths as scripts.
Richer walkthrough notebooks for this surface belong in the sibling
`forecastability-examples` repository and are intentionally not listed here
until those files exist.

| Script | Description |
| --- | --- |
| [../scripts/run_showcase_lag_aware_mod_mrmr.py](../scripts/run_showcase_lag_aware_mod_mrmr.py) | Fast-scorer Lag-Aware ModMRMR showcase; writes deterministic JSON, tables, figures, and markdown, and supports `--smoke`. |
| [../scripts/run_showcase_lag_aware_catt_mod_mrmr.py](../scripts/run_showcase_lag_aware_catt_mod_mrmr.py) | Catt-style KSG Lag-Aware ModMRMR showcase; same artifact contract with the native nonlinear scorer path and `--smoke`. |

## Walkthroughs

End-to-end capability demonstrations covering every major triage method.

| Notebook | Description | Source |
|---|---|---|
| `00_air_passengers_showcase.ipynb` | All forecastability methods demonstrated on the Air Passengers series | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/00_air_passengers_showcase.ipynb) |
| `01_canonical_forecastability.ipynb` | AMI vs pAMI forecastability triage on canonical synthetic cases; full report output | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/01_canonical_forecastability.ipynb) |
| `01_covariant_informative_showcase.ipynb` | Covariate informativeness triage — when does an exogenous driver improve forecastability? | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/01_covariant_informative_showcase.ipynb) |
| `02_exogenous_analysis.ipynb` | CrossAMI and pCrossAMI exogenous screening on bike-sharing, AAPL/SPY, and BTC/ETH series | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/02_exogenous_analysis.ipynb) |
| `02_forecastability_fingerprint_showcase.ipynb` | Forecastability fingerprint — compact four-field profile and routing recommendation | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/02_forecastability_fingerprint_showcase.ipynb) |
| `03_lagged_exogenous_triage_showcase.ipynb` | Lagged-exogenous triage — driver lag roles, sparse selection, and tensor-ready lag maps | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb) |
| `03_triage_end_to_end.ipynb` | End-to-end agentic triage walkthrough; the consumer surface for automated triage pipelines | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/03_triage_end_to_end.ipynb) |
| `04_routing_validation_showcase.ipynb` | Routing validation — auditing deterministic routing against synthetic archetypes | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/04_routing_validation_showcase.ipynb) |
| `04_screening_end_to_end.ipynb` | Agentic feature screening — which exogenous drivers matter for forecastability? | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/04_screening_end_to_end.ipynb) |
| `05_forecast_prep_to_models.ipynb` | Triage → `ForecastPrepContract` → hand-off to Darts, MLForecast, and sklearn Ridge; demonstrates the v0.3.4 sprint | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/05_forecast_prep_to_models.ipynb) |
| `06_triage_driven_vs_naive_on_m4.ipynb` | Triage-driven model-family selection vs SeasonalNaive on M4 monthly subset (≤ 200 series) | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/06_triage_driven_vs_naive_on_m4.ipynb) |
| `07_causal_rivers_lag_and_feature_selection.ipynb` | Capability demo on the CausalRivers benchmark — self-lag and exogenous lag selection recovering graph-verified positives and rejecting negative controls | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/07_causal_rivers_lag_and_feature_selection.ipynb) |

## Triage Walkthroughs

Focused diagnostic notebooks corresponding to the triage-method framework figures (F1–F8, N3–N4).

| Notebook | Description | Source |
|---|---|---|
| `01_forecastability_profile_walkthrough.ipynb` | Forecastability profile — F1 deep dive into horizon-by-horizon AMI structure | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/triage_walkthroughs/01_forecastability_profile_walkthrough.ipynb) |
| `02_information_limits_and_compression.ipynb` | Information-theoretic limits and compression — F2, horizon-specific upper bounds | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/triage_walkthroughs/02_information_limits_and_compression.ipynb) |
| `03_predictive_information_learning_curves.ipynb` | Predictive information learning curves — N3, sample-size effects | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/triage_walkthroughs/03_predictive_information_learning_curves.ipynb) |
| `04_spectral_and_entropy_diagnostics.ipynb` | Spectral and entropy diagnostics — N4, seasonality structure and permutation entropy | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/triage_walkthroughs/04_spectral_and_entropy_diagnostics.ipynb) |
| `05_batch_and_exogenous_workbench.ipynb` | Batch ranking and exogenous screening workbench — F7/F8, multi-series and driver comparison | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/triage_walkthroughs/05_batch_and_exogenous_workbench.ipynb) |
| `06_agent_ready_triage_interpretation.ipynb` | Agent-ready triage interpretation — deterministic deep dive and agent-payload construction | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/triage_walkthroughs/06_agent_ready_triage_interpretation.ipynb) |

## Recipes

Minimal reproducible examples demonstrating specific API contracts and integration patterns.

| Notebook | Description | Source |
|---|---|---|
| `contract_roundtrip.ipynb` | `ForecastPrepContract` round-trip — `model_dump_json()` → disk → `model_validate_json()` without re-importing `forecastability` | [source](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/recipes/contract_roundtrip.ipynb) |

## Where to file issues

| Issue type | Tracker |
|---|---|
| Notebook execution failures, walkthrough content, integration examples | [`forecastability-examples` issues](https://github.com/AdamKrysztopa/forecastability-examples/issues) |
| Core library API, triage logic, public symbols | [core repo issues](https://github.com/AdamKrysztopa/dependence-forecastability/issues) |

For framework-agnostic recipe text, see [docs/recipes/forecast_prep_to_external_frameworks.md](recipes/forecast_prep_to_external_frameworks.md).
