"""Shared lag-design scaffolding for residualization helpers.

Private utility module. Callers are responsible for input validation; this
helper performs no shape, dtype, or finiteness checks of its own.
"""

from __future__ import annotations

import numpy as np


def build_intermediate_design(arr: np.ndarray, h: int) -> np.ndarray:
    """Aligned design matrix of intermediate lags ``1..h-1`` for residualization.

    Returns an array of shape ``(arr.size - h, h - 1)``. For ``h <= 1`` returns
    an empty ``(arr.size - h, 0)`` matrix. The ``k``-th column (0-indexed)
    equals ``arr[k + 1 : arr.size - h + k + 1]``.

    The output is always a ``float64`` C-contiguous array, matching the
    historical ``np.column_stack`` / ``np.empty(..., dtype=float)`` behavior of
    the duplicated implementations this helper replaces.

    Args:
        arr: 1-D source series.
        h: Horizon / lag (1-based). ``h <= 1`` yields an empty design.

    Returns:
        Design matrix of intermediate-lag columns.
    """
    n_rows = arr.size - h
    if h <= 1:
        return np.empty((n_rows, 0), dtype=np.float64)
    cols = [arr[offset : offset + n_rows] for offset in range(1, h)]
    return np.column_stack(cols)


def residualize_with_intercept(
    z: np.ndarray,
    targets: tuple[np.ndarray, ...],
) -> tuple[np.ndarray, ...]:
    """Residualize one or more 1-D targets on a shared design matrix.

    Solves OLS with intercept once for each target via :func:`np.linalg.lstsq`
    on the augmented design ``[1 | z]``. Returns ``targets`` minus the OLS
    fit. Numerically equivalent (to floating-point tolerance) to
    ``LinearRegression().fit(z, t).predict(z)`` from scikit-learn but avoids
    two model objects and two ``predict`` round-trips per call.

    Args:
        z: Design matrix of shape ``(n_rows, n_cols)``. ``n_cols == 0`` is
            treated as the intercept-only model.
        targets: Tuple of 1-D arrays of length ``n_rows``.

    Returns:
        Tuple of residualized arrays in the same order as ``targets``.
    """
    if z.shape[1] == 0:
        return tuple(t - t.mean() for t in targets)
    augmented = np.column_stack([np.ones(z.shape[0], dtype=z.dtype), z])
    residuals: list[np.ndarray] = []
    for target in targets:
        coef, *_ = np.linalg.lstsq(augmented, target, rcond=None)
        residuals.append(target - augmented @ coef)
    return tuple(residuals)
