"""Concrete EventEmitterPort adapters (AGT-012).

Adapters are confined to this module; domain and use-case code depend only
on :class:`~forecastability.ports.EventEmitterPort`.
"""

from __future__ import annotations

import logging

from forecastability.triage.events import (
    TriageError,
    TriageEvent,
    TriageStageCompleted,
    TriageStageStarted,
)


class NoopEventEmitter:
    """Event emitter that silently discards all events.

    Use when observability is not required (default in tests and lightweight
    scripts).
    """

    def emit(self, event: TriageEvent) -> None:  # noqa: ARG002
        """Discard *event* without side effects."""


class LoggingEventEmitter:
    """Event emitter that writes structured log records via the stdlib logger.

    Args:
        logger_name: Logger name used for all emitted records.  Defaults to
            ``"forecastability.triage"`` so callers can configure it
            independently.
    """

    def __init__(self, logger_name: str = "forecastability.triage") -> None:
        self._logger = logging.getLogger(logger_name)

    def emit(self, event: TriageEvent) -> None:
        """Write a log record for *event* at the appropriate level.

        - :class:`~forecastability.triage.events.TriageStageStarted` → ``DEBUG``
        - :class:`~forecastability.triage.events.TriageStageCompleted` → ``INFO``
        - :class:`~forecastability.triage.events.TriageError` → ``ERROR``
        """
        if isinstance(event, TriageStageStarted):
            self._logger.debug(
                "stage_started",
                extra={"stage": event.stage, "timestamp": event.timestamp.isoformat()},
            )
        elif isinstance(event, TriageStageCompleted):
            self._logger.info(
                "stage_completed  stage=%s  duration_ms=%.1f  summary=%s",
                event.stage,
                event.duration_ms,
                event.result_summary,
            )
        elif isinstance(event, TriageError):
            self._logger.error(
                "stage_error  stage=%s  error=%s",
                event.stage,
                event.error,
            )


class CollectingEventEmitter:
    """Event emitter that accumulates events in-memory for inspection.

    Primarily useful in tests and notebooks where callers want to assert
    that specific stages fired.

    Attributes:
        events: Ordered list of all emitted events.
    """

    def __init__(self) -> None:
        self.events: list[TriageEvent] = []

    def emit(self, event: TriageEvent) -> None:
        """Append *event* to :attr:`events`."""
        self.events.append(event)
