"""forecastability — thin re-export shim (v0.5.0+).

Canonical public surface lives in ``forecastability.api`` (~25 names).
Legacy v0.4.x names forward through ``forecastability._legacy`` with a
``DeprecationWarning``; ``compute_transfer_entropy`` raises ``ImportError``
because its semantics changed.  See docs/migration/v0.4.x_to_v0.5.0.md.
"""

from __future__ import annotations

from typing import Any

from forecastability.api import (
    AmiInformationGeometry,
    AmiInformationGeometryConfig,
    ForecastabilityFingerprint,
    ForecastPrepContract,
    GcmiResult,
    MetricCurve,
    ReadinessReport,
    RoutingRecommendation,
    TransferEntropyResult,
    TriageRequest,
    TriageResult,
    __version__,
    build_forecast_prep_contract,
    compute_ami,
    compute_ami_information_geometry,
    compute_conditional_mutual_information_ksg,
    compute_pami_linear_residual,
    compute_predictive_information_gain,
    compute_significance_bands_generic,
    compute_transfer_entropy_ksg,
    generate_ar1,
    generate_white_noise,
    run_batch_forecastability_workbench,
    run_covariant_analysis,
    run_lagged_exogenous_triage,
    run_triage,
    validate_time_series,
)

__all__ = [
    "__version__",
    "AmiInformationGeometry",
    "AmiInformationGeometryConfig",
    "build_forecast_prep_contract",
    "compute_ami",
    "compute_ami_information_geometry",
    "compute_conditional_mutual_information_ksg",
    "compute_pami_linear_residual",
    "compute_predictive_information_gain",
    "compute_significance_bands_generic",
    "compute_transfer_entropy_ksg",
    "ForecastabilityFingerprint",
    "ForecastPrepContract",
    "generate_ar1",
    "generate_white_noise",
    "GcmiResult",
    "MetricCurve",
    "ReadinessReport",
    "RoutingRecommendation",
    "run_batch_forecastability_workbench",
    "run_covariant_analysis",
    "run_lagged_exogenous_triage",
    "run_triage",
    "TransferEntropyResult",
    "TriageRequest",
    "TriageResult",
    "validate_time_series",
]


def __getattr__(name: str) -> Any:  # Any: legacy resolver returns heterogeneous types
    """Forward legacy names to _legacy module with DeprecationWarning.

    Args:
        name: Attribute name being accessed on the ``forecastability`` package.

    Raises:
        ImportError: If ``name`` was removed in v0.5.0 with no drop-in replacement.
        AttributeError: If ``name`` was never part of the public surface.
    """
    import importlib

    try:
        legacy = importlib.import_module("forecastability._legacy")
        # ImportError (removed name) must propagate; AttributeError (unknown) is re-raised.
        return getattr(legacy, name)
    except ImportError:
        raise  # removed symbol — let the ImportError with migration message propagate
    except AttributeError:
        raise AttributeError(
            f"module 'forecastability' has no attribute {name!r}. "
            "This name may have been removed or renamed in v0.5.0. "
            "See docs/migration/v0.4.x_to_v0.5.0.md."
        ) from None
