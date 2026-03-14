# 19. Series-Level Rolling-Origin Evaluation Pipeline

- [x] For each series and each horizon:
  - [ ] compute training-only `AMI(h)`
  - [ ] compute training-only `pAMI(h)`
  - [ ] fit models on training only
  - [ ] score `sMAPE` on test only
  - [ ] aggregate across origins

```python
from __future__ import annotations

import numpy as np

from forecastability.metrics import compute_ami, compute_pami_linear_residual
from forecastability.models import forecast_ets, forecast_naive, forecast_seasonal_naive, smape
from forecastability.rolling_origin import build_expanding_window_splits
from forecastability.types import ForecastResult, SeriesEvaluationResult


def run_rolling_origin_evaluation(
    ts: np.ndarray,
    *,
    series_id: str,
    frequency: str,
    horizons: list[int],
    n_origins: int,
    seasonal_period: int | None,
    random_state: int,
) -> SeriesEvaluationResult:
    """Run rolling-origin evaluation for one series."""
    ami_by_horizon: dict[int, float] = {}
    pami_by_horizon: dict[int, float] = {}
    naive_smape: dict[int, float] = {}
    snaive_smape: dict[int, float] = {}
    ets_smape: dict[int, float] = {}

    for horizon in horizons:
        splits = build_expanding_window_splits(
            ts,
            n_origins=n_origins,
            horizon=horizon,
        )

        ami_vals: list[float] = []
        pami_vals: list[float] = []
        naive_vals: list[float] = []
        snaive_vals: list[float] = []
        ets_vals: list[float] = []

        for split in splits:
            train = split.train
            test = split.test

            ami_curve = compute_ami(
                train,
                max_lag=horizon,
                random_state=random_state,
            )
            pami_curve = compute_pami_linear_residual(
                train,
                max_lag=horizon,
                random_state=random_state,
            )

            ami_vals.append(float(ami_curve[horizon - 1]))
            pami_vals.append(float(pami_curve[horizon - 1]))

            pred_naive = forecast_naive(train, horizon)
            pred_snaive = forecast_seasonal_naive(
                train,
                horizon,
                seasonal_period=seasonal_period or 1,
            )
            pred_ets = forecast_ets(
                train,
                horizon,
                seasonal_period=seasonal_period,
            )

            naive_vals.append(smape(test, pred_naive))
            snaive_vals.append(smape(test, pred_snaive))
            ets_vals.append(smape(test, pred_ets))

        ami_by_horizon[horizon] = float(np.mean(ami_vals))
        pami_by_horizon[horizon] = float(np.mean(pami_vals))
        naive_smape[horizon] = float(np.mean(naive_vals))
        snaive_smape[horizon] = float(np.mean(snaive_vals))
        ets_smape[horizon] = float(np.mean(ets_vals))

    return SeriesEvaluationResult(
        series_id=series_id,
        frequency=frequency,
        ami_by_horizon=ami_by_horizon,
        pami_by_horizon=pami_by_horizon,
        forecast_results=[
            ForecastResult(
                model_name="naive",
                horizons=horizons,
                smape_by_horizon=naive_smape,
            ),
            ForecastResult(
                model_name="seasonal_naive",
                horizons=horizons,
                smape_by_horizon=snaive_smape,
            ),
            ForecastResult(
                model_name="ets",
                horizons=horizons,
                smape_by_horizon=ets_smape,
            ),
        ],
        metadata={},
    )
```
