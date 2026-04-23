"""Routing-validation summary serialiser — transport envelope for agent payloads.

Wraps :class:`RoutingValidationAgentPayload` in a frozen versioned envelope so
the deterministic routing-validation review can be handed to external tools or
optional LLM adapters without recomputing any scientific or policy fields.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

from forecastability.adapters.agents.routing_validation_agent_payload_models import (
    RoutingValidationAgentPayload,
)

__all__ = [
    "SerialisedRoutingValidationSummary",
    "serialise_routing_validation_payload",
    "serialise_routing_validation_to_json",
]


class SerialisedRoutingValidationSummary(BaseModel):
    """Versioned envelope for a routing-validation agent payload.

    Attributes:
        schema_version: Envelope schema version.
        payload_type: Wrapped payload class name.
        serialised_at: ISO-8601 UTC timestamp of serialisation.
        payload: Dumped deterministic payload.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    payload_type: str
    serialised_at: str
    payload: dict[str, object]


def serialise_routing_validation_payload(
    payload: RoutingValidationAgentPayload,
) -> SerialisedRoutingValidationSummary:
    """Wrap a routing-validation payload in a versioned envelope.

    Args:
        payload: Deterministic routing-validation agent payload.

    Returns:
        Frozen serialised envelope.
    """
    return SerialisedRoutingValidationSummary(
        payload_type=type(payload).__name__,
        serialised_at=datetime.now(UTC).isoformat(),
        payload=payload.model_dump(),
    )


def serialise_routing_validation_to_json(
    payload: RoutingValidationAgentPayload,
) -> str:
    """Serialise a routing-validation payload to pretty-printed JSON.

    Args:
        payload: Deterministic routing-validation agent payload.

    Returns:
        JSON string representing the serialised envelope.
    """
    summary = serialise_routing_validation_payload(payload)
    return json.dumps(summary.model_dump(), indent=2)
