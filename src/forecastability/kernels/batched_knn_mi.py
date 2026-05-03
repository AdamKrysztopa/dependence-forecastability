"""Pure-Python batched kNN MI kernel using sklearn (PBE-F23)."""

from __future__ import annotations

import numpy as np
from sklearn.feature_selection import mutual_info_regression  # noqa: PLC0415


class PurePythonBatchedKnnMiKernel:
    """Pure-Python implementation of BatchedKnnMiKernel using sklearn.

    Evaluates each (past, future) pair independently via
    ``sklearn.feature_selection.mutual_info_regression``, matching the
    scalar MI path used elsewhere in the package.  Negative estimates are
    clipped to 0.

    This implementation is the parity oracle for any native kernel.  A future
    native implementation may share NearestNeighbors index construction across
    pairs of the same length, but this pure-Python version keeps correctness
    as its sole optimisation criterion.
    """

    def batched_knn_mi(
        self,
        pairs: list[tuple[np.ndarray, np.ndarray]],
        *,
        n_neighbors: int,
        random_state: int,
    ) -> np.ndarray:
        """Estimate MI for each (past, future) pair.

        Args:
            pairs: Sequence of (past, future) 1-D float64 array pairs.
                Each pair must have arrays of equal length.
            n_neighbors: Number of neighbours for the KSG estimator (>= 1).
            random_state: Integer seed for jitter/tie-breaking.

        Returns:
            1-D float64 array of length ``len(pairs)`` with non-negative MI
            estimates, one per pair.
        """
        if not pairs:
            return np.empty(0, dtype=np.float64)

        results: list[float] = []
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
