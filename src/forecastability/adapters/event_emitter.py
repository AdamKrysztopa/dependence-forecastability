"""Concrete EventEmitterPort adapters (AGT-012, AGT-024).

Adapters are confined to this module; domain and use-case code depend only
on :class:`~forecastability.ports.EventEmitterPort`.
"""

from __future__ import annotations

import json
import logging
import queue
from collections.abc import Generator

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


class StreamingEventEmitter:
    """Event emitter that encodes events as Server-Sent Events (SSE) bytes.

    Designed for the ``GET /triage/stream`` FastAPI endpoint (AGT-024).  A
    background thread executes ``run_triage()`` while the HTTP response
    generator pulls SSE-encoded events from an internal queue.

    Each event is encoded as::

        data: {\"event_type\": \"...\", ...}\\n\\n

    A sentinel ``data: {\"event_type\": \"done\"}\\n\\n`` is emitted after all
    stages complete (or after the first error).

    Usage inside a FastAPI streaming response::

        emitter = StreamingEventEmitter()
        # launch triage in a background thread
        thread = threading.Thread(target=run_triage, args=(request,),
                                  kwargs={\"event_emitter\": emitter})
        thread.start()
        # yield SSE chunks from the emitter
        for chunk in emitter.sse_stream():
            yield chunk
        thread.join()

    Attributes:
        _q: Internal thread-safe queue.
        _SENTINEL: Unique object that signals end-of-stream.
    """

    _SENTINEL: object = object()

    def __init__(self) -> None:
        self._q: queue.Queue[object] = queue.Queue()

    def emit(self, event: TriageEvent) -> None:
        """Enqueue *event* for SSE delivery."""
        self._q.put(event)

    def close(self) -> None:
        """Signal that no further events will be emitted."""
        self._q.put(self._SENTINEL)

    @staticmethod
    def _encode_event(event: TriageEvent) -> str:
        """Convert a :class:`TriageEvent` to an SSE ``data:`` line.

        Args:
            event: Event to serialise.

        Returns:
            SSE-formatted string ending in ``\\n\\n``.
        """
        if isinstance(event, TriageStageStarted):
            payload = {
                "event_type": "stage_started",
                "stage": event.stage,
                "timestamp": event.timestamp.isoformat(),
            }
        elif isinstance(event, TriageStageCompleted):
            payload = {
                "event_type": "stage_completed",
                "stage": event.stage,
                "duration_ms": event.duration_ms,
                "result_summary": event.result_summary,
            }
        elif isinstance(event, TriageError):
            payload = {
                "event_type": "stage_error",
                "stage": event.stage,
                "error": event.error,
            }
        else:  # pragma: no cover
            payload = {"event_type": "unknown"}
        return f"data: {json.dumps(payload)}\n\n"

    def sse_stream(self, timeout: float = 120.0) -> Generator[str, None, None]:
        """Yield SSE-encoded strings until the sentinel is received.

        Args:
            timeout: Maximum seconds to wait for each event before raising
                :class:`TimeoutError`.  Defaults to 120 seconds.

        Yields:
            SSE-formatted strings (``data: {...}\\n\\n``).

        Raises:
            TimeoutError: When no event arrives within *timeout* seconds.
        """
        while True:
            try:
                item = self._q.get(timeout=timeout)
            except queue.Empty as exc:
                raise TimeoutError(
                    f"StreamingEventEmitter: no event received within {timeout}s"
                ) from exc
            if item is self._SENTINEL:
                yield 'data: {"event_type": "done"}\n\n'
                return
            yield self._encode_event(item)  # type: ignore[arg-type]
