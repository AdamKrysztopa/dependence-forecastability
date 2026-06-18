# Migration shim — canonical location is forecastability.pipeline.robustness
# Remove this shim in v0.6.0.
#
# This module intentionally avoids a static ``import`` of the canonical
# ``forecastability.pipeline`` package: a top-level import would re-introduce
# the ``utils -> pipeline`` layer edge that this refactor removes. Names are
# resolved lazily through ``importlib`` so the public import path keeps working
# without participating in the layer-import graph.
from __future__ import annotations

import importlib
import warnings as _warnings
from typing import Any

_CANONICAL_MODULE = "forecastability.pipeline.robustness"

_EXPORTS = frozenset(
    {
        "run_backend_comparison",
        "run_robustness_study",
        "run_sample_size_stress",
    }
)

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve robustness-study entry points from the pipeline layer lazily."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    _warnings.warn(
        "forecastability.utils.robustness is deprecated in v0.5.0; "
        "use forecastability.pipeline.robustness instead. "
        "See docs/migration/v0.4.x_to_v0.5.0.md.",
        DeprecationWarning,
        stacklevel=2,
    )
    module = importlib.import_module(_CANONICAL_MODULE)
    return getattr(module, name)
