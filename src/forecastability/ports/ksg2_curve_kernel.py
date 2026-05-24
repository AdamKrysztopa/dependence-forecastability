"""KSG2CurveKernel Protocol — unified Chebyshev KSG-II curve estimator contract (RVH-F01)."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class KSG2CurveKernel(Protocol):
    """Protocol for the unified Chebyshev KSG-II curve kernel introduced in v0.5.0.

    Distinct from the legacy Ksg2ProfileKernel (ports/kernels.py) which has a
    scalar-profile signature. This protocol exposes the full (H, m) matrix API
    needed for multi-k median-over-k estimation and vectorized surrogate bands.

    All random_state parameters are int, never numpy.Generator.
    Implementors must reject n_surrogates < 99 before any allocation.
    """

    def estimate_curve(
        self,
        series: np.ndarray,
        lag_range: int,
        k_list: tuple[int, ...],
    ) -> np.ndarray:
        """Estimate AMI curve.

        Parameters
        ----------
        series: 1-D float64 array.
        lag_range: Number of lags H to evaluate (lags 1..H).
        k_list: Neighbour counts; median taken across k values.

        Returns
        -------
        np.ndarray: Shape (H, len(k_list)), dtype float64.
        """
        ...

    def estimate_surrogate_band(
        self,
        series: np.ndarray,
        lag_range: int,
        k_list: tuple[int, ...],
        n_surrogates: int,
        random_state: int,
    ) -> np.ndarray:
        """Estimate surrogate band via phase-randomised surrogates.

        Parameters
        ----------
        series: 1-D float64 array.
        lag_range: Number of lags H.
        k_list: Neighbour counts.
        n_surrogates: Must be >= 99.
        random_state: Integer seed.

        Returns
        -------
        np.ndarray: Shape (n_surrogates, H, len(k_list)), dtype float64.
        """
        ...
