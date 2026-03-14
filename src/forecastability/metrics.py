"""AMI and pAMI metric computation."""

from __future__ import annotations

import numpy as np
from sklearn.feature_selection import mutual_info_regression
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from forecastability.validation import validate_time_series


def _scale_series(ts: np.ndarray) -> np.ndarray:
    """Standardize a univariate series."""
    return StandardScaler().fit_transform(ts.reshape(-1, 1)).ravel()


def compute_ami(
    ts: np.ndarray,
    max_lag: int,
    *,
    n_neighbors: int = 8,
    min_pairs: int = 30,
    random_state: int = 42,
) -> np.ndarray:
    """Compute horizon-specific average mutual information."""
    if max_lag < 1:
        raise ValueError("max_lag must be >= 1")

    arr = validate_time_series(ts, min_length=max_lag + min_pairs + 1)
    arr = _scale_series(arr)

    ami = np.zeros(max_lag, dtype=float)
    for horizon in range(1, max_lag + 1):
        if arr.size - horizon < min_pairs:
            break

        x = arr[:-horizon].reshape(-1, 1)
        y = arr[horizon:]
        value = mutual_info_regression(
            x,
            y,
            n_neighbors=n_neighbors,
            random_state=random_state + horizon,
        )[0]
        ami[horizon - 1] = max(float(value), 0.0)

    return ami


def _build_conditioning_matrix(ts: np.ndarray, lag: int) -> np.ndarray:
    """Build conditioning matrix using intermediate lags 1..lag-1."""
    if lag <= 1:
        return np.empty((ts.size - lag, 0), dtype=float)

    n_rows = ts.size - lag
    cols = [ts[offset : offset + n_rows] for offset in range(1, lag)]
    return np.column_stack(cols)


def compute_pami_linear_residual(
    ts: np.ndarray,
    max_lag: int,
    *,
    n_neighbors: int = 8,
    min_pairs: int = 50,
    random_state: int = 42,
) -> np.ndarray:
    """Compute pAMI via linear residualization + nonlinear MI."""
    if max_lag < 1:
        raise ValueError("max_lag must be >= 1")

    arr = validate_time_series(ts, min_length=max_lag + min_pairs + 1)
    arr = _scale_series(arr)

    pami = np.zeros(max_lag, dtype=float)
    for horizon in range(1, max_lag + 1):
        if arr.size - horizon < min_pairs:
            break

        z = _build_conditioning_matrix(arr, horizon)
        past = arr[:-horizon]
        future = arr[horizon:]

        # Guard: skip underdetermined conditioning regression
        if z.shape[1] > 0 and z.shape[0] <= z.shape[1]:
            break

        if z.shape[1] == 0:
            res_past = past
            res_future = future
        else:
            model_past = LinearRegression()
            model_future = LinearRegression()
            model_past.fit(z, past)
            model_future.fit(z, future)
            res_past = past - model_past.predict(z)
            res_future = future - model_future.predict(z)

        value = mutual_info_regression(
            res_past.reshape(-1, 1),
            res_future,
            n_neighbors=n_neighbors,
            random_state=random_state + horizon,
        )[0]
        pami[horizon - 1] = max(float(value), 0.0)

    return pami
