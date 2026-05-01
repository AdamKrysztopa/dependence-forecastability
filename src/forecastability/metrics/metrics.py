"""AMI and pAMI metric computation."""

from __future__ import annotations

import numpy as np
from sklearn.feature_selection import mutual_info_regression
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from forecastability.utils.validation import validate_time_series


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


# ---------------------------------------------------------------------------
# Single-horizon helpers (PBE-F04)
# ---------------------------------------------------------------------------


def compute_ami_at_horizon(
    ts: np.ndarray,
    h: int,
    *,
    n_neighbors: int = 8,
    min_pairs: int = 30,
    random_state: int = 42,
) -> float:
    """Compute AMI at a single horizon *h*.

    Returns the same value as
    ``compute_ami(ts, max_lag=H, random_state=R)[h - 1]``
    for any ``H >= h`` and ``random_state=R``, provided the series satisfies
    the ``max_lag=H`` minimum-length requirement.

    Invariant F: ``_scale_series`` is applied once to the full series before
    slicing.  The aligned pair is never independently scaled.

    Args:
        ts: Univariate time series.
        h: Horizon index (1-based).
        n_neighbors: kNN neighbours for MI estimation.
        min_pairs: Minimum number of aligned sample pairs.
        random_state: Base random seed; internally uses ``random_state + h``
            for the MI estimator (mirrors the full-curve convention).

    Returns:
        Non-negative scalar MI value at horizon *h*, or ``0.0`` when the
        series is too short to form ``min_pairs`` aligned pairs.

    Raises:
        ValueError: If ``h < 1``.
    """
    if h < 1:
        raise ValueError("h must be >= 1")
    arr = validate_time_series(ts, min_length=h + min_pairs + 1)
    arr = _scale_series(arr)
    if arr.size - h < min_pairs:
        return 0.0
    x = arr[:-h].reshape(-1, 1)
    y = arr[h:]
    value = mutual_info_regression(
        x,
        y,
        n_neighbors=n_neighbors,
        random_state=random_state + h,
    )[0]
    return max(float(value), 0.0)


def compute_pami_at_horizon(
    ts: np.ndarray,
    h: int,
    *,
    n_neighbors: int = 8,
    min_pairs: int = 50,
    random_state: int = 42,
) -> float:
    """Compute pAMI at a single horizon *h* (legacy break-then-zero semantics).

    Returns the same value as
    ``compute_pami_linear_residual(ts, max_lag=H, random_state=R)[h - 1]``
    for any ``H >= h``, including the legacy underdetermined-conditioning
    guard: when the conditioning matrix is underdetermined (``n_rows <= n_cols``),
    the helper returns ``0.0`` exactly as the full-curve loop would via ``break``.

    Invariant F: ``_scale_series`` is applied once to the full series before
    slicing.  The aligned pair is never independently scaled.

    Args:
        ts: Univariate time series.
        h: Horizon index (1-based).
        n_neighbors: kNN neighbours for MI estimation.
        min_pairs: Minimum number of aligned sample pairs.
        random_state: Base random seed; internally uses ``random_state + h``
            for the MI estimator (mirrors the full-curve convention).

    Returns:
        Non-negative scalar pAMI value at horizon *h*, or ``0.0`` when the
        series is too short or the conditioning set is underdetermined.

    Raises:
        ValueError: If ``h < 1``.
    """
    if h < 1:
        raise ValueError("h must be >= 1")
    arr = validate_time_series(ts, min_length=h + min_pairs + 1)
    arr = _scale_series(arr)
    if arr.size - h < min_pairs:
        return 0.0
    z = _build_conditioning_matrix(arr, h)
    past = arr[:-h]
    future = arr[h:]
    # Mirror the legacy break-then-zero guard: underdetermined → 0.0
    if z.shape[1] > 0 and z.shape[0] <= z.shape[1]:
        return 0.0
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
        random_state=random_state + h,
    )[0]
    return max(float(value), 0.0)
