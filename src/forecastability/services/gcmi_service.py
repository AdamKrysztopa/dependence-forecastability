"""Compatibility service facade for Gaussian Copula MI functions."""

from forecastability.diagnostics.gcmi import (
    compute_gcmi,
    compute_gcmi_at_lag,
    compute_gcmi_curve,
)

__all__ = ["compute_gcmi", "compute_gcmi_at_lag", "compute_gcmi_curve"]
