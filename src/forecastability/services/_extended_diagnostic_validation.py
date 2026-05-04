"""Shared validation helpers for the extended diagnostic services."""

from __future__ import annotations

from typing import Literal, cast

import numpy as np
from numpy.typing import ArrayLike

SpectralDetrendMode = Literal["none", "linear"]
_SPECTRAL_DETREND_MODES = ("none", "linear")


def coerce_univariate_values(values: ArrayLike) -> np.ndarray:
    """Validate and coerce a finite one-dimensional series."""
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError("values must be a one-dimensional series")
    if arr.size == 0:
        raise ValueError("values must contain at least one observation")
    if not np.isfinite(arr).all():
        raise ValueError("values must be finite")
    return arr


def validate_positive_argument(value: int, *, name: str) -> None:
    """Validate that a strictly positive integer-like argument was supplied."""
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def validate_optional_period(period: int | None) -> None:
    """Validate the optional seasonal period used by extended diagnostics."""
    if period is not None and period <= 1:
        raise ValueError("period must be greater than 1 when provided")


def validate_embedding_dimension(embedding_dimension: int) -> None:
    """Validate the ordinal embedding dimension at service entry."""
    if embedding_dimension < 2:
        raise ValueError("embedding_dimension must be at least 2")


def validate_memory_scale_bounds(
    min_scale: int | None,
    max_scale: int | None,
) -> None:
    """Validate optional DFA scale bounds at the public seam."""
    if min_scale is not None and min_scale < 4:
        raise ValueError("memory_min_scale must be at least 4 when provided")
    if max_scale is not None and max_scale <= 0:
        raise ValueError("memory_max_scale must be positive when provided")
    if min_scale is not None and max_scale is not None and max_scale <= min_scale:
        raise ValueError("memory_max_scale must be greater than memory_min_scale")


def validate_spectral_detrend(detrend: object) -> SpectralDetrendMode:
    """Validate the public spectral detrend mode before calling Welch."""
    if detrend not in _SPECTRAL_DETREND_MODES:
        raise ValueError("detrend must be one of: 'none', 'linear'")
    return cast(SpectralDetrendMode, detrend)
