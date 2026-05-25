"""Backward-compatible re-export shim (RVH-F11).

Routing validation agent payload models have moved to
:mod:`forecastability.adapters.agents.payloads.routing_validation_agent_payload_models`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.agents.routing_validation_agent_payload_models is deprecated. "
    "Import from "
    "forecastability.adapters.agents.payloads.routing_validation_agent_payload_models instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.payloads.routing_validation_agent_payload_models import (  # noqa: E402, F401
    RoutingValidationAgentPayload,
    routing_validation_agent_payload,
)

__all__ = [
    "RoutingValidationAgentPayload",
    "routing_validation_agent_payload",
]
