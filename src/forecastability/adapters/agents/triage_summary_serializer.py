"""Backward-compatible re-export shim (RVH-F11).

Triage summary serializer has moved to
:mod:`forecastability.adapters.agents.payloads.triage_summary_serializer`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.agents.triage_summary_serializer is deprecated. "
    "Import from forecastability.adapters.agents.payloads.triage_summary_serializer instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.payloads.triage_summary_serializer import (  # noqa: E402, F401
    SerialisedTriageSummary,
    serialise_batch,
    serialise_batch_to_json,
    serialise_payload,
    serialise_to_json,
)

__all__ = [
    "SerialisedTriageSummary",
    "serialise_batch",
    "serialise_batch_to_json",
    "serialise_payload",
    "serialise_to_json",
]
