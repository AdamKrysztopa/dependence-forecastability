"""Baseline forecasting models and scoring."""

from __future__ import annotations

import importlib
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

import numpy as np
from numpy.linalg import LinAlgError
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute symmetric mean absolute percentage error."""
    true = np.asarray(y_true, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    denom = np.abs(true) + np.abs(pred)
    denom = np.where(denom == 0.0, 1e-12, denom)
    return float(np.mean(200.0 * np.abs(true - pred) / denom))


def forecast_naive(train: np.ndarray, horizon: int) -> np.ndarray:
    """Forecast by repeating the final observed value."""
    return np.repeat(np.asarray(train, dtype=float)[-1], horizon)


def forecast_seasonal_naive(
    train: np.ndarray,
    horizon: int,
    *,
    seasonal_period: int,
) -> np.ndarray:
    """Seasonal naive forecast with fallback to naive."""
    arr = np.asarray(train, dtype=float)
    if seasonal_period <= 1 or arr.size < seasonal_period:
        return forecast_naive(arr, horizon)

    base = arr[-seasonal_period:]
    reps = int(np.ceil(horizon / seasonal_period))
    return np.tile(base, reps)[:horizon]


def forecast_ets(
    train: np.ndarray,
    horizon: int,
    *,
    seasonal_period: int | None = None,
    _timeout: int = 30,
) -> np.ndarray:
    """Fit ETS and forecast with robust fallback behavior.

    Args:
        _timeout: Seconds to wait for the scipy optimizer before falling back
            to naive.  Hard-kills via ThreadPoolExecutor so ETS hangs on
            ill-conditioned series do not block the pipeline.
    """
    arr = np.asarray(train, dtype=float)

    def _fit_and_forecast() -> np.ndarray:
        try:
            if (
                seasonal_period is not None
                and seasonal_period >= 2
                and arr.size >= 2 * seasonal_period
            ):
                model = ExponentialSmoothing(
                    arr,
                    trend="add",
                    seasonal="add",
                    seasonal_periods=seasonal_period,
                )
            else:
                model = ExponentialSmoothing(
                    arr,
                    trend="add",
                    seasonal=None,
                )
            fit = model.fit(optimized=True)
            return np.asarray(fit.forecast(horizon), dtype=float)
        except (ValueError, LinAlgError, FloatingPointError, RuntimeError):
            return forecast_naive(arr, horizon)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fit_and_forecast)
            return future.result(timeout=_timeout)
    except FuturesTimeoutError:
        return forecast_naive(arr, horizon)


def forecast_lightgbm_autoreg(
    train: np.ndarray,
    horizon: int,
    *,
    n_lags: int = 24,
) -> np.ndarray:
    """Optional LightGBM autoregression with graceful fallback."""
    arr = np.asarray(train, dtype=float)
    if importlib.util.find_spec("lightgbm") is None:
        return forecast_naive(arr, horizon)
    if arr.size <= n_lags + 1:
        return forecast_naive(arr, horizon)

    lightgbm = importlib.import_module("lightgbm")
    model = lightgbm.LGBMRegressor(n_estimators=200, learning_rate=0.05, random_state=42)

    x_train = np.vstack([arr[idx - n_lags : idx] for idx in range(n_lags, arr.size)])
    y_train = arr[n_lags:]
    model.fit(x_train, y_train)

    history = arr.copy()
    preds: list[float] = []
    for _ in range(horizon):
        x_next = history[-n_lags:].reshape(1, -1)
        y_next = float(model.predict(x_next)[0])
        preds.append(y_next)
        history = np.append(history, y_next)
    return np.asarray(preds, dtype=float)


def forecast_nbeats(
    train: np.ndarray,
    horizon: int,
    *,
    input_size: int = 36,
) -> np.ndarray:
    """Optional N-BEATS integration with graceful fallback.

    If ``neuralforecast`` is unavailable, fallback is naive to keep pipeline usable.
    """
    arr = np.asarray(train, dtype=float)
    if importlib.util.find_spec("neuralforecast") is None:
        return forecast_naive(arr, horizon)
    if arr.size < input_size + horizon + 1:
        return forecast_naive(arr, horizon)

    nf_module = importlib.import_module("neuralforecast")
    models_module = importlib.import_module("neuralforecast.models")
    nbeats_cls = models_module.NBEATS
    nf_cls = nf_module.NeuralForecast
    pd = importlib.import_module("pandas")

    train_df = pd.DataFrame(
        {
            "unique_id": "series_0",
            "ds": np.arange(arr.size),
            "y": arr,
        }
    )
    model = nbeats_cls(
        h=horizon,
        input_size=input_size,
        max_steps=50,
        random_seed=42,
    )
    nf = nf_cls(models=[model], freq=1)
    nf.fit(df=train_df)
    preds = nf.predict().iloc[:, 1].to_numpy(dtype=float)
    return preds[:horizon]


def forecast_linear_autoreg(
    train: np.ndarray,
    horizon: int,
    *,
    n_lags: int = 24,
) -> np.ndarray:
    """Deterministic lightweight autoregression fallback."""
    arr = np.asarray(train, dtype=float)
    if arr.size <= n_lags + 1:
        return forecast_naive(arr, horizon)

    x_train = np.vstack([arr[idx - n_lags : idx] for idx in range(n_lags, arr.size)])
    y_train = arr[n_lags:]
    model = LinearRegression()
    model.fit(x_train, y_train)

    history = arr.copy()
    preds: list[float] = []
    for _ in range(horizon):
        x_next = history[-n_lags:].reshape(1, -1)
        y_next = float(model.predict(x_next)[0])
        preds.append(y_next)
        history = np.append(history, y_next)
    return np.asarray(preds, dtype=float)
