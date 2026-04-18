"""Compatibility service facade for directional transfer-entropy functions."""

from forecastability.diagnostics.transfer_entropy import (
    compute_transfer_entropy,
    compute_transfer_entropy_curve,
)

__all__ = ["compute_transfer_entropy", "compute_transfer_entropy_curve"]
