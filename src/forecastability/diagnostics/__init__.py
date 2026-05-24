"""Diagnostics subpackage for dependence and significance utilities."""

from forecastability.diagnostics.cmi_ksg import (
    compute_conditional_mutual_information_ksg,
    compute_transfer_entropy_ksg,
)
from forecastability.diagnostics.docs_contract import DocsCheckName
from forecastability.diagnostics.predictive_information_gain import (
    compute_predictive_information_gain,
)

__all__ = [
    "DocsCheckName",
    "compute_conditional_mutual_information_ksg",
    "compute_predictive_information_gain",
    "compute_transfer_entropy_ksg",
]


def __getattr__(name: str) -> object:
    if name == "compute_transfer_entropy":
        raise ImportError(
            "compute_transfer_entropy was split in v0.5.0; use "
            "compute_transfer_entropy_ksg for Schreiber TE or "
            "compute_predictive_information_gain for residual-MI. "
            "See docs/migration/v0.4.x_to_v0.5.0.md."
        )
    raise AttributeError(f"module 'forecastability.diagnostics' has no attribute {name!r}")
