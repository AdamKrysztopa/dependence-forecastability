"""Internal response types for agent-ready seams.

These are NOT part of the public API and are not exported from the package.
They exist as internal contracts for future agent integration.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from forecastability.pipeline.analyzer import AnalyzeResult
from forecastability.utils.types import SeriesEvaluationResult


class AnalyzeSeriesResponse(BaseModel):
    """Response from the analyze-one-series use case."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    result: AnalyzeResult


class RollingOriginResponse(BaseModel):
    """Response from the rolling-origin benchmark use case."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    result: SeriesEvaluationResult


class ExogenousRollingOriginResponse(BaseModel):
    """Response from the exogenous rolling-origin benchmark use case."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    result: SeriesEvaluationResult
