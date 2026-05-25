"""Backward-compatible re-export shim (RVH-F11).

Fingerprint agent interpretation adapter has moved to
:mod:`forecastability.adapters.agents.payloads.fingerprint_agent_interpretation_adapter`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.agents.fingerprint_agent_interpretation_adapter is deprecated. "
    "Import from "
    "forecastability.adapters.agents.payloads.fingerprint_agent_interpretation_adapter instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.payloads.fingerprint_agent_interpretation_adapter import (  # noqa: E402, F401
    FingerprintAgentInterpretation,
    FingerprintInterpretationEvidence,
    FingerprintInterpretationInput,
    interpret_fingerprint_batch,
    interpret_fingerprint_payload,
)

__all__ = [
    "FingerprintAgentInterpretation",
    "FingerprintInterpretationEvidence",
    "FingerprintInterpretationInput",
    "interpret_fingerprint_batch",
    "interpret_fingerprint_payload",
]
