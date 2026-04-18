"""Fingerprint summary serialiser — A2 transport boundary (V3_1-F05.1).

Converts :class:`FingerprintAgentPayload` instances to versioned,
envelope-wrapped :class:`SerialisedFingerprintSummary` objects suitable
for JSON transport, MCP, or cross-system agent handoff.

No domain or use-case code is imported at module level; payload models are
plain Pydantic and carry no scientific logic.

Ownership rules (SOLID / hexagonal):
* This module owns A2 transport envelopes and JSON-safe serialisation only.
* It must not recompute fingerprint values, tune thresholds, or re-route families.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

from forecastability.adapters.agents.fingerprint_agent_payload_models import (
    FingerprintAgentPayload,
)

__all__ = [
    "SerialisedFingerprintSummary",
    "serialise_fingerprint_payload",
    "serialise_fingerprint_to_json",
]


class SerialisedFingerprintSummary(BaseModel):
    """Versioned serialisation envelope for a fingerprint agent payload.

    Attributes:
        schema_version: Version of the serialisation envelope format.
        payload_type: Class name of the wrapped payload (always
            ``FingerprintAgentPayload``).
        serialised_at: ISO-8601 UTC timestamp of serialisation.
        payload: ``model_dump()`` of the inner payload; no numpy types.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    payload_type: str
    serialised_at: str
    payload: dict[str, object]


def serialise_fingerprint_payload(
    payload: FingerprintAgentPayload,
) -> SerialisedFingerprintSummary:
    """Wrap a :class:`FingerprintAgentPayload` in a versioned envelope.

    Args:
        payload: An A1 :class:`FingerprintAgentPayload` instance.

    Returns:
        A frozen :class:`SerialisedFingerprintSummary` with schema version,
        payload type, UTC timestamp, and the dumped payload dict.
    """
    raw: dict[str, object] = payload.model_dump()
    return SerialisedFingerprintSummary(
        payload_type=type(payload).__name__,
        serialised_at=datetime.now(UTC).isoformat(),
        payload=raw,
    )


def serialise_fingerprint_to_json(
    payload: FingerprintAgentPayload,
) -> str:
    """Serialise a :class:`FingerprintAgentPayload` to a pretty-printed JSON string.

    Args:
        payload: An A1 :class:`FingerprintAgentPayload` instance.

    Returns:
        A JSON string (``indent=2``) representing the
        :class:`SerialisedFingerprintSummary` envelope.
    """
    summary = serialise_fingerprint_payload(payload)
    return json.dumps(summary.model_dump(), indent=2)
