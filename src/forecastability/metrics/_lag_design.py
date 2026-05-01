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
