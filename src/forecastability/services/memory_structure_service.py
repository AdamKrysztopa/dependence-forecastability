"""Deterministic DFA-based memory summaries for the extended fingerprint."""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike

from forecastability.services._extended_diagnostic_validation import coerce_univariate_values
from forecastability.triage.extended_forecastability import MemoryStructureResult

_SHORT_SERIES_NOTE = "series is too short for a stable DFA fit"
_CONSTANT_SERIES_NOTE = "constant series; memory structure is undefined"
_LIMITED_SCALE_NOTE = "limited scale coverage makes the DFA fit unstable"
_HIGH_ALPHA_NOTE = (
    "dfa_alpha exceeds 1.0; interpret as a nonstationary or trend-contaminated warning"
)


def _resolve_scales(
    n_observations: int,
    *,
    min_scale: int | None,
    max_scale: int | None,
    n_scales: int,
) -> np.ndarray:
    """Resolve a deterministic set of DFA scales."""
    if n_scales < 3:
        raise ValueError("n_scales must be at least 3")
    lower = 4 if min_scale is None else min_scale
    upper = max(lower + 1, n_observations // 4) if max_scale is None else max_scale
    if lower < 4:
        raise ValueError("min_scale must be at least 4 when provided")
    if upper <= lower:
        raise ValueError("max_scale must be greater than min_scale")
    effective_upper = min(upper, n_observations // 4)
    if effective_upper <= lower:
        return np.array([], dtype=int)
    scales = np.unique(np.geomspace(lower, effective_upper, num=n_scales).astype(int))
    return np.asarray([scale for scale in scales if n_observations // int(scale) >= 2], dtype=int)


def _dfa_fluctuation(profile: np.ndarray, *, scale: int) -> float | None:
    """Compute the DFA fluctuation at one scale."""
    n_segments = profile.size // scale
    if n_segments < 2:
        return None
    segments = profile[: n_segments * scale].reshape(n_segments, scale)
    time_index = np.arange(scale, dtype=float)
    centered_time = time_index - float(np.mean(time_index))
    denominator = float(np.dot(centered_time, centered_time))
    mean_squares: list[float] = []
    for segment in segments:
        centered_segment = segment - float(np.mean(segment))
        slope = (
            0.0
            if denominator == 0.0
            else float(np.dot(centered_time, centered_segment) / denominator)
        )
        trend = float(np.mean(segment)) + slope * centered_time
        detrended = segment - trend
        mean_squares.append(float(np.mean(np.square(detrended))))
    mean_square = float(np.mean(mean_squares))
    if mean_square <= 0.0:
        return None
    return math.sqrt(mean_square)


def _classify_memory_type(
    alpha: float | None,
) -> Literal[
    "anti_persistent",
    "short_memory",
    "persistent",
    "long_memory_candidate",
    "unclear",
]:
    """Map DFA alpha to a conservative persistence label."""
    if alpha is None:
        return "unclear"
    if alpha < 0.45:
        return "anti_persistent"
    if alpha <= 0.55:
        return "short_memory"
    if alpha <= 0.9:
        return "persistent"
    if alpha <= 1.0:
        return "long_memory_candidate"
    return "unclear"


def compute_memory_structure(
    values: ArrayLike,
    *,
    min_scale: int | None = None,
    max_scale: int | None = None,
    n_scales: int = 12,
) -> MemoryStructureResult:
    """Compute a conservative DFA-based memory summary.

    Args:
        values: Univariate series values to analyze.
        min_scale: Optional lower DFA scale bound.
        max_scale: Optional upper DFA scale bound.
        n_scales: Number of scales that will eventually be evaluated.

    Returns:
        Memory-structure result with DFA alpha when the fit is stable enough.
    """
    arr = coerce_univariate_values(values)
    if float(np.ptp(arr)) <= 1e-12:
        return MemoryStructureResult(
            dfa_alpha=None,
            hurst_proxy=None,
            memory_type="unclear",
            scale_range=None,
            notes=[_CONSTANT_SERIES_NOTE],
        )

    scales = _resolve_scales(
        arr.size,
        min_scale=min_scale,
        max_scale=max_scale,
        n_scales=n_scales,
    )
    if scales.size < 3:
        return MemoryStructureResult(
            dfa_alpha=None,
            hurst_proxy=None,
            memory_type="unclear",
            scale_range=None,
            notes=[_SHORT_SERIES_NOTE],
        )

    profile = np.cumsum(arr - float(np.mean(arr)))
    valid_scales: list[int] = []
    fluctuations: list[float] = []
    for scale in scales.tolist():
        fluctuation = _dfa_fluctuation(profile, scale=scale)
        if fluctuation is None:
            continue
        valid_scales.append(int(scale))
        fluctuations.append(float(fluctuation))
    if len(valid_scales) < 3:
        return MemoryStructureResult(
            dfa_alpha=None,
            hurst_proxy=None,
            memory_type="unclear",
            scale_range=None,
            notes=[_SHORT_SERIES_NOTE],
        )

    log_scales = np.log(np.asarray(valid_scales, dtype=float))
    log_fluctuations = np.log(np.asarray(fluctuations, dtype=float))
    slope, intercept = np.polyfit(log_scales, log_fluctuations, deg=1)
    fitted = slope * log_scales + intercept
    ss_res = float(np.sum(np.square(log_fluctuations - fitted)))
    ss_tot = float(np.sum(np.square(log_fluctuations - np.mean(log_fluctuations))))
    r_squared = 1.0 if ss_tot == 0.0 else 1.0 - (ss_res / ss_tot)
    dfa_alpha = float(slope)
    hurst_proxy = None if dfa_alpha > 1.0 else dfa_alpha
    memory_type = _classify_memory_type(dfa_alpha)

    notes: list[str] = []
    if arr.size < 64 or len(valid_scales) < 5 or r_squared < 0.95:
        notes.append(_LIMITED_SCALE_NOTE)
    if dfa_alpha > 1.0:
        notes.append(_HIGH_ALPHA_NOTE)

    return MemoryStructureResult(
        dfa_alpha=dfa_alpha,
        hurst_proxy=hurst_proxy,
        memory_type=memory_type,
        scale_range=(valid_scales[0], valid_scales[-1]),
        notes=notes,
    )
