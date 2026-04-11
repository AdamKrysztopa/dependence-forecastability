"""Triage recommendation logic and exogenous series validation."""

from __future__ import annotations

import numpy as np

from forecastability.validation import validate_time_series

# Family → (high_threshold, medium_threshold)
_TRIAGE_THRESHOLDS: dict[str, tuple[float, float]] = {
    "nonlinear": (0.8, 0.3),
    "linear": (0.5, 0.2),
    "rank": (0.5, 0.2),
    "bounded_nonlinear": (0.5, 0.2),
}


def _triage_recommendation(raw_curve: np.ndarray, *, family: str, is_cross: bool = False) -> str:
    """Generate a triage recommendation from the raw curve mean.

    Args:
        raw_curve: Raw dependence curve array.
        family: Scorer family for threshold lookup.
        is_cross: If ``True``, format recommendation for exogenous series.

    Returns:
        Human-readable recommendation string.
    """
    high, medium = _TRIAGE_THRESHOLDS.get(family, (0.8, 0.3))
    mean_raw = float(np.mean(raw_curve[: min(20, raw_curve.size)]))

    if is_cross:
        if mean_raw > high:
            return "HIGH -> Strongly predictive exogenous (include in Transformers, N-BEATS, etc.)"
        if mean_raw > medium:
            return "MEDIUM -> Useful exogenous (include in ARIMAX/Prophet/LightGBM)"
        return "LOW -> Weak exogenous; drop or test further"

    if mean_raw > high:
        return "HIGH -> Complex global models (Transformers, N-BEATS)"
    if mean_raw > medium:
        return "MEDIUM -> Seasonal ARIMA / Prophet / LightGBM"
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
