"""Deterministic classical structure summaries for the extended fingerprint."""

from __future__ import annotations

from typing import Literal

import numpy as np
from numpy.typing import ArrayLike

from forecastability.services._extended_diagnostic_validation import (
    coerce_univariate_values,
    validate_optional_period,
    validate_positive_argument,
)
from forecastability.services.linear_information_service import _safe_autocorrelation
from forecastability.triage.extended_forecastability import ClassicalStructureResult

_SHORT_SERIES_NOTE = "series is too short for stable classical structure diagnostics"
_CONSTANT_SERIES_NOTE = "constant series; classical structure summaries are not informative"
_SEASONAL_CYCLE_NOTE = "fewer than two full seasonal cycles were available"


def _fit_linear_trend(values: np.ndarray) -> np.ndarray:
    """Fit a deterministic least-squares linear trend."""
    time_index = np.arange(values.size, dtype=float)
    centered_time = time_index - float(np.mean(time_index))
    centered_values = values - float(np.mean(values))
    denominator = float(np.dot(centered_time, centered_time))
    slope = (
        0.0 if denominator == 0.0 else float(np.dot(centered_time, centered_values) / denominator)
    )
    intercept = float(np.mean(values))
    return intercept + slope * centered_time


def _bounded_strength(reference: np.ndarray, residual: np.ndarray) -> float | None:
    """Return a conservative variance-explained strength score."""
    reference_variance = float(np.var(reference))
    if reference_variance <= 1e-12:
        return None
    return float(np.clip(1.0 - (float(np.var(residual)) / reference_variance), 0.0, 1.0))


def _compute_acf_decay_rate(values: np.ndarray, *, max_lag: int) -> float | None:
    """Summarize the early-lag autocorrelation decay rate on a unit scale."""
    lag_limit = min(max_lag, max(2, values.size // 4))
    acf_values = [
        abs(rho)
        for lag in range(1, lag_limit + 1)
        if (rho := _safe_autocorrelation(values, lag)) is not None
    ]
    if len(acf_values) < 2:
        return None
    ratios = [
        current / previous
        for previous, current in zip(acf_values, acf_values[1:], strict=False)
        if previous > 1e-12
    ]
    if not ratios:
        return None
    decay_values = np.clip(1.0 - np.asarray(ratios, dtype=float), 0.0, 1.0)
    return float(np.mean(decay_values))


def _compute_seasonal_component(values: np.ndarray, *, period: int) -> np.ndarray:
    """Estimate a deterministic seasonal template from phase means."""
    phase_means = np.zeros(period, dtype=float)
    for phase in range(period):
        phase_slice = values[phase::period]
        phase_means[phase] = float(np.mean(phase_slice))
    return phase_means[np.arange(values.size) % period]


def _compute_seasonal_strength(values: np.ndarray, *, period: int) -> float | None:
    """Estimate seasonality strength on the same detrended basis as the residual block."""
    seasonal_component = _compute_seasonal_component(values, period=period)
    residual = values - seasonal_component
    template_strength = _bounded_strength(values, residual)
    acf_at_period = _safe_autocorrelation(values, period)
    acf_strength = None if acf_at_period is None else float(np.clip(abs(acf_at_period), 0.0, 1.0))
    candidates = [
        strength for strength in (template_strength, acf_strength) if strength is not None
    ]
    if not candidates:
        return None
    return float(max(candidates))


def _classify_stationarity_hint(
    *,
    acf1: float | None,
    trend_strength: float | None,
    seasonal_strength: float | None,
) -> Literal[
    "likely_stationary",
    "trend_nonstationary",
    "seasonal",
    "unclear",
]:
    """Map classical summaries to a conservative stationarity hint."""
    if trend_strength is not None and trend_strength >= 0.6:
        return "trend_nonstationary"
    if seasonal_strength is not None and seasonal_strength >= 0.45:
        return "seasonal"
    if (
        acf1 is not None
        and abs(acf1) <= 0.25
        and (trend_strength is None or trend_strength < 0.2)
        and (seasonal_strength is None or seasonal_strength < 0.2)
    ):
        return "likely_stationary"
    return "unclear"


def compute_classical_structure(
    values: ArrayLike,
    *,
    period: int | None = None,
    max_lag: int = 40,
) -> ClassicalStructureResult:
    """Compute deterministic trend, seasonality, and autocorrelation summaries.

    Args:
        values: Univariate series values to analyze.
        period: Optional seasonal period for period-aware summaries.
        max_lag: Maximum lag used by deterministic autocorrelation summaries.

    Returns:
        Classical structure summary with conservative notes for unstable cases.
    """
    arr = coerce_univariate_values(values)
    validate_positive_argument(max_lag, name="max_lag")
    validate_optional_period(period)
    if arr.size < 6:
        return ClassicalStructureResult(
            acf1=None,
            acf_decay_rate=None,
            seasonal_strength=None,
            trend_strength=None,
            residual_variance_ratio=None,
            stationarity_hint="unclear",
            notes=[_SHORT_SERIES_NOTE],
        )
    if float(np.ptp(arr)) <= 1e-12:
        return ClassicalStructureResult(
            acf1=None,
            acf_decay_rate=None,
            seasonal_strength=None,
            trend_strength=None,
            residual_variance_ratio=None,
            stationarity_hint="unclear",
            notes=[_CONSTANT_SERIES_NOTE],
        )

    trend_component = _fit_linear_trend(arr)
    detrended = arr - trend_component
    trend_strength = _bounded_strength(arr, detrended)

    seasonal_strength: float | None = None
    residual = detrended
    notes: list[str] = []
    if period is not None:
        if arr.size < 2 * period:
            notes.append(_SEASONAL_CYCLE_NOTE)
        else:
            seasonal_component = _compute_seasonal_component(detrended, period=period)
            residual = detrended - seasonal_component
            seasonal_strength = _compute_seasonal_strength(detrended, period=period)

    residual_variance_ratio = None
    reference_variance = float(np.var(arr))
    if reference_variance > 1e-12:
        residual_variance_ratio = float(np.var(residual) / reference_variance)

    acf1 = _safe_autocorrelation(arr, 1)
    acf_decay_rate = _compute_acf_decay_rate(arr, max_lag=max_lag)
    stationarity_hint = _classify_stationarity_hint(
        acf1=acf1,
        trend_strength=trend_strength,
        seasonal_strength=seasonal_strength,
    )
    return ClassicalStructureResult(
        acf1=acf1,
        acf_decay_rate=acf_decay_rate,
        seasonal_strength=seasonal_strength,
        trend_strength=trend_strength,
        residual_variance_ratio=residual_variance_ratio,
        stationarity_hint=stationarity_hint,
        notes=notes,
    )
