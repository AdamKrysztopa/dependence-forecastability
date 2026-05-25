"""Backward-compatible re-export shim (RVH-F11).

Fingerprint summary serializer has moved to
:mod:`forecastability.adapters.agents.payloads.fingerprint_summary_serializer`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.agents.fingerprint_summary_serializer is deprecated. "
    "Import from forecastability.adapters.agents.payloads.fingerprint_summary_serializer instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.payloads.fingerprint_summary_serializer import (  # noqa: E402, F401
    SerialisedFingerprintSummary,
    serialise_fingerprint_payload,
    serialise_fingerprint_to_json,
)

__all__ = [
    "SerialisedFingerprintSummary",
    "serialise_fingerprint_payload",
    "serialise_fingerprint_to_json",
]
