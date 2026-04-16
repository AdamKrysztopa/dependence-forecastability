"""Conditional-MI backends for pAMI estimation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.feature_selection import mutual_info_regression
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from forecastability.utils.validation import validate_time_series

CMIBackendName = Literal["linear_residual", "rf_residual", "extra_trees_residual"]
_CONDITIONAL_MIN_PAIRS_FLOOR = 50


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


@dataclass(slots=True)
class ExtraTreesResidualBackend:
    """Extra-trees residualization backend (variance-reduced nonlinear variant)."""

    n_estimators: int = 300
    max_depth: int | None = 10

    def residualize(self, z: np.ndarray, target: np.ndarray, *, random_state: int) -> np.ndarray:
        model = ExtraTreesRegressor(
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
    backend: str,
    *,
    rf_estimators: int,
    rf_max_depth: int | None,
    et_estimators: int,
    et_max_depth: int | None,
) -> ResidualBackend:
    """Construct a residual backend from configuration."""
    if backend == "linear_residual":
        return LinearResidualBackend()
    if backend == "rf_residual":
        return RandomForestResidualBackend(
            n_estimators=rf_estimators,
            max_depth=rf_max_depth,
        )
    if backend == "extra_trees_residual":
        return ExtraTreesResidualBackend(
            n_estimators=et_estimators,
            max_depth=et_max_depth,
        )
    raise ValueError(
        "Unsupported pAMI backend. Supported backends are "
        "'linear_residual', 'rf_residual', and 'extra_trees_residual'."
    )


def _validate_aligned_pair(
    past: np.ndarray,
    future: np.ndarray,
    *,
    min_pairs: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Validate a pair of aligned vectors for conditional-MI estimation."""
    validated_past = validate_time_series(past, min_length=min_pairs)
    validated_future = validate_time_series(future, min_length=min_pairs)
    if validated_past.size != validated_future.size:
        raise ValueError(
            "past and future must have identical lengths; "
            f"got {validated_past.size} and {validated_future.size}"
        )
    return validated_past, validated_future


def _coerce_conditioning_matrix(
    conditioning: np.ndarray | None,
    *,
    n_rows: int,
) -> np.ndarray:
    """Return a 2-D conditioning matrix with row count *n_rows*."""
    if conditioning is None:
        return np.empty((n_rows, 0), dtype=float)
    z = np.asarray(conditioning, dtype=float)
    if z.ndim == 1:
        z = z.reshape(-1, 1)
    if z.ndim != 2:
        raise ValueError(
            f"conditioning must be a 1-D or 2-D numeric array; got array with ndim={z.ndim}"
        )
    if z.shape[0] != n_rows:
        raise ValueError(
            "conditioning rows must match past/future length; "
            f"got {z.shape[0]} rows and expected {n_rows}"
        )
    return z


def _validate_conditional_sample_requirements(
    *,
    n_rows: int,
    n_features: int,
    min_pairs: int,
) -> None:
    """Validate sample-size requirements for conditional estimators.

    Conditional MI estimation is materially less stable than bivariate MI.
    We therefore enforce the project floor ``min_pairs >= 50`` and, when
    conditioning is present, require at least ``2 * min_pairs`` aligned rows.
    """
    if min_pairs < _CONDITIONAL_MIN_PAIRS_FLOOR:
        raise ValueError(f"min_pairs must be >= 50 for conditional estimators; got {min_pairs}")
    if n_features > 0 and n_rows < 2 * min_pairs:
        raise ValueError(
            "conditional estimators require at least 2 * min_pairs aligned rows "
            f"when conditioning is non-empty; got rows={n_rows}, min_pairs={min_pairs}"
        )
    if n_features > 0 and n_rows <= n_features:
        raise ValueError(
            "conditioning regression is underdetermined: "
            f"rows={n_rows} must be > columns={n_features}"
        )


def compute_conditional_mi_with_backend(
    past: np.ndarray,
    future: np.ndarray,
    *,
    conditioning: np.ndarray | None = None,
    backend: str = "linear_residual",
    rf_estimators: int = 200,
    rf_max_depth: int | None = 8,
    et_estimators: int = 300,
    et_max_depth: int | None = 10,
    n_neighbors: int = 8,
    min_pairs: int = 50,
    random_state: int = 42,
) -> float:
    r"""Estimate conditional MI $I(\text{future}; \text{past} \mid Z)$.

    Uses the same residualization backends as :func:`compute_pami_with_backend`.
    When ``conditioning`` is empty, this reduces to standard bivariate MI.

    Args:
        past: Predictor vector.
        future: Response vector aligned to ``past``.
        conditioning: Optional conditioning matrix ``Z``.
        backend: Residualization backend name.
        rf_estimators: Number of trees for RF backend.
        rf_max_depth: Optional max depth for RF backend.
        et_estimators: Number of trees for extra-trees backend.
        et_max_depth: Optional max depth for extra-trees backend.
        n_neighbors: Neighbors for kNN MI estimator.
        min_pairs: Minimum aligned pairs required.
        random_state: Deterministic seed.

    Returns:
        Non-negative conditional MI estimate.

    Raises:
        ValueError: If shapes are invalid, vectors are misaligned, or
            the conditioning regression is underdetermined.
    """
    if n_neighbors < 1:
        raise ValueError(f"n_neighbors must be >= 1; got {n_neighbors}")

    aligned_past, aligned_future = _validate_aligned_pair(past, future, min_pairs=min_pairs)
    z = _coerce_conditioning_matrix(conditioning, n_rows=aligned_past.size)
    _validate_conditional_sample_requirements(
        n_rows=z.shape[0],
        n_features=z.shape[1],
        min_pairs=min_pairs,
    )

    if z.shape[1] == 0:
        residual_past = aligned_past
        residual_future = aligned_future
    else:
        residual_backend = _backend_from_name(
            backend,
            rf_estimators=rf_estimators,
            rf_max_depth=rf_max_depth,
            et_estimators=et_estimators,
            et_max_depth=et_max_depth,
        )
        residual_past = residual_backend.residualize(
            z,
            aligned_past,
            random_state=random_state + 1,
        )
        residual_future = residual_backend.residualize(
            z,
            aligned_future,
            random_state=random_state + 2,
        )

    value = mutual_info_regression(
        residual_past.reshape(-1, 1),
        residual_future,
        n_neighbors=n_neighbors,
        random_state=random_state,
    )[0]
    return max(float(value), 0.0)


def compute_pami_with_backend(
    ts: np.ndarray,
    max_lag: int,
    *,
    backend: str = "linear_residual",
    rf_estimators: int = 200,
    rf_max_depth: int | None = 8,
    et_estimators: int = 300,
    et_max_depth: int | None = 10,
    n_neighbors: int = 8,
    min_pairs: int = 50,
    random_state: int = 42,
) -> np.ndarray:
    """Compute pAMI with pluggable conditional-MI residual backends."""
    if max_lag < 1:
        raise ValueError("max_lag must be >= 1")
    if min_pairs < _CONDITIONAL_MIN_PAIRS_FLOOR:
        raise ValueError(f"min_pairs must be >= 50 for conditional estimators; got {min_pairs}")

    arr = validate_time_series(ts, min_length=max_lag + min_pairs + 1)
    arr = _scale_series(arr)

    pami = np.zeros(max_lag, dtype=float)
    for horizon in range(1, max_lag + 1):
        if arr.size - horizon < min_pairs:
            break

        z = _build_conditioning_matrix(arr, horizon)
        past = arr[:-horizon]
        future = arr[horizon:]

        # Conditional estimators need a stronger data floor than raw MI.
        if z.shape[1] > 0 and z.shape[0] < 2 * min_pairs:
            break
        if z.shape[1] > 0 and z.shape[0] <= z.shape[1]:
            break

        pami[horizon - 1] = compute_conditional_mi_with_backend(
            past,
            future,
            conditioning=z,
            backend=backend,
            rf_estimators=rf_estimators,
            rf_max_depth=rf_max_depth,
            et_estimators=et_estimators,
            et_max_depth=et_max_depth,
            n_neighbors=n_neighbors,
            min_pairs=min_pairs,
            random_state=random_state + 3 * horizon,
        )
    return pami
