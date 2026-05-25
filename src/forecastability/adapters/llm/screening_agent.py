"""Backward-compatible re-export shim (RVH-F11).

The screening agent has moved to
:mod:`forecastability.adapters.agents.runtime.screening_agent`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.llm.screening_agent is deprecated. "
    "Import from forecastability.adapters.agents.runtime.screening_agent instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.runtime.screening_agent import (  # noqa: E402, F401
    FeatureRanking,
    FeatureScreeningReport,
    ScreeningDeps,
    create_screening_agent,
    pydantic_ai_available,
)

__all__ = [
    "FeatureRanking",
    "FeatureScreeningReport",
    "ScreeningDeps",
    "create_screening_agent",
    "pydantic_ai_available",
]
