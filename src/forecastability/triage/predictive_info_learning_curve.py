"""Domain model for F3 — Predictive Information Learning Curves."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PredictiveInfoLearningCurve(BaseModel):
    """Result of a predictive-information learning-curve analysis.

    Attributes:
        window_sizes: Window (lookback) sizes evaluated, k=1..K.
        information_values: I_pred(k) for each window size.
        convergence_index: Index (0-based) within window_sizes where plateau
            begins; -1 if no plateau.
        recommended_lookback: Recommended lookback length from plateau
            detection.
        plateau_detected: True when a plateau was found.
        reliability_warnings: List of reliability warning strings (may be
            empty).
    """

    model_config = ConfigDict(frozen=True)

    window_sizes: list[int]
    information_values: list[float]
    convergence_index: int
    recommended_lookback: int
    plateau_detected: bool
    reliability_warnings: list[str]
