# 18. Baseline Forecasting Models

- [x] Implement minimum baseline models:
  - [ ] naive
  - [ ] seasonal naive
  - [ ] ETS
- [x] Optional integrations:
  - [ ] N-BEATS
  - [ ] LightGBM autoregression

```python
from __future__ import annotations

import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute sMAPE."""
    denom = np.abs(y_true) + np.abs(y_pred)
    denom = np.where(denom == 0.0, 1e-12, denom)
    return float(np.mean(200.0 * np.abs(y_true - y_pred) / denom))


def forecast_naive(train: np.ndarray, horizon: int) -> np.ndarray:
    """Naive forecast."""
    return np.repeat(train[-1], horizon)


def forecast_seasonal_naive(
    train: np.ndarray,
    horizon: int,
    *,
    seasonal_period: int,
) -> np.ndarray:
    """Seasonal naive forecast."""
    if seasonal_period <= 0 or train.size < seasonal_period:
        return forecast_naive(train, horizon)

    base = train[-seasonal_period:]
    reps = int(np.ceil(horizon / seasonal_period))
    return np.tile(base, reps)[:horizon]


def forecast_ets(
    train: np.ndarray,
    horizon: int,
    *,
    seasonal_period: int | None = None,
) -> np.ndarray:
    """ETS forecast with simple fallback."""
    if seasonal_period is not None and seasonal_period >= 2 and train.size >= 2 * seasonal_period:
        model = ExponentialSmoothing(
            train,
            trend="add",
            seasonal="add",
            seasonal_periods=seasonal_period,
        )
    else:
        model = ExponentialSmoothing(
            train,
            trend="add",
            seasonal=None,
        )

    fit = model.fit(optimized=True)
    return np.asarray(fit.forecast(horizon), dtype=float)
```
