# Migration shim — canonical location is
# forecastability.use_cases.diagnostics.fingerprint_regression
# Remove this shim in v0.6.0.
#
# Names are resolved lazily through ``importlib`` so the public import path
# keeps working without eagerly importing the use-case layer at module load.
from __future__ import annotations

import importlib
import warnings as _warnings
from typing import Any

_CANONICAL_MODULE = "forecastability.use_cases.diagnostics.fingerprint_regression"


def __getattr__(name: str) -> Any:
    """Resolve the validation harness from the use-case layer lazily."""
    if name.startswith("__") and name.endswith("__"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    _warnings.warn(
        "forecastability.diagnostics.fingerprint_regression is deprecated in v0.5.0; "
        "use forecastability.use_cases.diagnostics.fingerprint_regression instead. "
        "See docs/migration/v0.4.x_to_v0.5.0.md.",
        DeprecationWarning,
        stacklevel=2,
    )
    module = importlib.import_module(_CANONICAL_MODULE)
    return getattr(module, name)
