"""Backward-compatible re-export shim.

The live triage agent has moved to
``forecastability.adapters.llm.triage_agent``.
This module will be removed in a future release.
"""

import warnings

warnings.warn(
    "forecastability.adapters.pydantic_ai_agent is deprecated. "
    "Import from forecastability.adapters.llm.triage_agent instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.llm.triage_agent import (  # noqa: E402, F401
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
