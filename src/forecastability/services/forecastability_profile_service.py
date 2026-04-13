"""Application service that builds a ForecastabilityProfile from an AMI curve."""

from __future__ import annotations

import numpy as np

from forecastability.triage.forecastability_profile import ForecastabilityProfile


def _determine_epsilon(
    raw_curve: np.ndarray,
    sig_raw_lags: np.ndarray | None,
    epsilon_param: float | None,
    default_epsilon: float,
) -> float:
    """Resolve the threshold epsilon from surrogate results or fallback params.

    Args:
        raw_curve: Raw AMI curve.
        sig_raw_lags: 0-based indices of significantly active lags, or ``None``
            when surrogates were not computed.
        epsilon_param: Caller-supplied explicit epsilon, or ``None``.
        default_epsilon: Fallback when neither surrogates nor explicit epsilon
            are available.

    Returns:
        Resolved float threshold.
    """
    if sig_raw_lags is not None:
        if len(sig_raw_lags) > 0:
            return float(np.min(raw_curve[sig_raw_lags]))
        max_val = float(np.max(raw_curve)) if raw_curve.size > 0 else 0.0
        return max_val + 1.0
    if epsilon_param is not None:
        return epsilon_param
    return default_epsilon


def _build_model_now(informative_horizons: list[int], peak_value: float) -> str:
    """Derive an immediate modeling recommendation from the profile shape.

    Args:
        informative_horizons: Horizons where forecastability exceeds epsilon.
        peak_value: Maximum value on the AMI curve.

    Returns:
        Human-readable recommendation string.
    """
    n = len(informative_horizons)
    if n > 0 and peak_value > 0.15:
        return f"HIGH — Complex structured models recommended for {n} informative horizon(s)."
    if n > 0 and peak_value > 0.05:
        return (
            "MEDIUM — Moderate forecastability; consider ARIMA/LightGBM for informative horizons."
        )
    if n > 0:
        return "LOW — Weak signal detected; consider naive models."
    return "NONE — No informative horizons detected; naive/seasonal naive recommended."


def build_forecastability_profile(
    raw_curve: np.ndarray,
    *,
    sig_raw_lags: np.ndarray | None = None,
    epsilon: float | None = None,
    default_epsilon: float = 0.05,
) -> ForecastabilityProfile:
    """Build a :class:`ForecastabilityProfile` from a raw AMI curve.

    When ``sig_raw_lags`` is provided, epsilon is derived from the minimum AMI
    value among those significant lags so that all surrogate-significant lags
    are included in ``informative_horizons``.  When no lags are significant,
    ``informative_horizons`` is empty.  When surrogates were not computed,
    ``epsilon`` or ``default_epsilon`` is used as the threshold.

    Args:
        raw_curve: AMI values indexed 0 to H-1 (lag 1 to H).
        sig_raw_lags: 0-based indices of surrogate-significant lags, or
            ``None`` when surrogates were not computed.
        epsilon: Explicit threshold override, used only when ``sig_raw_lags``
            is ``None``.
        default_epsilon: Fallback threshold when neither ``sig_raw_lags`` nor
            ``epsilon`` are supplied.

    Returns:
        A frozen :class:`ForecastabilityProfile` instance.
    """
    if raw_curve.size == 0:
        horizons: list[int] = []
        resolved_epsilon = default_epsilon if epsilon is None else epsilon
        return ForecastabilityProfile(
            horizons=horizons,
            values=raw_curve,
            epsilon=resolved_epsilon,
            informative_horizons=[],
            peak_horizon=0,
            is_non_monotone=False,
            summary="No data — empty curve provided.",
            model_now="NONE — No informative horizons detected; naive/seasonal naive recommended.",
            review_horizons=[],
            avoid_horizons=[],
        )

    horizons = list(range(1, len(raw_curve) + 1))
    resolved_epsilon = _determine_epsilon(raw_curve, sig_raw_lags, epsilon, default_epsilon)

    informative_horizons = sorted(
        {h for h, v in zip(horizons, raw_curve, strict=True) if v >= resolved_epsilon}
    )
    peak_horizon = horizons[int(np.argmax(raw_curve))]

    is_non_monotone = any(raw_curve[i] > raw_curve[i - 1] for i in range(1, len(raw_curve)))

    n_informative = len(informative_horizons)
    summary = (
        f"Peak forecastability at horizon {peak_horizon}, "
        f"{n_informative} informative horizon(s) identified."
    )
    peak_value = float(np.max(raw_curve))
    model_now = _build_model_now(informative_horizons, peak_value)

    informative_set = set(informative_horizons)
    avoid_horizons = [h for h in horizons if h not in informative_set]

    return ForecastabilityProfile(
        horizons=horizons,
        values=raw_curve,
        epsilon=resolved_epsilon,
        informative_horizons=informative_horizons,
        peak_horizon=peak_horizon,
        is_non_monotone=is_non_monotone,
        summary=summary,
        model_now=model_now,
        review_horizons=informative_horizons,
        avoid_horizons=avoid_horizons,
    )
