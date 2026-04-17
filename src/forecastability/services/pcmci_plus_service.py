"""PCMCI+ service facade.

Provides a composition-root factory that returns a ``CausalGraphPort``
backed by the optional Tigramite adapter. The adapter import is deferred
to call time so the service layer stays free of static adapter imports.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from forecastability.ports import CausalGraphPort

__all__ = ["build_pcmci_plus"]


def build_pcmci_plus(
    *,
    ci_test: Literal["parcorr", "gpdc", "cmiknn"] = "parcorr",
) -> CausalGraphPort:
    """Create a PCMCI+ causal-discovery adapter.

    Args:
        ci_test: Conditional-independence test backend.

    Returns:
        A ``CausalGraphPort``-compatible adapter.
    """
    mod = importlib.import_module("forecastability.adapters.tigramite_adapter")
    return mod.TigramiteAdapter(ci_test=ci_test)
