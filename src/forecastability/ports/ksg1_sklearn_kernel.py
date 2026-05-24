"""Ksg1SklearnKernel Protocol — legacy sklearn KSG-I compatibility kernel (RVH-F01)."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Ksg1SklearnKernel(Protocol):
    """Protocol for the opt-in KSG-I legacy kernel introduced in v0.5.0.

    Wraps sklearn.feature_selection.mutual_info_regression to reproduce
    v0.4.3 numerics bit-identically when estimator='ksg1_sklearn' is passed
    to any public AMI/pAMI function.

    Use KSG2CurveKernel for all new code; this kernel exists only for
    backwards-compatibility fixture reproduction.
    """

    def estimate_curve(
        self,
        series: np.ndarray,
        lag_range: int,
    ) -> np.ndarray:
        """Estimate AMI curve using sklearn KSG-I.

        Returns
        -------
        np.ndarray: Shape (H,), dtype float64. Single-k, no median.
        """
        ...
