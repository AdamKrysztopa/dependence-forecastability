"""Compatibility service facade for directional transfer-entropy functions.

v0.5.0: compute_transfer_entropy renamed to compute_predictive_information_gain.
        compute_transfer_entropy_curve renamed to compute_predictive_information_gain_curve.
        This facade re-exports under both old and new names for a single release cycle.
"""

from forecastability.services.diagnostics.predictive_information_gain import (
    compute_predictive_information_gain,
    compute_predictive_information_gain_curve,
)

# Legacy shim — will be removed in v0.6.0
compute_transfer_entropy_curve = compute_predictive_information_gain_curve

__all__ = [
    "compute_predictive_information_gain",
    "compute_predictive_information_gain_curve",
    "compute_transfer_entropy_curve",
]
