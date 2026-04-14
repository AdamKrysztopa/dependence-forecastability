"""Triage recommendation logic and exogenous series validation."""

from __future__ import annotations

import numpy as np

from forecastability.utils.validation import validate_time_series

# Family → (high_threshold, medium_threshold) — peak-based, calibrated on
# canonical examples (WN ≈ 0.02, AR(1) ≈ 0.38, Logistic/Sine/Hénon ≥ 1.1).
_TRIAGE_THRESHOLDS: dict[str, tuple[float, float]] = {
    "nonlinear": (0.15, 0.05),
    "linear": (0.15, 0.05),
    "rank": (0.15, 0.05),
    "bounded_nonlinear": (0.15, 0.05),
}


def _triage_recommendation(raw_curve: np.ndarray, *, family: str, is_cross: bool = False) -> str:
    """Generate a triage recommendation from the raw curve peak.

    Uses the peak (maximum) of the raw dependence curve with thresholds
    aligned to :func:`forecastability.reporting.interpretation._forecastability_class`.

    Args:
        raw_curve: Raw dependence curve array.
        family: Scorer family for threshold lookup.
        is_cross: If ``True``, format recommendation for exogenous series.

    Returns:
        Human-readable recommendation string.
    """
    high, medium = _TRIAGE_THRESHOLDS.get(family, (0.15, 0.05))
    peak_raw = float(np.max(raw_curve))

    if is_cross:
        if peak_raw > high:
            return "HIGH -> Strongly predictive exogenous (include in ARIMAX/LightGBM)"
        if peak_raw > medium:
            return "MEDIUM -> Useful exogenous signal; include and validate"
        return "LOW -> Weak exogenous; drop or test further"

    if peak_raw > high:
        return "HIGH -> Complex structured models (deep AR, nonlinear, LSTM)"
    if peak_raw > medium:
        return "MEDIUM -> Seasonal ARIMA / LightGBM"
    return "LOW -> Naive or seasonal naive only"


def _validate_exog_for_target(exog: np.ndarray | None, *, target: np.ndarray) -> np.ndarray | None:
    """Validate optional exogenous series and enforce an exact length match.

    Args:
        exog: Optional exogenous array to validate.
        target: Target series whose length must be matched.

    Returns:
        Validated exogenous array or ``None``.

    Raises:
        ValueError: If *exog* length does not match *target* length.
    """
    if exog is None:
        return None
    validated = validate_time_series(exog, min_length=target.size)
    if validated.size != target.size:
        raise ValueError(
            f"exog length ({validated.size}) must exactly match target length ({target.size})"
        )
    return validated
