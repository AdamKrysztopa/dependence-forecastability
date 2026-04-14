"""Compatibility shim for moved metrics module."""

# TODO: 0.3.0 Remove shim; import from forecastability.metrics.scorers.

from forecastability.metrics.scorers import *  # noqa: F401,F403
from forecastability.metrics.scorers import (  # noqa: F401
    _choose_embedding_order,
    _compute_log_divergence,
    _compute_permutation_entropy,
    _embed_series,
    _estimate_lle_rosenstein,
    _find_nearest_with_theiler,
    _permutation_entropy_scorer,
    _spectral_entropy_scorer,
    _spectral_predictability_scorer,
)
