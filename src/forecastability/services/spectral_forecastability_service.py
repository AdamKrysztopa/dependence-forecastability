"""Deterministic spectral forecastability summaries for the extended fingerprint."""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike

from forecastability.diagnostics.spectral_utils import compute_normalised_psd, spectral_entropy
from forecastability.services._extended_diagnostic_validation import (
    SpectralDetrendMode,
    coerce_univariate_values,
    validate_positive_argument,
    validate_spectral_detrend,
)
from forecastability.triage.extended_forecastability import SpectralForecastabilityResult

_MIN_SPECTRAL_LENGTH = 8
_SHORT_SERIES_NOTE = "series is too short for a stable spectral summary"
_CONSTANT_SERIES_NOTE = "constant series; returning a conservative degenerate spectral summary"
_SAMPLING_NOTE = (
    "dominant periods are reported in sample counts because no sampling interval was supplied"
)
_LOW_FREQUENCY_NOTE = (
    "low-frequency spectral concentration may reflect trend rather than stable periodic structure"
)


def _conservative_result(note: str) -> SpectralForecastabilityResult:
    """Return a conservative spectral result for degenerate inputs."""
    return SpectralForecastabilityResult(
        spectral_entropy=1.0,
        spectral_predictability=0.0,
        dominant_periods=[],
        spectral_concentration=0.0,
        periodicity_hint="none",
        notes=[note],
    )


def _compute_spectral_concentration(probabilities: np.ndarray) -> float:
    """Summarize how concentrated the positive-frequency spectrum is."""
    n_bins = probabilities.size
    if n_bins <= 1:
        return 0.0
    peak_mass = float(np.max(probabilities))
    baseline = 1.0 / float(n_bins)
    concentration = (peak_mass - baseline) / max(1.0 - baseline, 1e-12)
    return float(np.clip(concentration, 0.0, 1.0))


def _extract_dominant_periods(
    frequencies: np.ndarray,
    probabilities: np.ndarray,
    *,
    max_periods: int,
) -> list[int]:
    """Extract unique dominant periods ordered by descending spectral power."""
    dominant_periods: list[int] = []
    for index in np.argsort(probabilities)[::-1]:
        frequency = float(frequencies[index])
        if frequency <= 0.0:
            continue
        period = int(np.rint(1.0 / frequency))
        if period <= 1 or period in dominant_periods:
            continue
        dominant_periods.append(period)
        if len(dominant_periods) >= max_periods:
            break
    return dominant_periods


def _classify_periodicity_hint(
    *,
    spectral_predictability: float,
    spectral_concentration: float,
) -> Literal["none", "weak", "moderate", "strong"]:
    """Map bounded spectral summaries to a periodicity hint."""
    score = 0.6 * spectral_predictability + 0.4 * spectral_concentration
    if score >= 0.75:
        return "strong"
    if score >= 0.55:
        return "moderate"
    if score >= 0.35:
        return "weak"
    return "none"


def _downgrade_hint(
    hint: Literal["none", "weak", "moderate", "strong"],
) -> Literal["none", "weak", "moderate", "strong"]:
    """Downgrade a periodicity hint when low-frequency ambiguity is present."""
    if hint == "strong":
        return "moderate"
    if hint == "moderate":
        return "weak"
    return hint


def _resolve_detrend(detrend: SpectralDetrendMode) -> str | bool:
    """Translate the public detrend mode into the Welch-compatible argument."""
    if detrend == "none":
        return False
    return detrend


def compute_spectral_forecastability(
    values: ArrayLike,
    *,
    max_periods: int = 5,
    detrend: SpectralDetrendMode = "linear",
    eps: float = 1e-12,
) -> SpectralForecastabilityResult:
    """Compute normalized spectral forecastability diagnostics.

    Args:
        values: Univariate series values to analyze.
        max_periods: Maximum number of dominant periods to report.
        detrend: Deterministic detrending mode for the spectral path.
        eps: Small numerical floor for safe normalization.

    Returns:
        Spectral forecastability summary with bounded entropy and concentration.
    """
    arr = coerce_univariate_values(values)
    validate_positive_argument(max_periods, name="max_periods")
    detrend_mode = validate_spectral_detrend(detrend)
    if arr.size < _MIN_SPECTRAL_LENGTH:
        return _conservative_result(_SHORT_SERIES_NOTE)
    if float(np.ptp(arr)) <= eps:
        return _conservative_result(_CONSTANT_SERIES_NOTE)

    frequencies, probabilities = compute_normalised_psd(
        arr,
        nperseg=arr.size,
        detrend=_resolve_detrend(detrend_mode),
    )
    positive_mask = frequencies > 0.0
    positive_frequencies = frequencies[positive_mask]
    positive_probabilities = probabilities[positive_mask]
    if positive_probabilities.size <= 1:
        return _conservative_result(_SHORT_SERIES_NOTE)

    positive_probabilities = np.clip(positive_probabilities, a_min=eps, a_max=None)
    positive_probabilities = positive_probabilities / positive_probabilities.sum()

    normalized_entropy = spectral_entropy(positive_probabilities) / max(
        math.log(float(positive_probabilities.size)),
        eps,
    )
    spectral_entropy_score = float(np.clip(normalized_entropy, 0.0, 1.0))
    spectral_predictability = float(np.clip(1.0 - spectral_entropy_score, 0.0, 1.0))
    spectral_concentration = _compute_spectral_concentration(positive_probabilities)

    periodicity_hint = _classify_periodicity_hint(
        spectral_predictability=spectral_predictability,
        spectral_concentration=spectral_concentration,
    )
    dominant_periods = _extract_dominant_periods(
        positive_frequencies,
        positive_probabilities,
        max_periods=max_periods,
    )

    notes: list[str] = []
    dominant_frequency = float(positive_frequencies[int(np.argmax(positive_probabilities))])
    low_frequency_threshold = 1.0 / max(float(arr.size) / 3.0, 2.0)
    if dominant_frequency <= low_frequency_threshold and spectral_predictability >= 0.45:
        notes.append(_LOW_FREQUENCY_NOTE)
        periodicity_hint = _downgrade_hint(periodicity_hint)
    if dominant_periods and periodicity_hint != "none":
        notes.append(_SAMPLING_NOTE)

    return SpectralForecastabilityResult(
        spectral_entropy=spectral_entropy_score,
        spectral_predictability=spectral_predictability,
        dominant_periods=dominant_periods,
        spectral_concentration=spectral_concentration,
        periodicity_hint=periodicity_hint,
        notes=notes,
    )
