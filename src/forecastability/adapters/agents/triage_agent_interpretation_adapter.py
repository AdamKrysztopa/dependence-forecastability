"""Backward-compatible re-export shim (RVH-F11).

Triage agent interpretation adapter has moved to
:mod:`forecastability.adapters.agents.payloads.triage_agent_interpretation_adapter`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.agents.triage_agent_interpretation_adapter is deprecated. "
    "Import from forecastability.adapters.agents.payloads.triage_agent_interpretation_adapter "
    "instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.payloads.triage_agent_interpretation_adapter import (  # noqa: E402, F401
    InterpretationEvidence,
    TriageAgentInterpretation,
    interpret_batch,
    interpret_payload,
)

__all__ = [
    "InterpretationEvidence",
    "TriageAgentInterpretation",
    "interpret_batch",
    "interpret_payload",
]
