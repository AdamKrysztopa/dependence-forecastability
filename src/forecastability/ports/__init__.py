"""Port interfaces for the AMI → pAMI forecastability package.

Each port is a narrow, runtime-checkable Protocol (ISP).  Concrete adapters
and services implement these ports without importing from this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from forecastability.scorers import DependenceScorer, ScorerInfo
from forecastability.types import CanonicalExampleResult, InterpretationResult

__all__ = [
    "SeriesValidatorPort",
    "CurveComputePort",
    "SignificanceBandsPort",
    "InterpretationPort",
    "RecommendationPort",
    "ReportRendererPort",
    "SettingsPort",
]


@runtime_checkable
class SeriesValidatorPort(Protocol):
    """Validates a raw time-series array before analysis."""

    def __call__(self, ts: np.ndarray, *, min_length: int) -> np.ndarray: ...


@runtime_checkable
class CurveComputePort(Protocol):
    """Computes an AMI or pAMI curve for a single series."""

    def __call__(
        self,
        series: np.ndarray,
        max_lag: int,
        scorer: DependenceScorer,
        *,
        exog: np.ndarray | None,
        min_pairs: int,
        random_state: int,
    ) -> np.ndarray: ...


@runtime_checkable
class SignificanceBandsPort(Protocol):
    """Computes surrogate-based significance bands for a curve."""

    def __call__(
        self,
        series: np.ndarray,
        n_surrogates: int,
        random_state: int,
        max_lag: int,
        info: ScorerInfo,
        which: str,
        *,
        exog: np.ndarray | None,
        min_pairs: int,
        n_jobs: int,
    ) -> tuple[np.ndarray, np.ndarray]: ...


@runtime_checkable
class InterpretationPort(Protocol):
    """Interprets a completed canonical example result."""

    def __call__(
        self,
        result: CanonicalExampleResult,
        *,
        best_smape: float | None,
    ) -> InterpretationResult: ...


@runtime_checkable
class RecommendationPort(Protocol):
    """Returns a triage recommendation string from a raw curve."""

    def __call__(
        self,
        raw_curve: np.ndarray,
        *,
        family: str,
        is_cross: bool,
    ) -> str: ...


@runtime_checkable
class ReportRendererPort(Protocol):
    """Renders and persists canonical example reports."""

    def render_markdown(self, result: CanonicalExampleResult) -> str: ...

    def save_json(self, result: CanonicalExampleResult, *, output_path: Path) -> None: ...


@runtime_checkable
class SettingsPort(Protocol):
    """Runtime infrastructure configuration."""

    def get_context7_api_key(self) -> str | None: ...

    def get_openai_api_key(self) -> str | None: ...

    def get_openai_model(self) -> str: ...

    def get_anthropic_api_key(self) -> str | None: ...

    def get_anthropic_model(self) -> str: ...

    def get_xai_api_key(self) -> str | None: ...

    def get_xai_model(self) -> str: ...

    def get_triage_enable_streaming(self) -> bool: ...

    def get_triage_default_significance_mode(self) -> str: ...

    def get_mcp_host(self) -> str: ...

    def get_mcp_port(self) -> int: ...
