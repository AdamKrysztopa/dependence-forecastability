"""Frozen Pydantic result models for screening agent tool returns.

Each model maps 1-to-1 to the dict keys previously returned by the
corresponding ``@agent.tool`` function in
:mod:`forecastability.adapters.agents.runtime.screening_agent`.

No new fields are added; semantics are unchanged.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = [
    "CandidateStatsResult",
    "TargetAssessmentResult",
    "FeatureScreenResult",
    "UnknownFeatureResult",
]


class CandidateStatsResult(BaseModel):
    """Stats for a single candidate feature returned by ``list_candidates``.

    Attributes:
        n: Length of the candidate array.
        mean: Sample mean of the candidate array.
        std: Sample standard deviation of the candidate array.
    """

    model_config = ConfigDict(frozen=True)

    n: int
    mean: float
    std: float


class TargetAssessmentResult(BaseModel):
    """Result returned by the ``assess_target`` tool.

    Attributes:
        blocked: Whether the readiness gate blocked execution.
        peak_raw: Peak raw AMI value (absent when blocked).
        peak_partial: Peak partial AMI value (absent when not computed).
        forecastability: Forecastability class label (absent when blocked).
        directness: Directness class label (absent when blocked).
        regime: Modeling regime label (absent when blocked).
        narrative: Deterministic narrative fragment (absent when blocked).
        recommendation: Triage recommendation string.
    """

    model_config = ConfigDict(frozen=True)

    blocked: bool
    peak_raw: float | None = None
    peak_partial: float | None = None
    forecastability: str | None = None
    directness: str | None = None
    regime: str | None = None
    narrative: str | None = None
    recommendation: str | None = None


class UnknownFeatureResult(BaseModel):
    """Error result returned by ``screen_feature`` for an unknown feature name.

    Attributes:
        error: Human-readable error message.
    """

    model_config = ConfigDict(frozen=True)

    error: str


class FeatureScreenResult(BaseModel):
    """Result returned by the ``screen_feature`` tool for a known feature.

    Attributes:
        feature: Feature name.
        blocked: Whether the readiness gate blocked execution.
        peak_raw: Peak raw CrossAMI value (absent when blocked).
        peak_partial: Peak partial CrossAMI value (absent when not computed).
        forecastability: Forecastability class label (absent when blocked).
        directness: Directness class label (absent when blocked).
        regime: Modeling regime label (absent when blocked).
        narrative: Deterministic narrative fragment (absent when blocked).
        recommendation: Triage recommendation string.
    """

    model_config = ConfigDict(frozen=True)

    feature: str
    blocked: bool
    peak_raw: float | None = None
    peak_partial: float | None = None
    forecastability: str | None = None
    directness: str | None = None
    regime: str | None = None
    narrative: str | None = None
    recommendation: str | None = None
