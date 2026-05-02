"""Port interfaces for the AMI → pAMI forecastability package.

Each port is a narrow, runtime-checkable Protocol (ISP).  Concrete adapters
and services implement these ports without importing from this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import numpy as np

from forecastability.metrics.scorers import DependenceScorer, ScorerInfo
from forecastability.ports.kernels import (
    KernelProvider,
    KernelProviderError,
    KernelProviderMetadata,
    Ksg2ProfileKernel,
    LagDesignKernel,
    LinearResidualizeKernel,
    PhaseSurrogateKernel,
    load_kernel_provider,
)
from forecastability.triage.events import TriageEvent
from forecastability.utils.types import (
    CanonicalExampleResult,
    CausalGraphResult,
    InterpretationResult,
    PcmciAmiResult,
)

__all__ = [
    "CausalGraphFullPort",
    "CausalGraphPort",
    "CheckpointPort",
    "CurveComputePort",
    "EventEmitterPort",
    "InterpretationPort",
    "KernelProvider",
    "KernelProviderError",
    "KernelProviderMetadata",
    "Ksg2ProfileKernel",
    "LagDesignKernel",
    "LinearResidualizeKernel",
    "PhaseSurrogateKernel",
    "RecommendationPort",
    "ReportRendererPort",
    "SeriesValidatorPort",
    "SettingsPort",
    "SignificanceBandsPort",
    "load_kernel_provider",
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


@runtime_checkable
class EventEmitterPort(Protocol):
    """Emits triage pipeline progress events (AGT-012).

    Implementations may log, stream SSE, publish to a queue, or no-op.
    """

    def emit(self, event: TriageEvent) -> None: ...


@runtime_checkable
class CheckpointPort(Protocol):
    """Persists and restores partial triage state for durable execution (AGT-014).

    Each triage run is identified by a ``checkpoint_key`` string.  Adapters
    may use the filesystem, a database, or an in-memory store.
    """

    def load_checkpoint(self, checkpoint_key: str) -> dict[str, Any] | None:
        """Return the saved state dict for *checkpoint_key*, or ``None``."""
        ...

    def save_checkpoint(
        self,
        checkpoint_key: str,
        stage: str,
        state: dict[str, Any],
    ) -> None:
        """Overwrite the checkpoint for *checkpoint_key* with *state*."""
        ...


@runtime_checkable
class CausalGraphPort(Protocol):
    """Port for methods that return a causal graph (PCMCI+, PCMCI-AMI).

    Implementations must not import from adapters — only from ports and domain.
    """

    def discover(
        self,
        data: np.ndarray,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> CausalGraphResult: ...


@runtime_checkable
class CausalGraphFullPort(Protocol):
    """Extended causal-discovery port for adapters that also expose ``discover_full``.

    Any adapter satisfying this port satisfies ``CausalGraphPort`` structurally
    (it has both ``discover`` and ``discover_full``).  Declared as a flat Protocol
    rather than a ``CausalGraphPort`` subclass to avoid ``isinstance`` hazards with
    multi-level ``@runtime_checkable`` Protocols on Python < 3.12.
    """

    def discover(
        self,
        data: np.ndarray,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> CausalGraphResult: ...

    def discover_full(
        self,
        data: np.ndarray,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> PcmciAmiResult: ...
