"""Backward-compatible re-export shim (RVH-F11).

The routing-validation agent has moved to
:mod:`forecastability.adapters.agents.runtime.routing_validation_agent`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.llm.routing_validation_agent is deprecated. "
    "Import from forecastability.adapters.agents.runtime.routing_validation_agent instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.runtime.routing_validation_agent import (  # noqa: E402, F401
    RoutingValidationDeps,
    RoutingValidationExplanation,
    RoutingValidationNarrative,
    create_routing_validation_agent,
    pydantic_ai_available,
    run_routing_validation_agent,
)

__all__ = [
    "RoutingValidationDeps",
    "RoutingValidationExplanation",
    "RoutingValidationNarrative",
    "create_routing_validation_agent",
    "pydantic_ai_available",
    "run_routing_validation_agent",
]
