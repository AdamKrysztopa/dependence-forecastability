"""Conditional-MI backends for pAMI estimation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import mutual_info_regression
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from forecastability.validation import validate_time_series


class ResidualBackend(Protocol):
    """Interface for residualization backends used in conditional MI."""

    def residualize(
        self, z: np.ndarray, target: np.ndarray, *, random_state: int
    ) -> np.ndarray: ...


@dataclass(slots=True)
class LinearResidualBackend:
    """Linear regression residualization backend."""

    def residualize(self, z: np.ndarray, target: np.ndarray, *, random_state: int) -> np.ndarray:
        del random_state
        model = LinearRegression()
        model.fit(z, target)
        return target - model.predict(z)


@dataclass(slots=True)
class RandomForestResidualBackend:
    """Random-forest residualization backend (stronger nonlinear variant)."""

    n_estimators: int = 200
    max_depth: int | None = 8

    def residualize(self, z: np.ndarray, target: np.ndarray, *, random_state: int) -> np.ndarray:
        model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=random_state,
        )
        model.fit(z, target)
        return target - model.predict(z)


def _scale_series(ts: np.ndarray) -> np.ndarray:
    """Standardize a univariate time series."""
    return StandardScaler().fit_transform(ts.reshape(-1, 1)).ravel()


def _build_conditioning_matrix(ts: np.ndarray, lag: int) -> np.ndarray:
    """Build conditioning matrix using intermediate lags 1..lag-1."""
    if lag <= 1:
        return np.empty((ts.size - lag, 0), dtype=float)
    n_rows = ts.size - lag
    cols = [ts[offset : offset + n_rows] for offset in range(1, lag)]
    return np.column_stack(cols)


def _backend_from_name(
    backend: Literal["linear_residual", "rf_residual"],
    *,
    rf_estimators: int,
    rf_max_depth: int | None,
) -> ResidualBackend:
    """Construct a residual backend from configuration."""
    if backend == "linear_residual":
        return LinearResidualBackend()
    return RandomForestResidualBackend(
        n_estimators=rf_estimators,
        max_depth=rf_max_depth,
    )


def compute_pami_with_backend(
    ts: np.ndarray,
    max_lag: int,
    *,
    backend: Literal["linear_residual", "rf_residual"] = "linear_residual",
    rf_estimators: int = 200,
    rf_max_depth: int | None = 8,
    n_neighbors: int = 8,
    min_pairs: int = 50,
    random_state: int = 42,
) -> np.ndarray:
    """Compute pAMI with pluggable conditional-MI residual backends."""
    if max_lag < 1:
        raise ValueError("max_lag must be >= 1")

    arr = validate_time_series(ts, min_length=max_lag + min_pairs + 1)
    arr = _scale_series(arr)
    residual_backend = _backend_from_name(
        backend,
        rf_estimators=rf_estimators,
        rf_max_depth=rf_max_depth,
    )

    pami = np.zeros(max_lag, dtype=float)
    for horizon in range(1, max_lag + 1):
        if arr.size - horizon < min_pairs:
            break

        z = _build_conditioning_matrix(arr, horizon)
        past = arr[:-horizon]
        future = arr[horizon:]

        if z.shape[1] == 0:
            res_past = past
            res_future = future
        else:
            res_past = residual_backend.residualize(
                z,
                past,
                random_state=random_state + 2 * horizon,
            )
            res_future = residual_backend.residualize(
                z,
                future,
                random_state=random_state + 2 * horizon + 1,
            )

        value = mutual_info_regression(
            res_past.reshape(-1, 1),
            res_future,
            n_neighbors=n_neighbors,
            random_state=random_state + horizon,
        )[0]
        pami[horizon - 1] = max(float(value), 0.0)
    return pami
