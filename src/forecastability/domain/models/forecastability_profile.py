"""Domain model for forecastability profiles (F1)."""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, ConfigDict


class ForecastabilityProfile(BaseModel):
    """Summarised forecastability profile for a single triage run.

    Captures the AMI curve, threshold-derived informative horizons, and
    actionable decision strings derived from the curve shape.

    Attributes:
        horizons: 1-based lag indices, e.g. ``[1, 2, ..., H]``.
        values: F(h; I_t) for each horizon h — the raw AMI curve.
        epsilon: Threshold used to identify informative horizons.
        informative_horizons: Horizons where ``F(h) >= epsilon``.
        peak_horizon: 1-based lag index at which ``values`` is maximised.
        is_non_monotone: ``True`` when the curve increases at any point after
            the first element.
        summary: One-sentence human-readable profile description.
        model_now: Immediate modeling-decision recommendation.
        review_horizons: Informative horizons that warrant modeling review.
        avoid_horizons: Non-informative horizons to exclude from models.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    horizons: list[int]
    values: np.ndarray
    epsilon: float
    informative_horizons: list[int]
    peak_horizon: int
    is_non_monotone: bool
    summary: str
    model_now: str
    review_horizons: list[int]
    avoid_horizons: list[int]
