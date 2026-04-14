"""Internal request types for agent-ready seams.

These are NOT part of the public API and are not exported from the package.
They exist as internal contracts for future agent integration.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from forecastability.utils.config import RollingOriginConfig


class AnalyzeSeriesRequest(BaseModel):
    """Request for analysing a single series (analyze-one-series use case)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    series: np.ndarray
    max_lag: int = 100
    method: str = "mi"
    compute_surrogates: bool = False
    random_state: int = 42
    n_surrogates: int = Field(default=99, ge=99)


class RollingOriginRequest(BaseModel):
    """Request for the rolling-origin benchmark use case."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    series: np.ndarray
    config: RollingOriginConfig
    random_state: int = 42
    n_jobs: int = -1


class ExogenousRollingOriginRequest(BaseModel):
    """Request for the exogenous rolling-origin benchmark use case."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    target: np.ndarray
    exog: np.ndarray
    config: RollingOriginConfig
    random_state: int = 42
    n_jobs: int = -1


class ReportPayloadRequest(BaseModel):
    """Request for report payload generation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    series_name: str
    series: np.ndarray
    config: RollingOriginConfig
