"""Signed cross-correlation profile service.

This service provides a linear baseline profile for driver/target lag structure.
It is descriptive only: correlation is not causal evidence and can miss symmetric
nonlinear couplings that remain detectable via MI-based methods.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

from forecastability.utils.validation import validate_time_series


def _resolve_lag_range(
    *,
    max_lag: int,
    lag_range: tuple[int, int | None],
) -> tuple[int, int]:
    """Resolve and validate lag bounds for profile computation.

    Args:
        max_lag: Maximum lag accepted by the caller.
        lag_range: Inclusive lag bounds ``(start_lag, end_lag_or_none)``.

    Returns:
        Inclusive ``(start_lag, end_lag)`` lag bounds.

    Raises:
        ValueError: If lag bounds are invalid.
    """
    if max_lag < 0:
        raise ValueError(f"max_lag must be >= 0, got {max_lag}")

    lag_start, lag_end_raw = lag_range
    lag_end = max_lag if lag_end_raw is None else lag_end_raw

    if lag_start < 0:
        raise ValueError(f"lag_range start must be >= 0, got {lag_start}")
    if lag_end < lag_start:
        raise ValueError(f"lag_range end must be >= start, got start={lag_start}, end={lag_end}")
    if lag_end > max_lag:
        raise ValueError(f"lag_range end must be <= max_lag, got end={lag_end}, max_lag={max_lag}")

    return lag_start, lag_end


def _signed_pearson(x: np.ndarray, y: np.ndarray) -> float:
    """Compute signed Pearson correlation, returning 0.0 for degenerate slices."""
    if x.size < 2 or y.size < 2:
        return 0.0

    x_std = float(np.std(x))
    y_std = float(np.std(y))
    if x_std == 0.0 or y_std == 0.0:
        return 0.0

    value = float(np.corrcoef(x, y)[0, 1])
    if not np.isfinite(value):
        return 0.0
    return value


def compute_cross_correlation_profile(
    target: np.ndarray,
    driver: np.ndarray,
    *,
    max_lag: int,
    lag_range: tuple[int, int | None] = (0, None),
    method: Literal["pearson"] = "pearson",
) -> np.ndarray:
    """Compute a signed cross-correlation profile over a lag range.

    This function keeps the correlation sign. Consumers that want absolute
    scores for ranking should apply ``abs()`` explicitly downstream.

    Warning:
        This is a linear baseline, not a causal estimator, and it cannot detect
        symmetric nonlinear couplings that may still be visible to MI-based
        profiles.

    Args:
        target: Target series ``Y``.
        driver: Exogenous driver series ``X`` aligned with *target*.
        max_lag: Maximum lag considered by the profile.
        lag_range: Inclusive lag bounds ``(start_lag, end_lag_or_none)``.
            Default ``(0, None)`` means ``0..max_lag``.
        method: Correlation method. Only ``"pearson"`` is currently supported.

    Returns:
        1-D array aligned to ``range(start_lag, end_lag + 1)``.

    Raises:
        ValueError: If method is unsupported or input lengths mismatch.
    """
    if method != "pearson":
        raise ValueError(f"method must be 'pearson', got {method!r}")

    validated_target = validate_time_series(target, min_length=2)
    validated_driver = validate_time_series(driver, min_length=2)
    if validated_target.shape != validated_driver.shape:
        raise ValueError("driver and target must have identical lengths")

    lag_start, lag_end = _resolve_lag_range(max_lag=max_lag, lag_range=lag_range)
    profile = np.zeros(lag_end - lag_start + 1, dtype=float)

    for lag in range(lag_start, lag_end + 1):
        if lag == 0:
            x = validated_driver
            y = validated_target
        else:
            x = validated_driver[:-lag]
            y = validated_target[lag:]
        profile[lag - lag_start] = _signed_pearson(x, y)

    return profile
