"""AMI and pAMI metric computation."""

from __future__ import annotations

from typing import Literal

import numpy as np
from sklearn.feature_selection import mutual_info_regression

from forecastability.kernels.ksg2_curve_kernel import KSG2CurveKernel
from forecastability.metrics._lag_design import (
    build_intermediate_design,
    residualize_with_intercept,
)
from forecastability.utils.validation import validate_time_series


def _scale_series(ts: np.ndarray) -> np.ndarray:
    """Standardize a univariate series to zero mean and unit variance.

    Replaces ``StandardScaler().fit_transform(...)`` with a direct NumPy
    computation, eliminating the sklearn object construction and reshape
    round-trip on every call (RVH-F04).
    """
    std = ts.std()
    return (ts - ts.mean()) / (std if std > 0.0 else 1.0)


def compute_ami(
    ts: np.ndarray,
    max_lag: int,
    *,
    n_neighbors: int = 8,
    min_pairs: int = 30,
    random_state: int = 42,
    estimator: Literal["ksg2", "ksg1_sklearn"] = "ksg2",
) -> np.ndarray:
    """Compute horizon-specific average mutual information.

    Parameters
    ----------
    ts: Univariate time series.
    max_lag: Number of lags to evaluate.
    n_neighbors: kNN neighbours (used only when estimator='ksg1_sklearn').
    min_pairs: Minimum number of aligned sample pairs required per horizon.
    random_state: Base random seed.
    estimator: "ksg2" (default, v0.5.0) uses KSG-II with Chebyshev cKDTree +
        median over k in {3,5,8}. "ksg1_sklearn" reproduces v0.4.3 KSG-I numerics
        via sklearn.mutual_info_regression (single k=n_neighbors).
    """
    if max_lag < 1:
        raise ValueError("max_lag must be >= 1")

    if estimator == "ksg2":
        arr = validate_time_series(ts, min_length=max_lag + min_pairs + 1)
        kernel = KSG2CurveKernel(min_pairs=min_pairs)
        curve_2d = kernel.estimate_curve(arr, max_lag, random_state=random_state)
        # Median across k axis, clip to 0
        return np.maximum(np.nanmedian(curve_2d, axis=1), 0.0)
    elif estimator == "ksg1_sklearn":
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
    else:
        raise ValueError(f"estimator must be 'ksg2' or 'ksg1_sklearn', got {estimator!r}")


def _build_conditioning_matrix(ts: np.ndarray, lag: int) -> np.ndarray:
    """Build conditioning matrix using intermediate lags 1..lag-1."""
    return build_intermediate_design(ts, lag)


def compute_pami_linear_residual(
    ts: np.ndarray,
    max_lag: int,
    *,
    n_neighbors: int = 8,
    min_pairs: int = 50,
    random_state: int = 42,
    estimator: Literal["ksg2", "ksg1_sklearn"] = "ksg2",
) -> np.ndarray:
    """Compute pAMI via linear residualization + nonlinear MI.

    Parameters
    ----------
    estimator: "ksg2" (default) routes the residualized-pair MI through
        KSG2CurveKernel._estimate_horizon (single-horizon call with k in {3,5,8},
        median aggregation). "ksg1_sklearn" reproduces v0.4.3 numerics via
        sklearn.mutual_info_regression.
    """
    if max_lag < 1:
        raise ValueError("max_lag must be >= 1")

    arr = validate_time_series(ts, min_length=max_lag + min_pairs + 1)
    arr = _scale_series(arr)

    pami = np.zeros(max_lag, dtype=float)

    if estimator == "ksg2":
        kernel = KSG2CurveKernel(min_pairs=min_pairs)
        k_list = kernel.k_list
        k_max = max(k_list)
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
                res_past, res_future = residualize_with_intercept(z, (past, future))

            values = kernel._estimate_horizon(
                res_past, res_future, k_list=k_list, k_max=k_max
            )
            pami[horizon - 1] = max(float(np.nanmedian(values)), 0.0)

    elif estimator == "ksg1_sklearn":
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
                res_past, res_future = residualize_with_intercept(z, (past, future))

            value = mutual_info_regression(
                res_past.reshape(-1, 1),
                res_future,
                n_neighbors=n_neighbors,
                random_state=random_state + horizon,
            )[0]
            pami[horizon - 1] = max(float(value), 0.0)

    else:
        raise ValueError(f"estimator must be 'ksg2' or 'ksg1_sklearn', got {estimator!r}")

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
    estimator: Literal["ksg2", "ksg1_sklearn"] = "ksg2",
) -> float:
    """Compute AMI at a single horizon *h*.

    Returns the same value as
    ``compute_ami(ts, max_lag=H, random_state=R)[h - 1]``
    for any ``H >= h`` and ``random_state=R``, provided the series satisfies
    the ``max_lag=H`` minimum-length requirement.

    Invariant F: ``_scale_series`` is applied once to the full series before
    slicing (ksg1_sklearn path only).  The aligned pair is never independently
    scaled.

    Args:
        ts: Univariate time series.
        h: Horizon index (1-based).
        n_neighbors: kNN neighbours for MI estimation (ksg1_sklearn only).
        min_pairs: Minimum number of aligned sample pairs.
        random_state: Base random seed; internally uses ``random_state + h``
            for the MI estimator on the ksg1_sklearn path.
        estimator: "ksg2" (default) or "ksg1_sklearn".

    Returns:
        Non-negative scalar MI value at horizon *h*, or ``0.0`` when the
        series is too short to form ``min_pairs`` aligned pairs.

    Raises:
        ValueError: If ``h < 1``.
    """
    if h < 1:
        raise ValueError("h must be >= 1")
    arr = validate_time_series(ts, min_length=h + min_pairs + 1)
    if arr.size - h < min_pairs:
        return 0.0
    if estimator == "ksg2":
        kernel = KSG2CurveKernel(min_pairs=min_pairs)
        k_list = kernel.k_list
        k_max = max(k_list)
        from forecastability.kernels.ksg2_curve_kernel import _apply_jitter
        jittered = _apply_jitter(arr, jitter_scale=kernel._jitter_scale, random_state=random_state)
        x = jittered[:-h]
        y = jittered[h:]
        values = kernel._estimate_horizon(x, y, k_list=k_list, k_max=k_max)
        return max(float(np.nanmedian(values)), 0.0)
    else:
        arr = _scale_series(arr)
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
    estimator: Literal["ksg2", "ksg1_sklearn"] = "ksg2",
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
        n_neighbors: kNN neighbours for MI estimation (ksg1_sklearn only).
        min_pairs: Minimum number of aligned sample pairs.
        random_state: Base random seed; internally uses ``random_state + h``
            for the MI estimator (ksg1_sklearn path).
        estimator: "ksg2" (default) or "ksg1_sklearn".

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
        res_past, res_future = residualize_with_intercept(z, (past, future))
    if estimator == "ksg2":
        kernel = KSG2CurveKernel(min_pairs=min_pairs)
        k_list = kernel.k_list
        k_max = max(k_list)
        values = kernel._estimate_horizon(res_past, res_future, k_list=k_list, k_max=k_max)
        return max(float(np.nanmedian(values)), 0.0)
    else:
        value = mutual_info_regression(
            res_past.reshape(-1, 1),
            res_future,
            n_neighbors=n_neighbors,
            random_state=random_state + h,
        )[0]
        return max(float(value), 0.0)
