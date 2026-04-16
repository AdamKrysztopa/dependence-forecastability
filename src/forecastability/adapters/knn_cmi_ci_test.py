"""Residualization-based kNN CI test for tigramite PCMCI+ (V3-F04).

Provides a ``CondIndTest`` subclass that delegates to
``forecastability.diagnostics.cmi.compute_conditional_mi_with_backend``
for the dependence measure and implements its own permutation test
to avoid a NumPy 2.x compatibility bug in tigramite's
``_get_block_length``.

The shipped implementation estimates dependence between residuals; with
the default ``linear_residual`` backend this should be read as a practical,
residualization-based CI test rather than fully non-parametric conditioning.

The module is imported lazily so that ``tigramite`` remains an
optional dependency.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass


def _extract_ci_vectors(
    array: np.ndarray,
    xyz: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract X, Y, and Z views from tigramite's stacked CI-test contract."""
    x = array[xyz == 0, :].T[:, 0]
    y = array[xyz == 1, :].T[:, 0]
    z_mask = xyz == 2
    if np.any(z_mask):
        return x, y, array[z_mask, :].T
    return x, y, np.empty((array.shape[1], 0), dtype=float)


def build_knn_cmi_test(
    *,
    n_neighbors: int = 8,
    n_permutations: int = 199,
    residual_backend: str = "linear_residual",
    seed: int = 42,
) -> object:
    """Factory that lazily imports tigramite and returns a ``KnnCMI`` instance.

    Args:
        n_neighbors: kNN neighbors for MI estimation.
        n_permutations: Shuffle permutations for p-values.
        residual_backend: Backend name passed to ``compute_conditional_mi_with_backend``.
        seed: Base random seed.

    Returns:
        An instantiated ``KnnCMI`` conditional-independence test object.
    """
    base_module = importlib.import_module(
        "tigramite.independence_tests.independence_tests_base",
    )
    cond_ind_test_cls = base_module.CondIndTest

    from forecastability.diagnostics.cmi import (
        _residualize_target_with_backend,
        compute_conditional_mi_with_backend,
    )

    class KnnCMI(cond_ind_test_cls):
        """kNN CI test using residualization + permutation.

        Uses residualization to handle the conditioning set, then estimates
        MI between residuals via kNN. With the default backend this keeps the
        conditioning-removal step linear while allowing a nonlinear score on
        the residuals.

        The permutation test shuffles residuals of X to compute p-values,
        using the Phipson & Smyth (2010) correction:
        ``p = (1 + #{T_b >= T_obs}) / (1 + B)``.
        """

        def __init__(
            self,
            *,
            n_neighbors: int = 8,
            n_permutations: int = 199,
            residual_backend: str = "linear_residual",
            random_state_seed: int = 42,
            **kwargs: object,
        ) -> None:
            kwargs.setdefault("significance", "shuffle_test")
            cond_ind_test_cls.__init__(self, seed=random_state_seed, **kwargs)
            self._measure = "knn_cmi"
            self.two_sided = False
            self.residual_based = False
            self.recycle_residuals = False
            self._n_neighbors = n_neighbors
            self._n_permutations = n_permutations
            self._residual_backend = residual_backend
            self._random_state_seed = random_state_seed

        @property
        def measure(self) -> str:
            return self._measure

        def get_dependence_measure(
            self,
            array: np.ndarray,
            xyz: np.ndarray,
            data_type: object = None,
        ) -> float:
            """Compute kNN conditional MI from the tigramite ``(array, xyz)`` contract.

            Args:
                array: Shape ``(dim, T)`` — stacked variable observations.
                xyz: Int array of shape ``(dim,)`` with 0=X, 1=Y, 2=Z.
                data_type: Unused; kept for interface compatibility.

            Returns:
                Non-negative MI value (clamped to 0.0).
            """
            del data_type
            t_len = array.shape[1]

            x, y, z = _extract_ci_vectors(array, xyz)

            if t_len < 50:
                return 0.0

            mi = compute_conditional_mi_with_backend(
                x,
                y,
                conditioning=z,
                backend=self._residual_backend,
                n_neighbors=self._n_neighbors,
                min_pairs=50,
                random_state=self._random_state_seed,
            )
            return max(float(mi), 0.0)

        def get_shuffle_significance(
            self,
            array: np.ndarray,
            xyz: np.ndarray,
            value: float,
            data_type: object = None,
            return_null_dist: bool = False,
        ) -> float | tuple[float, np.ndarray]:
            """Permutation-based significance using own shuffle logic.

            Avoids tigramite's ``_get_block_length`` which is broken
            under NumPy 2.x (calls ``np.corrcoef(..., ddof=0)``).

            Args:
                array: Shape ``(dim, T)``.
                xyz: Variable role indicators.
                value: Observed test statistic.
                data_type: Unused.
                return_null_dist: If ``True``, also return the sorted null distribution.

            Returns:
                p-value, or ``(p-value, null_dist)`` when *return_null_dist* is set.
            """
            del data_type
            rng = self.random_state  # numpy RandomState set by base class
            x, y, z = _extract_ci_vectors(array, xyz)
            residual_future = _residualize_target_with_backend(
                y,
                conditioning=z,
                backend=self._residual_backend,
                rf_estimators=200,
                rf_max_depth=8,
                et_estimators=300,
                et_max_depth=10,
                random_state=self._random_state_seed + 2,
            )
            null_dist = np.empty(self._n_permutations)

            for b in range(self._n_permutations):
                shuffled_x = np.array(x, copy=True)
                rng.shuffle(shuffled_x)
                residual_past = _residualize_target_with_backend(
                    shuffled_x,
                    conditioning=z,
                    backend=self._residual_backend,
                    rf_estimators=200,
                    rf_max_depth=8,
                    et_estimators=300,
                    et_max_depth=10,
                    random_state=self._random_state_seed + 1,
                )
                null_dist[b] = compute_conditional_mi_with_backend(
                    residual_past,
                    residual_future,
                    conditioning=None,
                    n_neighbors=self._n_neighbors,
                    min_pairs=50,
                    random_state=self._random_state_seed,
                )

            # Phipson & Smyth (2010) correction
            p_value = float((1 + np.sum(null_dist >= value)) / (1 + self._n_permutations))

            if return_null_dist:
                return p_value, np.sort(null_dist)
            return p_value

    return KnnCMI(
        n_neighbors=n_neighbors,
        n_permutations=n_permutations,
        residual_backend=residual_backend,
        random_state_seed=seed,
    )
