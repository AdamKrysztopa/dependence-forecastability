"""Extended forecastability result models for the Phase 0 expansion scaffold."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, TypeAlias, cast

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from forecastability.triage.forecastability_profile import ForecastabilityProfile
from forecastability.utils.types import AmiInformationGeometry

SignalStrengthLabel: TypeAlias = Literal["low", "medium", "high", "unclear"]
NoiseRiskLabel: TypeAlias = Literal["low", "medium", "high", "unclear"]
PeriodicityHintLabel: TypeAlias = Literal["none", "weak", "moderate", "strong"]
OrdinalComplexityClassLabel: TypeAlias = Literal[
    "degenerate",
    "regular",
    "structured_nonlinear",
    "complex_but_redundant",
    "noise_like",
    "unclear",
]
StationarityHintLabel: TypeAlias = Literal[
    "likely_stationary",
    "trend_nonstationary",
    "seasonal",
    "unclear",
]
MemoryTypeLabel: TypeAlias = Literal[
    "anti_persistent",
    "short_memory",
    "persistent",
    "long_memory_candidate",
    "unclear",
]
PredictabilitySourceLabel: TypeAlias = Literal[
    "lag_dependence",
    "seasonality",
    "trend",
    "spectral_concentration",
    "ordinal_redundancy",
    "long_memory",
]
PredictabilitySources: TypeAlias = tuple[PredictabilitySourceLabel, ...]
RoutingMetadataValue: TypeAlias = str | int | float | bool | None


def _coerce_profile_values(value: object) -> np.ndarray:
    """Coerce JSON-friendly profile values back to the legacy ndarray surface."""
    if isinstance(value, np.ndarray):
        return value
    if isinstance(value, str | bytes):
        raise TypeError("values must be a numeric array or array-like sequence")
    try:
        return np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise TypeError("values must be a numeric array or array-like sequence") from exc


def _normalize_predictability_sources(value: object) -> PredictabilitySources:
    """Return a sorted, deduplicated predictability-source contract."""
    if value is None:
        return ()
    if isinstance(value, str | bytes):
        raise TypeError(
            "predictability_sources must be an iterable of PredictabilitySourceLabel values"
        )
    if not isinstance(value, Iterable):
        raise TypeError(
            "predictability_sources must be an iterable of PredictabilitySourceLabel values"
        )
    labels = tuple(cast(Iterable[PredictabilitySourceLabel], value))
    return cast(PredictabilitySources, tuple(sorted(set(labels), key=str)))


class SpectralForecastabilityResult(BaseModel):
    """Phase 0 result surface for spectral forecastability diagnostics."""

    model_config = ConfigDict(frozen=True)

    spectral_entropy: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized spectral entropy on the unit interval.",
    )
    spectral_predictability: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Deterministic spectral predictability score computed as one minus spectral entropy."
        ),
    )
    dominant_periods: list[int] = Field(
        default_factory=list,
        description="Dominant candidate periods ordered from highest to lower spectral power.",
    )
    spectral_concentration: float = Field(
        ge=0.0,
        le=1.0,
        description="Unit-scale concentration summary derived from the normalized spectrum.",
    )
    periodicity_hint: PeriodicityHintLabel = Field(
        description="Heuristic label describing the apparent strength of periodic structure.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Deterministic caveats or low-data notes emitted by the spectral diagnostic.",
    )

    @field_validator("dominant_periods")
    @classmethod
    def _validate_dominant_periods(cls, value: list[int]) -> list[int]:
        """Reject non-physical dominant periods."""
        if any(period <= 0 for period in value):
            raise ValueError("dominant_periods must contain only positive periods")
        return value


class OrdinalComplexityResult(BaseModel):
    """Phase 0 result surface for ordinal-pattern complexity diagnostics."""

    model_config = ConfigDict(frozen=True)

    permutation_entropy: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized permutation entropy on the unit interval.",
    )
    weighted_permutation_entropy: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional normalized weighted permutation entropy on the unit interval.",
    )
    ordinal_redundancy: float = Field(
        ge=0.0,
        le=1.0,
        description="Redundancy proxy computed from ordinal-pattern entropy.",
    )
    embedding_dimension: int = Field(
        description="Embedding dimension used for ordinal pattern extraction.",
    )
    delay: int = Field(
        ge=1,
        description="Delay between samples in each ordinal embedding vector.",
    )
    complexity_class: OrdinalComplexityClassLabel = Field(
        description="Deterministic ordinal complexity label derived from entropy summaries.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Deterministic caveats or degeneracy notes emitted by the ordinal diagnostic.",
    )

    @field_validator("embedding_dimension")
    @classmethod
    def _validate_embedding_dimension(cls, value: int) -> int:
        """Reject ordinal embeddings that are too small to define patterns."""
        if value < 2:
            raise ValueError("embedding_dimension must be at least 2")
        return value


class ClassicalStructureResult(BaseModel):
    """Phase 0 result surface for deterministic classical-structure features."""

    model_config = ConfigDict(frozen=True)

    acf1: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Lag-1 autocorrelation estimate when it can be computed safely.",
    )
    acf_decay_rate: float | None = Field(
        default=None,
        description=(
            "Deterministic summary of how quickly autocorrelation decays across early lags."
        ),
    )
    seasonal_strength: float | None = Field(
        default=None,
        description="Seasonality-strength summary; omitted when no period is supplied.",
    )
    trend_strength: float | None = Field(
        default=None,
        description="Trend-strength summary from a lightweight deterministic decomposition path.",
    )
    residual_variance_ratio: float | None = Field(
        default=None,
        ge=0.0,
        description="Residual-variance ratio after the classical-structure summaries are applied.",
    )
    stationarity_hint: StationarityHintLabel = Field(
        description="Heuristic stationarity label derived from classical structure summaries.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description=(
            "Deterministic caveats or decomposition notes emitted by the classical diagnostic."
        ),
    )


class MemoryStructureResult(BaseModel):
    """Phase 0 result surface for conservative memory-structure diagnostics."""

    model_config = ConfigDict(frozen=True)

    dfa_alpha: float | None = Field(
        default=None,
        description="Detrended fluctuation analysis alpha estimate when the fit is available.",
    )
    hurst_proxy: float | None = Field(
        default=None,
        description="Hurst-style proxy derived from the DFA slope when interpretation is safe.",
    )
    memory_type: MemoryTypeLabel = Field(
        description="Heuristic label describing the apparent persistence regime.",
    )
    scale_range: tuple[int, int] | None = Field(
        default=None,
        description="Inclusive minimum and maximum DFA scales used by the diagnostic.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Deterministic caveats or fit-quality notes emitted by the memory diagnostic.",
    )

    @field_validator("scale_range")
    @classmethod
    def _validate_scale_range(cls, value: tuple[int, int] | None) -> tuple[int, int] | None:
        """Require positive increasing bounds for DFA scale ranges."""
        if value is None:
            return value
        lower, upper = value
        if lower <= 0 or upper <= 0 or lower >= upper:
            raise ValueError("scale_range must contain positive increasing bounds")
        return value


class ExtendedForecastabilityFingerprint(BaseModel):
    """Composite extended fingerprint that bundles Phase 0 diagnostic blocks."""

    model_config = ConfigDict(frozen=True)

    information_geometry: AmiInformationGeometry | None = Field(
        default=None,
        description="Existing AMI information-geometry result reused by the extended fingerprint.",
    )
    spectral: SpectralForecastabilityResult | None = Field(
        default=None,
        description="Spectral forecastability diagnostic block when enabled.",
    )
    ordinal: OrdinalComplexityResult | None = Field(
        default=None,
        description="Ordinal complexity diagnostic block when enabled.",
    )
    classical: ClassicalStructureResult | None = Field(
        default=None,
        description="Classical structure diagnostic block when enabled.",
    )
    memory: MemoryStructureResult | None = Field(
        default=None,
        description="Memory-structure diagnostic block when enabled.",
    )


class ExtendedForecastabilityProfile(ForecastabilityProfile):
    """Human-facing routing summary derived from the extended fingerprint."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    horizons: list[int] = Field(
        description="1-based lag indices reused from the legacy forecastability profile.",
    )
    values: np.ndarray = Field(
        description="Raw AMI profile values reused from the legacy forecastability profile.",
    )
    epsilon: float = Field(
        description="Threshold used to identify informative horizons on the reused AMI profile.",
    )
    informative_horizons: list[int] = Field(
        description="Horizons where the reused AMI profile remains at or above epsilon.",
    )
    peak_horizon: int = Field(
        description="Peak lag horizon on the reused AMI profile.",
    )
    is_non_monotone: bool = Field(
        description="Whether the reused AMI profile increases after its first horizon.",
    )
    summary: str = Field(
        description="One-sentence summary inherited from the legacy forecastability profile.",
    )
    model_now: str = Field(
        description="Immediate model-action recommendation inherited from the legacy profile.",
    )
    review_horizons: list[int] = Field(
        description="Horizons from the reused AMI profile that warrant modeling review.",
    )
    avoid_horizons: list[int] = Field(
        description="Horizons from the reused AMI profile that should be avoided.",
    )

    signal_strength: SignalStrengthLabel = Field(
        description="High-level forecastability signal-strength label for the series.",
    )
    predictability_sources: PredictabilitySources = Field(
        default_factory=tuple,
        description=(
            "Sorted sequence of interpretable sources that appear to drive forecastability."
        ),
    )
    noise_risk: NoiseRiskLabel = Field(
        description="Heuristic noise-risk label inferred from the diagnostic fingerprint.",
    )
    recommended_model_families: list[str] = Field(
        default_factory=list,
        description="Deterministic shortlist of model families that fit the observed structure.",
    )
    avoid_model_families: list[str] = Field(
        default_factory=list,
        description="Model families to avoid when the diagnostic evidence argues against them.",
    )
    explanation: list[str] = Field(
        default_factory=list,
        description="Human-readable explanation bullets supporting the routing profile.",
    )

    @field_validator("values", mode="before")
    @classmethod
    def _coerce_values(cls, value: object) -> np.ndarray:
        """Preserve the parent ndarray contract across JSON round-trips."""
        return _coerce_profile_values(value)

    @field_serializer("values", when_used="json")
    def _serialize_values(self, value: np.ndarray) -> list[float]:
        """Serialize inherited ndarray profile values as a JSON-friendly sequence."""
        return value.tolist()

    @field_validator("predictability_sources", mode="before")
    @classmethod
    def _sort_predictability_sources(cls, value: object) -> PredictabilitySources:
        """Stabilize predictability-source ordering for the public JSON contract."""
        return _normalize_predictability_sources(value)


class ExtendedForecastabilityAnalysisResult(BaseModel):
    """Top-level Phase 0 result container for extended forecastability analysis."""

    model_config = ConfigDict(frozen=True)

    series_name: str | None = Field(
        default=None,
        description="Optional stable identifier for the analyzed series.",
    )
    n_observations: int = Field(
        gt=0,
        description="Number of observations in the analyzed univariate series.",
    )
    max_lag: int = Field(
        gt=0,
        description="Maximum lag horizon requested for lag-based diagnostics.",
    )
    period: int | None = Field(
        default=None,
        description="Optional positive seasonal period used by period-aware diagnostics.",
    )
    fingerprint: ExtendedForecastabilityFingerprint = Field(
        description="Composite extended fingerprint produced by the enabled diagnostic services.",
    )
    profile: ExtendedForecastabilityProfile = Field(
        description="Human-facing routing profile derived deterministically from the fingerprint.",
    )
    routing_metadata: dict[str, RoutingMetadataValue] = Field(
        default_factory=dict,
        description="JSON-friendly routing metadata for deterministic provenance and heuristics.",
    )

    @field_validator("period")
    @classmethod
    def _validate_period(cls, value: int | None) -> int | None:
        """Reject non-positive seasonal periods."""
        if value is not None and value <= 0:
            raise ValueError("period must be positive when provided")
        return value


__all__ = [
    "ClassicalStructureResult",
    "ExtendedForecastabilityAnalysisResult",
    "ExtendedForecastabilityFingerprint",
    "ExtendedForecastabilityProfile",
    "MemoryStructureResult",
    "OrdinalComplexityResult",
    "SpectralForecastabilityResult",
]
