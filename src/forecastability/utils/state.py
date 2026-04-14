"""Frozen cached state container for ForecastabilityAnalyzer.

Not exported from the public API (__init__.py).
"""

from __future__ import annotations

import dataclasses

import numpy as np


@dataclasses.dataclass(frozen=True, slots=True)
class AnalyzerState:
    """Frozen cached arrays owned by a ForecastabilityAnalyzer instance.

    Immutable by design — internal updates use ``dataclasses.replace()``
    which creates cheap shallow copies (numpy arrays are reference types).

    Attributes:
        ts: Cached univariate target series.
        exog: Cached exogenous series (ForecastabilityAnalyzerExog only).
        ami: Legacy AMI curve cache.
        pami: Legacy pAMI curve cache.
        ami_bands: Legacy AMI surrogate bands ``(lower, upper)``.
        pami_bands: Legacy pAMI surrogate bands ``(lower, upper)``.
        raw: Generic raw dependence curve cache.
        partial: Generic partial dependence curve cache.
        raw_bands: Generic raw surrogate bands ``(lower, upper)``.
        partial_bands: Generic partial surrogate bands ``(lower, upper)``.
        method: Last scorer method used.
    """

    ts: np.ndarray | None = None
    exog: np.ndarray | None = None

    # Legacy AMI/pAMI caches
    ami: np.ndarray | None = None
    pami: np.ndarray | None = None
    ami_bands: tuple[np.ndarray, np.ndarray] | None = None
    pami_bands: tuple[np.ndarray, np.ndarray] | None = None

    # Generic scorer caches
    raw: np.ndarray | None = None
    partial: np.ndarray | None = None
    raw_bands: tuple[np.ndarray, np.ndarray] | None = None
    partial_bands: tuple[np.ndarray, np.ndarray] | None = None

    method: str = "mi"
