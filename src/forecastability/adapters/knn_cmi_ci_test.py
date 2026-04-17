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
from typing import TYPE_CHECKING, Literal

import numpy as np

if TYPE_CHECKING:
    pass

ShuffleScheme = Literal["iid", "block"]
_VALID_SHUFFLE_SCHEMES: tuple[str, ...] = ("iid", "block")


def _validate_shuffle_scheme(shuffle_scheme: str) -> None:
    """Raise ``ValueError`` when ``shuffle_scheme`` is not a recognised option.

    The ``Literal`` type is enforced only by static checkers; callers supplying
    strings from configs or CLIs can silently bypass the intended choice and
    fall through to the ``"iid"`` branch, which produces an anti-conservative
    null on autocorrelated series. This runtime guard closes that hole.
    """
    if shuffle_scheme not in _VALID_SHUFFLE_SCHEMES:
        raise ValueError(
            f"shuffle_scheme must be one of {_VALID_SHUFFLE_SCHEMES}; "
            f"got {shuffle_scheme!r}"
        )


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


def _politis_romano_block_length(t_len: int) -> int:
    """Rule-of-thumb block length ``L = max(1, round(1.75 * T^(1/3)))``."""
    return max(1, int(round(1.75 * float(t_len) ** (1.0 / 3.0))))


def _circular_block_permute(
    x: np.ndarray,
    *,
    block_length: int,
    rng: np.random.RandomState | np.random.Generator,
) -> np.ndarray:
    """Circular block permutation preserving short-range serial structure.

    Rotates the series by a uniform random offset, partitions into contiguous
    blocks of length ``block_length`` (the tail block may be shorter), permutes
    the block order, and trims the concatenation to the original length.
    """
    t_len = int(x.size)
    if block_length <= 1 or t_len <= 1:
        permuted = np.array(x, copy=True)
        rng.shuffle(permuted)
        return permuted
    if isinstance(rng, np.random.Generator):
        start = int(rng.integers(0, t_len))
    else:
        start = int(rng.randint(0, t_len))
    rotated = np.concatenate([x[start:], x[:start]])
    n_blocks = int(np.ceil(t_len / block_length))
    blocks = [rotated[i * block_length : (i + 1) * block_length] for i in range(n_blocks)]
    order = rng.permutation(n_blocks)
    result = np.concatenate([blocks[i] for i in order])
    return result[:t_len]


def _build_linear_projector(z: np.ndarray) -> np.ndarray | None:
    """Return an orthonormal basis ``Q`` for the ``[1, z]`` column space.

    ``None`` is returned when ``z`` has zero columns because in that case the
    linear residual of any vector is the vector itself.
    """
    t_len = z.shape[0]
    if z.shape[1] == 0:
        return None
    z_aug = np.column_stack([np.ones(t_len, dtype=float), z])
    q, _ = np.linalg.qr(z_aug)
    return q


def _linear_residual(v: np.ndarray, projector: np.ndarray | None) -> np.ndarray:
    """Residual of ``v`` after projecting onto the column space encoded by ``projector``."""
    if projector is None:
        return v
    return v - projector @ (projector.T @ v)


def build_knn_cmi_test(
    *,
    n_neighbors: int = 8,
    n_permutations: int = 199,
    residual_backend: str = "linear_residual",
    seed: int = 42,
    shuffle_scheme: ShuffleScheme = "iid",
) -> object:
    """Factory that lazily imports tigramite and returns a ``KnnCMI`` instance.

    Args:
        n_neighbors: kNN neighbors for MI estimation.
        n_permutations: Shuffle permutations for p-values.
        residual_backend: Backend name passed to ``compute_conditional_mi_with_backend``.
        seed: Base random seed.
        shuffle_scheme: Permutation scheme for the null distribution. ``"iid"``
            (default) permutes observations independently; ``"block"`` preserves
            short-range serial correlation via a circular block permutation
            (Politis & Romano, 1994).

    Returns:
        An instantiated ``KnnCMI`` conditional-independence test object.
    """
    _validate_shuffle_scheme(shuffle_scheme)
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
        MI between residuals via kNN. With the default ``linear_residual``
        backend the conditioning-removal step is linear while the score on
        the residuals remains nonlinear.

        Permutation null schemes:
          * ``"iid"`` (default): classical i.i.d. observation shuffle. Fast
            and appropriate when X is serially uncorrelated or already
            whitened by the residualisation step.
          * ``"block"``: circular block permutation (Politis & Romano, 1994)
            with block length ``L = max(1, round(1.75 * T^(1/3)))``. Preserves
            short-range autocorrelation and gives a more conservative null on
            raw autocorrelated series.

        p-values use the Phipson & Smyth (2010) correction
        ``p = (1 + #{T_b >= T_obs}) / (1 + B)``.
        """

        def __init__(
            self,
            *,
            n_neighbors: int = 8,
            n_permutations: int = 199,
            residual_backend: str = "linear_residual",
            random_state_seed: int = 42,
            shuffle_scheme: ShuffleScheme = "iid",
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
            self._shuffle_scheme: ShuffleScheme = shuffle_scheme

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

            Avoids tigramite's ``_get_block_length`` which is broken under
            NumPy 2.x (calls ``np.corrcoef(..., ddof=0)``).

            For ``residual_backend == "linear_residual"`` the projection onto
            the Z column-space is invariant across permutations, so we build
            an orthonormal basis once (QR of ``[1, Z]``) and compute residuals
            of each shuffled X with two matrix multiplies instead of refitting
            an OLS per permutation. Non-linear backends keep the per-permutation
            refit.

            The null is generated by permuting X. The ``"iid"`` scheme is the
            classical exchangeability null and can be anti-conservative on
            strongly autocorrelated raw X; ``"block"`` preserves short-range
            serial structure and is recommended for raw AR-like inputs.

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

            block_length = _politis_romano_block_length(int(x.size))
            linear_fast_path = self._residual_backend == "linear_residual"
            projector = _build_linear_projector(z) if linear_fast_path else None

            null_dist = np.empty(self._n_permutations)
            for b in range(self._n_permutations):
                if self._shuffle_scheme == "block":
                    shuffled_x = _circular_block_permute(x, block_length=block_length, rng=rng)
                else:
                    shuffled_x = np.array(x, copy=True)
                    rng.shuffle(shuffled_x)

                if linear_fast_path:
                    residual_past = _linear_residual(shuffled_x, projector)
                else:
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
        shuffle_scheme=shuffle_scheme,
    )
