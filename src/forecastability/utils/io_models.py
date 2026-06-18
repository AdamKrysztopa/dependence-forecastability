# Migration shim — canonical location is forecastability.reporting.io_models
# Remove this shim in v0.6.0.
#
# This module intentionally avoids a static ``import`` of the canonical
# ``forecastability.reporting`` package: a top-level import would re-introduce
# the ``utils -> reporting`` layer edge that this refactor removes. Names are
# resolved lazily through ``importlib`` so the public import path keeps working
# without participating in the layer-import graph.
from __future__ import annotations

import importlib
import warnings as _warnings
from typing import Any

_CANONICAL_MODULE = "forecastability.reporting.io_models"

_EXPORTS = frozenset(
    {
        "CanonicalInterpretationPayload",
        "CanonicalPayload",
        "CanonicalSummaryBundle",
        "CanonicalSummaryPayload",
        "ExogCaseRecord",
    }
)

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve canonical payload models from the reporting layer lazily."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    _warnings.warn(
        "forecastability.utils.io_models is deprecated in v0.5.0; "
        "use forecastability.reporting.io_models instead. "
        "See docs/migration/v0.4.x_to_v0.5.0.md.",
        DeprecationWarning,
        stacklevel=2,
    )
    module = importlib.import_module(_CANONICAL_MODULE)
    return getattr(module, name)
