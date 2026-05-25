"""Backward-compatible re-export shim (RVH-F11).

Covariant agent payload models have moved to
:mod:`forecastability.adapters.agents.payloads.covariant_agent_payload_models`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.agents.covariant_agent_payload_models is deprecated. "
    "Import from forecastability.adapters.agents.payloads.covariant_agent_payload_models instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.payloads.covariant_agent_payload_models import (  # noqa: E402, F401
    CovariantAgentExplanation,
    explanation_from_interpretation,
)

__all__ = [
    "CovariantAgentExplanation",
    "explanation_from_interpretation",
]
