"""Backward-compatible re-export shim (RVH-F11).

Routing validation summary serializer has moved to
:mod:`forecastability.adapters.agents.payloads.routing_validation_summary_serializer`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.agents.routing_validation_summary_serializer is deprecated. "
    "Import from "
    "forecastability.adapters.agents.payloads.routing_validation_summary_serializer instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.payloads.routing_validation_summary_serializer import (  # noqa: E402, F401
    SerialisedRoutingValidationSummary,
    serialise_routing_validation_payload,
    serialise_routing_validation_to_json,
)

__all__ = [
    "SerialisedRoutingValidationSummary",
    "serialise_routing_validation_payload",
    "serialise_routing_validation_to_json",
]
