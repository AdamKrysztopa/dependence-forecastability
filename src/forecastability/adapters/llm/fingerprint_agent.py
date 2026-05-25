"""Backward-compatible re-export shim (RVH-F11).

The fingerprint agent has moved to
:mod:`forecastability.adapters.agents.runtime.fingerprint_agent`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.llm.fingerprint_agent is deprecated. "
    "Import from forecastability.adapters.agents.runtime.fingerprint_agent instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.runtime.fingerprint_agent import (  # noqa: E402, F401
    FingerprintDeps,
    FingerprintExplanation,
    create_fingerprint_agent,
    pydantic_ai_available,
    run_fingerprint_agent,
)

__all__ = [
    "FingerprintDeps",
    "FingerprintExplanation",
    "create_fingerprint_agent",
    "pydantic_ai_available",
    "run_fingerprint_agent",
]
