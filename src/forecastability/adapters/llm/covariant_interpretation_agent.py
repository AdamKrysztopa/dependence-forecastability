"""Backward-compatible re-export shim (RVH-F11).

The covariant interpretation agent has moved to
:mod:`forecastability.adapters.agents.runtime.covariant_interpretation_agent`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.llm.covariant_interpretation_agent is deprecated. "
    "Import from forecastability.adapters.agents.runtime.covariant_interpretation_agent instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.runtime.covariant_interpretation_agent import (  # noqa: E402, F401
    CovariantAgentDeps,
    run_covariant_interpretation_agent,
)

__all__ = [
    "CovariantAgentDeps",
    "run_covariant_interpretation_agent",
]
