"""PCMCI-AMI-Hybrid service facade.

Provides a composition-root factory that returns a ``CausalGraphPort``
backed by the PCMCI-AMI-Hybrid adapter.  The adapter import is deferred
to call time via ``importlib`` so this module stays in the service layer
(no static adapter dependency).
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from forecastability.ports import CausalGraphPort

__all__ = ["build_pcmci_ami_hybrid"]


def build_pcmci_ami_hybrid(
    *,
    ci_test: Literal["parcorr", "gpdc", "cmiknn", "knn_cmi"] = "knn_cmi",
    ami_threshold: float | None = None,
    n_neighbors: int = 8,
    min_pairs: int = 50,
) -> CausalGraphPort:
    """Create a PCMCI-AMI-Hybrid causal discovery adapter.

    Args:
        ci_test: Conditional-independence test backend.
        ami_threshold: Optional fixed AMI pruning threshold.
        n_neighbors: kNN neighbors for MI estimation.
        min_pairs: Minimum observation pairs for MI computation.

    Returns:
        A ``CausalGraphPort``-compatible adapter.
    """
    mod = importlib.import_module("forecastability.adapters.pcmci_ami_adapter")
    return mod.PcmciAmiAdapter(
        ci_test=ci_test,
        ami_threshold=ami_threshold,
        n_neighbors=n_neighbors,
        min_pairs=min_pairs,
    )
