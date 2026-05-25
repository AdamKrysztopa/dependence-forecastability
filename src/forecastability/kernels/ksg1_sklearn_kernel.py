"""Ksg1SklearnKernel — legacy sklearn KSG-I compatibility kernel (RVH-F01).

Reproduces v0.4.3 compute_ami numerics bit-identically when estimator='ksg1_sklearn'
is passed to any public AMI/pAMI function.

PurePythonBatchedKnnMiKernel alias is preserved here for backward compatibility
with existing tests. It will be removed in v0.6.0.
"""

from __future__ import annotations

import warnings

import numpy as np
from sklearn.feature_selection import mutual_info_regression


class Ksg1SklearnKernel:
    """Legacy KSG-I estimator wrapping sklearn.mutual_info_regression.

    Use KSG2CurveKernel for all new code. This kernel exists only for
    backwards-compatible reproduction of v0.4.3 numerics via estimator='ksg1_sklearn'.
    """

    def __init__(self, *, n_neighbors: int = 8) -> None:
        self._n_neighbors = n_neighbors

    def estimate_curve(
        self,
        series: np.ndarray,
        lag_range: int,
        *,
        random_state: int = 42,
    ) -> np.ndarray:
        """Estimate AMI curve using sklearn KSG-I (single k, no median).

        Returns
        -------
        np.ndarray: Shape (H,), float64. Single-k, no median aggregation.
        """
        from sklearn.preprocessing import StandardScaler

        arr = StandardScaler().fit_transform(series.reshape(-1, 1)).ravel()
        result = np.zeros(lag_range, dtype=float)
        for horizon in range(1, lag_range + 1):
            n_pairs = arr.size - horizon
            if n_pairs < 30:
                break
            x = arr[:n_pairs].reshape(-1, 1)
            y = arr[horizon:]
            value = mutual_info_regression(
                x, y, n_neighbors=self._n_neighbors, random_state=random_state + horizon
            )[0]
            result[horizon - 1] = max(0.0, float(value))
        return result


# Backward-compatibility alias — removed in v0.6.0
class PurePythonBatchedKnnMiKernel:
    """Deprecated. Use Ksg1SklearnKernel or KSG2CurveKernel instead."""

    def __init__(self) -> None:
        warnings.warn(
            "PurePythonBatchedKnnMiKernel is deprecated in v0.5.0 and will be removed "
            "in v0.6.0. Use KSG2CurveKernel (default) or Ksg1SklearnKernel (legacy).",
            DeprecationWarning,
            stacklevel=2,
        )
        self._inner = Ksg1SklearnKernel()

    def batched_knn_mi(
        self,
        pairs: list[tuple[np.ndarray, np.ndarray]],
        *,
        n_neighbors: int,
        random_state: int,
    ) -> np.ndarray:
        if not pairs:
            return np.empty(0, dtype=np.float64)
        results = []
        for past, future in pairs:
            mi = mutual_info_regression(
                past.reshape(-1, 1),
                future,
                n_neighbors=n_neighbors,
                discrete_features=False,
                random_state=random_state,
            )[0]
            results.append(max(0.0, float(mi)))
        return np.array(results, dtype=np.float64)
