"""Typed event models for triage pipeline observability (AGT-012).

All models are pure-domain Pydantic types — no framework imports.
Adapters consume these events via :class:`EventEmitterPort`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class TriageStageStarted(BaseModel):
    """Emitted when a triage pipeline stage begins execution.

    Attributes:
        stage: Human-readable stage identifier (e.g. ``"readiness"``,
            ``"routing"``, ``"compute"``, ``"interpretation"``).
        timestamp: UTC wall-clock time at stage entry.
    """

    model_config = ConfigDict(frozen=True)

    stage: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC)
    )


class TriageStageCompleted(BaseModel):
    """Emitted when a triage pipeline stage finishes successfully.

    Attributes:
        stage: Stage identifier matching the corresponding
            :class:`TriageStageStarted` event.
        duration_ms: Wall-clock elapsed time in milliseconds.
        result_summary: Brief human-readable summary of the stage outcome.
    """

    model_config = ConfigDict(frozen=True)

    stage: str
    duration_ms: float
    result_summary: str


class TriageError(BaseModel):
    """Emitted when a triage pipeline stage raises an exception.

    Attributes:
        stage: Stage identifier where the error occurred.
        error: String representation of the exception.
    """

    model_config = ConfigDict(frozen=True)

    stage: str
    error: str


TriageEvent = Annotated[
    TriageStageStarted | TriageStageCompleted | TriageError,
    Field(discriminator=None),
]
