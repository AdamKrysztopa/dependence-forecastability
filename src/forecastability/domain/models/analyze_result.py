"""Domain result container for forecastability analysis output."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class AnalyzeResult:
    """Container returned by ``ForecastabilityAnalyzer.analyze``.

    Attributes:
        raw: Raw dependence curve (AMI when method is ``"mi"``).
        partial: Partial dependence curve (pAMI when method is ``"mi"``).
        sig_raw_lags: Lag indices where raw exceeds the upper surrogate band.
        sig_partial_lags: Lag indices where partial exceeds the upper band.
        recommendation: Human-readable triage recommendation.
        method: Name of the scorer used.
    """

    raw: np.ndarray
    partial: np.ndarray
    sig_raw_lags: np.ndarray
    sig_partial_lags: np.ndarray
    recommendation: str
    method: str
