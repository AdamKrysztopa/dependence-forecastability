"""Backward-compatible re-export shim (RVH-F11).

The triage agent has moved to
:mod:`forecastability.adapters.agents.runtime.triage_agent`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.llm.triage_agent is deprecated. "
    "Import from forecastability.adapters.agents.runtime.triage_agent instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.runtime.triage_agent import (  # noqa: E402, F401
    TriageDeps,
    TriageExplanation,
    create_triage_agent,
    run_triage_agent,
)

__all__ = [
    "TriageDeps",
    "TriageExplanation",
    "create_triage_agent",
    "run_triage_agent",
]
