"""KSG2CurveKernel — concrete unified Chebyshev KSG-II curve estimator (RVH-F01)."""
from __future__ import annotations

import warnings

import numpy as np
from scipy.spatial import cKDTree
from scipy.special import digamma

_DEFAULT_K_LIST = (3, 5, 8)
_DEFAULT_JITTER_SCALE = 1e-7
_DEFAULT_MIN_PAIRS = 30
_LOW_CARDINALITY_THRESHOLD = 0.5


def _apply_jitter(series: np.ndarray, *, jitter_scale: float, random_state: int) -> np.ndarray:
    """One-shot tiny jitter for tie breaking (matches reference _apply_one_shot_jitter)."""
    rng = np.random.default_rng(random_state)
    std = float(np.std(series))
    scale = max(std * jitter_scale, jitter_scale)
    return series + rng.normal(0.0, scale, size=series.size)


def _ksg2_single_k_vectorized(
    x: np.ndarray,
    y: np.ndarray,
    *,
    k: int,
    neighbor_indices: np.ndarray,
    x_sorted: np.ndarray,
    y_sorted: np.ndarray,
) -> float:
    """KSG-II MI estimate for one k value. Matches the reference _ksg2_single_k."""
    eps_x = np.max(np.abs(x[neighbor_indices] - x[:, None]), axis=1)
    eps_y = np.max(np.abs(y[neighbor_indices] - y[:, None]), axis=1)
    nx = (
        np.searchsorted(x_sorted, x + eps_x, side="right")
        - np.searchsorted(x_sorted, x - eps_x, side="left")
        - 1
    )
    ny = (
        np.searchsorted(y_sorted, y + eps_y, side="right")
        - np.searchsorted(y_sorted, y - eps_y, side="left")
        - 1
    )
    nx = np.maximum(nx, 1)
    ny = np.maximum(ny, 1)
    return float(digamma(k) - 1.0 / k + digamma(len(x)) - np.mean(digamma(nx) + digamma(ny)))


class KSG2CurveKernel:
    """Concrete unified Chebyshev KSG-II curve estimator.

    Implements the KSG2CurveKernel Protocol from ports/ksg2_curve_kernel.py.
    Replaces PurePythonBatchedKnnMiKernel as the default estimator for all
    public AMI/pAMI surfaces in v0.5.0.

    Uses scipy.spatial.cKDTree (Chebyshev/p=inf metric) for neighbor search.
    One tree build per (past, future) joint slice; marginal counts via
    np.searchsorted on pre-sorted arrays.

    Invariant B: estimate_curve results match _ksg2_median_profile_value
    reference within ~1e-6 relative error on non-degenerate inputs.
    """

    def __init__(
        self,
        *,
        k_list: tuple[int, ...] = _DEFAULT_K_LIST,
        jitter_scale: float = _DEFAULT_JITTER_SCALE,
        min_pairs: int = _DEFAULT_MIN_PAIRS,
    ) -> None:
        self._k_list = k_list
        self._jitter_scale = jitter_scale
        self._min_pairs = min_pairs

    @property
    def k_list(self) -> tuple[int, ...]:
        return self._k_list

    def estimate_curve(
        self,
        series: np.ndarray,
        lag_range: int,
        k_list: tuple[int, ...] | None = None,
        *,
        random_state: int = 42,
    ) -> np.ndarray:
        """Estimate AMI curve via KSG-II.

        Parameters
        ----------
        series: 1-D float64 array (raw, unscaled).
        lag_range: Number of lags H (lags 1..H).
        k_list: Neighbour counts for median aggregation. Uses instance default if None.
        random_state: Seed for one-shot jitter.

        Returns
        -------
        np.ndarray: Shape (H, len(k_list)), float64.
            Column k gives the KSG-II estimate for k_list[k].
            Median across columns gives the canonical profile.
        """
        k_list = k_list if k_list is not None else self._k_list
        n_unique = len(np.unique(series))
        if n_unique / len(series) < _LOW_CARDINALITY_THRESHOLD:
            warnings.warn(
                f"Low-cardinality input detected ({n_unique} unique / {len(series)} samples). "
                "KSG estimators perform poorly on discrete data. "
                "Consider using estimator='gcmi_rank' for categorical/integer series.",
                UserWarning,
                stacklevel=2,
            )

        jittered = _apply_jitter(series, jitter_scale=self._jitter_scale, random_state=random_state)
        k_max = max(k_list)
        H = lag_range
        result = np.full((H, len(k_list)), np.nan, dtype=float)

        for h_idx in range(H):
            h = h_idx + 1
            n_pairs = jittered.size - h
            if n_pairs < self._min_pairs:
                continue
            x = jittered[:n_pairs]
            y = jittered[h:]
            result[h_idx] = self._estimate_horizon(x, y, k_list=k_list, k_max=k_max)

        return result

    def _estimate_horizon(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        k_list: tuple[int, ...],
        k_max: int,
    ) -> np.ndarray:
        xy = np.column_stack((x, y))
        tree = cKDTree(xy, leafsize=16)
        _, indices = tree.query(xy, k=k_max + 1, workers=1, p=np.inf)

        x_sorted = np.sort(x)
        y_sorted = np.sort(y)

        values = []
        for k in k_list:
            nn_idx = indices[:, 1 : k + 1]
            mi = _ksg2_single_k_vectorized(
                x, y, k=k, neighbor_indices=nn_idx, x_sorted=x_sorted, y_sorted=y_sorted
            )
            values.append(mi)
        return np.array(values, dtype=float)

    def estimate_surrogate_band(
        self,
        series: np.ndarray,
        lag_range: int,
        k_list: tuple[int, ...] | None = None,
        n_surrogates: int = 99,
        random_state: int = 42,
    ) -> np.ndarray:
        """Estimate surrogate band via phase-randomised surrogates.

        Enforces n_surrogates >= 99. Uses SeedSequence.spawn for deterministic
        per-surrogate seeds.

        Returns
        -------
        np.ndarray: Shape (n_surrogates, H, len(k_list)), float64.
        """
        if n_surrogates < 99:
            raise ValueError("n_surrogates must be >= 99")

        k_list = k_list if k_list is not None else self._k_list
        from numpy.random import SeedSequence

        from forecastability.diagnostics.surrogates import phase_surrogates

        surrogates = phase_surrogates(series, n_surrogates=n_surrogates, random_state=random_state)
        ss = SeedSequence(random_state + 1)
        child_seeds = [int(s.generate_state(1)[0]) for s in ss.spawn(n_surrogates)]

        H = lag_range
        m = len(k_list)
        band = np.full((n_surrogates, H, m), np.nan, dtype=float)
        for i, (surr, seed) in enumerate(zip(surrogates, child_seeds, strict=True)):
            band[i] = self.estimate_curve(surr, lag_range, k_list, random_state=seed)
        return band
