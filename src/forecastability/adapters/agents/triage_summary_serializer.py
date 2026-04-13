"""Triage summary serialiser — agent adapter serialisation boundary.

Converts any A1 payload model instance to a versioned, envelope-wrapped
``SerialisedTriageSummary``.  No domain or use-case code is imported at
module level; payload models are plain Pydantic and carry no scientific logic.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from forecastability.adapters.agents.triage_agent_payload_models import (
    F1ProfilePayload,
    F2LimitsPayload,
    F3LearningCurvePayload,
    F4SpectralPayload,
    F5LyapunovPayload,
    F6ComplexityPayload,
    F7BatchRankPayload,
    F8ExogDriverPayload,
    TriageAgentPayload,
)

__all__ = [
    "SerialisedTriageSummary",
    "serialise_payload",
    "serialise_batch",
    "serialise_to_json",
    "serialise_batch_to_json",
]

# Union of all valid A1 payload types — used for internal dispatch.
_AnyPayload = (
    TriageAgentPayload
    | F1ProfilePayload
    | F2LimitsPayload
    | F3LearningCurvePayload
    | F4SpectralPayload
    | F5LyapunovPayload
    | F6ComplexityPayload
    | F7BatchRankPayload
    | F8ExogDriverPayload
)


class SerialisedTriageSummary(BaseModel):
    """Versioned serialisation envelope for a single triage payload.

    Attributes:
        schema_version: Version of the serialisation envelope format.
        payload_type: Class name of the wrapped payload model.
        serialised_at: ISO-8601 UTC timestamp of serialisation.
        payload: ``model_dump()`` of the inner payload; no numpy types.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    payload_type: str
    serialised_at: str
    payload: dict[str, object]


def serialise_payload(
    payload: Any,  # noqa: ANN401 — intentional: accepts any A1 payload duck-type
) -> SerialisedTriageSummary:
    """Wrap a single A1 payload model in a ``SerialisedTriageSummary`` envelope.

    Args:
        payload: Any instance of an A1 payload model
            (``TriageAgentPayload``, ``F1ProfilePayload``, …, ``F8ExogDriverPayload``).

    Returns:
        A frozen ``SerialisedTriageSummary`` with schema version, payload type,
        UTC timestamp, and the dumped payload dict.
    """
    raw: dict[str, object] = payload.model_dump()
    return SerialisedTriageSummary(
        payload_type=type(payload).__name__,
        serialised_at=datetime.now(UTC).isoformat(),
        payload=raw,
    )


def serialise_batch(
    payloads: Sequence[Any],  # noqa: ANN401 — sequence of heterogeneous A1 payloads
) -> list[SerialisedTriageSummary]:
    """Serialise a sequence of A1 payload models to ``SerialisedTriageSummary`` objects.

    Args:
        payloads: A sequence where each element is an A1 payload model instance.

    Returns:
        A list of ``SerialisedTriageSummary`` objects in the same order as the input.
    """
    return [serialise_payload(p) for p in payloads]


def serialise_to_json(
    payload: Any,  # noqa: ANN401 — accepts any A1 payload duck-type
) -> str:
    """Serialise a single A1 payload model to a pretty-printed JSON string.

    Args:
        payload: Any instance of an A1 payload model.

    Returns:
        A JSON string (``indent=2``) representing the ``SerialisedTriageSummary`` envelope.
    """
    summary = serialise_payload(payload)
    return json.dumps(summary.model_dump(), indent=2)


def serialise_batch_to_json(
    payloads: Sequence[Any],  # noqa: ANN401 — sequence of heterogeneous A1 payloads
) -> str:
    """Serialise a sequence of A1 payload models to a pretty-printed JSON array string.

    Args:
        payloads: A sequence where each element is an A1 payload model instance.

    Returns:
        A JSON string (``indent=2``) containing a list of serialised summary dicts.
    """
    summaries = serialise_batch(payloads)
    return json.dumps([s.model_dump() for s in summaries], indent=2)
