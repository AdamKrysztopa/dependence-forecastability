# Migration shim — canonical location is
# forecastability.domain.models.extended_forecastability
# Remove this shim in v0.6.0
from __future__ import annotations

import warnings as _warnings

from forecastability.domain.models.extended_forecastability import (  # noqa: F401
    ClassicalStructureResult,
    ExtendedForecastabilityAnalysisResult,
    ExtendedForecastabilityFingerprint,
    ExtendedForecastabilityProfile,
    MemoryStructureResult,
    MemoryTypeLabel,
    NoiseRiskLabel,
    OrdinalComplexityClassLabel,
    OrdinalComplexityResult,
    PeriodicityHintLabel,
    PredictabilitySourceLabel,
    PredictabilitySources,
    RoutingMetadataValue,
    SignalStrengthLabel,
    SpectralForecastabilityResult,
    StationarityHintLabel,
)

_warnings.warn(
    "forecastability.triage.extended_forecastability is deprecated in v0.5.0; "
    "use forecastability.domain.models.extended_forecastability instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
