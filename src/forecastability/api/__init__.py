"""forecastability.api — canonical public surface (v0.5.0+).

Every name exported here is part of the stable public API contract.
Import from ``forecastability`` directly (the thin shim re-exports everything).
Do NOT add names here without a corresponding plan entry; the list is frozen
for the v0.5.0 release and subject to semantic-versioning guarantees.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------
__version__: str = "0.5.0"

# ---------------------------------------------------------------------------
# Key estimators — diagnostics
# ---------------------------------------------------------------------------
from forecastability.diagnostics.cmi_ksg import (
    compute_conditional_mutual_information_ksg,
    compute_transfer_entropy_ksg,
)
from forecastability.diagnostics.predictive_information_gain import (
    compute_predictive_information_gain,
)

# ---------------------------------------------------------------------------
# Domain value objects — result / contract types
# ---------------------------------------------------------------------------
from forecastability.domain.value_objects.types import (
    AmiInformationGeometry,
    ForecastabilityFingerprint,
    ForecastPrepContract,
    GcmiResult,
    MetricCurve,
    RoutingRecommendation,
    TransferEntropyResult,
)

# ---------------------------------------------------------------------------
# Key estimators — metrics
# ---------------------------------------------------------------------------
from forecastability.metrics.metrics import (
    compute_ami,
    compute_pami_linear_residual,
)

# ---------------------------------------------------------------------------
# Key estimators — services
# ---------------------------------------------------------------------------
from forecastability.services.ami_information_geometry_service import (
    AmiInformationGeometryConfig,
    compute_ami_information_geometry,
)
from forecastability.services.significance_service import (
    compute_significance_bands_generic,
)

# ---------------------------------------------------------------------------
# Domain models — request / result types
# Import via the triage.models shim (not domain.models.triage directly) to
# avoid a circular import: domain.models.triage → triage.extended_forecastability
# → triage.__init__ → adapters.result_bundle_io → triage.models → domain.models.triage
# ---------------------------------------------------------------------------
from forecastability.triage.models import (
    ReadinessReport,
    TriageRequest,
    TriageResult,
)

# ---------------------------------------------------------------------------
# Core triage entry points
# ---------------------------------------------------------------------------
from forecastability.use_cases import (
    build_forecast_prep_contract,
    run_covariant_analysis,
    run_lagged_exogenous_triage,
    run_triage,
)
from forecastability.use_cases.run_batch_forecastability_workbench import (
    run_batch_forecastability_workbench,
)

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
from forecastability.utils.datasets import (
    generate_ar1,
    generate_white_noise,
)
from forecastability.utils.validation import validate_time_series

# ---------------------------------------------------------------------------
# Canonical public surface — frozen for v0.5.0
# ---------------------------------------------------------------------------
__all__: list[str] = [
    # version
    "__version__",
    # triage entry points
    "run_triage",
    "run_batch_forecastability_workbench",
    "build_forecast_prep_contract",
    "run_covariant_analysis",
    "run_lagged_exogenous_triage",
    # domain models
    "TriageRequest",
    "TriageResult",
    "ReadinessReport",
    # domain value objects
    "AmiInformationGeometry",
    "ForecastabilityFingerprint",
    "ForecastPrepContract",
    "GcmiResult",
    "MetricCurve",
    "RoutingRecommendation",
    "TransferEntropyResult",
    # estimators — metrics
    "compute_ami",
    "compute_pami_linear_residual",
    # estimators — diagnostics
    "compute_conditional_mutual_information_ksg",
    "compute_transfer_entropy_ksg",
    "compute_predictive_information_gain",
    # estimators — services
    "AmiInformationGeometryConfig",
    "compute_ami_information_geometry",
    "compute_significance_bands_generic",
    # utilities
    "generate_ar1",
    "generate_white_noise",
    "validate_time_series",
]
