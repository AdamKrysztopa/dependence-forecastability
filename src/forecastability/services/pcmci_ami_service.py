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
    from forecastability.ports import CausalGraphFullPort

__all__ = ["build_pcmci_ami_hybrid"]


def build_pcmci_ami_hybrid(
    *,
    ci_test: Literal["parcorr", "gpdc", "cmiknn", "knn_cmi"] = "knn_cmi",
    ami_threshold: float | None = None,
    n_neighbors: int = 8,
    min_pairs: int = 50,
    shuffle_scheme: Literal["iid", "block"] = "iid",
    n_permutations: int = 199,
    pcmci_max_lag: int | None = None,
    verbosity: int = 0,
    n_jobs_phase0: int = 1,
) -> CausalGraphFullPort:
    """Create a PCMCI-AMI-Hybrid causal discovery adapter.

    Args:
        ci_test: Conditional-independence test backend.
        ami_threshold: Optional fixed AMI pruning threshold.
        n_neighbors: kNN neighbors for MI estimation.
        min_pairs: Minimum observation pairs for MI computation.
        shuffle_scheme: Permutation scheme for the ``knn_cmi`` null distribution.
            ``"iid"`` (default) is fast and appropriate for residualised or
            whitened inputs; ``"block"`` preserves short-range autocorrelation
            (Politis & Romano, 1994) and is recommended on raw AR-like series.
        n_permutations: Shuffle-test null size for ``knn_cmi`` (floor 99).
        pcmci_max_lag: Optional maximum lag for Phase 1/2 PCMCI+.  When set,
            Phase 0 MI is still computed over the full ``max_lag`` range, but
            only candidates at or below ``pcmci_max_lag`` are passed to PCMCI+.
            Useful for reducing PCMCI+ runtime on large lag windows.
        verbosity: Tigramite verbosity level (0 = silent).
        n_jobs_phase0: Number of parallel workers for Phase 0 MI computation.

    Returns:
        A ``CausalGraphPort``-compatible adapter.
    """
    mod = importlib.import_module("forecastability.adapters.pcmci_ami_adapter")
    return mod.PcmciAmiAdapter(
        ci_test=ci_test,
        ami_threshold=ami_threshold,
        n_neighbors=n_neighbors,
        min_pairs=min_pairs,
        shuffle_scheme=shuffle_scheme,
        n_permutations=n_permutations,
        pcmci_max_lag=pcmci_max_lag,
        verbosity=verbosity,
        n_jobs_phase0=n_jobs_phase0,
    )
