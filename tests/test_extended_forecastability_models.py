"""Focused Phase 0 tests for the extended forecastability result surfaces."""

from __future__ import annotations

import json

import numpy as np
import pytest
from pydantic import BaseModel, ValidationError

import forecastability
import forecastability.triage as triage
from forecastability.triage import (
    ClassicalStructureResult,
    ExtendedForecastabilityAnalysisResult,
    ExtendedForecastabilityFingerprint,
    ExtendedForecastabilityProfile,
    MemoryStructureResult,
    OrdinalComplexityResult,
    SpectralForecastabilityResult,
)
from forecastability.triage.extended_forecastability import PredictabilitySourceLabel
from forecastability.triage.forecastability_profile import ForecastabilityProfile
from forecastability.utils.types import AmiInformationGeometry


def _minimal_geometry() -> AmiInformationGeometry:
    """Build a minimal AMI geometry object for extended-model tests."""
    return AmiInformationGeometry(
        signal_to_noise=0.4,
        information_horizon=3,
        information_structure="monotonic",
        informative_horizons=[1, 2, 3],
    )


def _minimal_profile() -> ExtendedForecastabilityProfile:
    """Build a minimal extended profile object for analysis-result tests."""
    predictability_sources: tuple[PredictabilitySourceLabel, PredictabilitySourceLabel] = (
        "seasonality",
        "lag_dependence",
    )
    return ExtendedForecastabilityProfile(
        horizons=[1, 2, 3],
        values=np.array([0.3, 0.2, 0.1]),
        epsilon=0.1,
        informative_horizons=[1, 2],
        peak_horizon=1,
        is_non_monotone=False,
        summary="Lag dependence decays quickly after the first horizon.",
        model_now="HIGH",
        review_horizons=[1, 2],
        avoid_horizons=[3],
        signal_strength="medium",
        predictability_sources=predictability_sources,
        noise_risk="low",
        recommended_model_families=["ARIMA", "ETS"],
        avoid_model_families=["pure_mlp"],
        explanation=["Lag dependence and seasonality are both present."],
    )


@pytest.mark.parametrize(
    ("model_cls", "expected_fields"),
    [
        (
            SpectralForecastabilityResult,
            {
                "spectral_entropy",
                "spectral_predictability",
                "dominant_periods",
                "spectral_concentration",
                "periodicity_hint",
                "notes",
            },
        ),
        (
            OrdinalComplexityResult,
            {
                "permutation_entropy",
                "weighted_permutation_entropy",
                "ordinal_redundancy",
                "embedding_dimension",
                "delay",
                "complexity_class",
                "notes",
            },
        ),
        (
            ClassicalStructureResult,
            {
                "acf1",
                "acf_decay_rate",
                "seasonal_strength",
                "trend_strength",
                "residual_variance_ratio",
                "stationarity_hint",
                "notes",
            },
        ),
        (
            MemoryStructureResult,
            {"dfa_alpha", "hurst_proxy", "memory_type", "scale_range", "notes"},
        ),
        (
            ExtendedForecastabilityFingerprint,
            {"information_geometry", "spectral", "ordinal", "classical", "memory"},
        ),
        (
            ExtendedForecastabilityProfile,
            {
                "horizons",
                "values",
                "epsilon",
                "informative_horizons",
                "peak_horizon",
                "is_non_monotone",
                "summary",
                "model_now",
                "review_horizons",
                "avoid_horizons",
                "signal_strength",
                "predictability_sources",
                "noise_risk",
                "recommended_model_families",
                "avoid_model_families",
                "explanation",
            },
        ),
        (
            ExtendedForecastabilityAnalysisResult,
            {
                "series_name",
                "n_observations",
                "max_lag",
                "period",
                "fingerprint",
                "profile",
                "routing_metadata",
            },
        ),
    ],
)
def test_extended_phase0_fields_have_descriptions(
    model_cls: type[BaseModel],
    expected_fields: set[str],
) -> None:
    """Every Phase 0 field should be present and carry a public description."""
    model_fields = model_cls.model_fields
    assert set(model_fields) == expected_fields
    for field_name, field_info in model_fields.items():
        assert field_info.description, f"Expected a Field description for {field_name}"


def test_extended_profile_subclasses_forecastability_profile_with_stable_json_surface() -> None:
    """The extended profile should preserve the legacy parent contract and stable JSON order."""
    raw_profile: dict[str, object] = {
        "horizons": [1, 2, 3],
        "values": [0.3, 0.2, 0.1],
        "epsilon": 0.1,
        "informative_horizons": [1, 2],
        "peak_horizon": 1,
        "is_non_monotone": False,
        "summary": "Lag dependence decays quickly after the first horizon.",
        "model_now": "HIGH",
        "review_horizons": [1, 2],
        "avoid_horizons": [3],
        "signal_strength": "medium",
        "predictability_sources": frozenset(("seasonality", "lag_dependence")),
        "noise_risk": "low",
        "recommended_model_families": ["ARIMA", "ETS"],
        "avoid_model_families": ["pure_mlp"],
        "explanation": ["Lag dependence and seasonality are both present."],
    }
    profile = ExtendedForecastabilityProfile.model_validate(raw_profile)

    assert issubclass(ExtendedForecastabilityProfile, ForecastabilityProfile)
    assert isinstance(profile, ForecastabilityProfile)
    assert profile.predictability_sources == ("lag_dependence", "seasonality")

    payload = json.loads(profile.model_dump_json())

    assert payload["values"] == [0.3, 0.2, 0.1]
    assert payload["predictability_sources"] == ["lag_dependence", "seasonality"]


def test_extended_profile_rejects_unknown_predictability_sources_with_validation_error() -> None:
    """Unknown predictability-source labels should surface as normal validation errors."""
    raw_profile: dict[str, object] = {
        "horizons": [1, 2, 3],
        "values": [0.3, 0.2, 0.1],
        "epsilon": 0.1,
        "informative_horizons": [1, 2],
        "peak_horizon": 1,
        "is_non_monotone": False,
        "summary": "Lag dependence decays quickly after the first horizon.",
        "model_now": "HIGH",
        "review_horizons": [1, 2],
        "avoid_horizons": [3],
        "signal_strength": "medium",
        "predictability_sources": ["lag_dependence", "mystery_source"],
        "noise_risk": "low",
        "recommended_model_families": ["ARIMA", "ETS"],
        "avoid_model_families": ["pure_mlp"],
        "explanation": ["Lag dependence and seasonality are both present."],
    }

    with pytest.raises(ValidationError, match="unknown predictability source"):
        ExtendedForecastabilityProfile.model_validate(raw_profile)


def test_extended_analysis_result_round_trips_with_existing_geometry_type() -> None:
    """The extended fingerprint should reuse the existing AMI geometry result model."""
    result = ExtendedForecastabilityAnalysisResult(
        series_name="demo",
        n_observations=128,
        max_lag=24,
        period=12,
        fingerprint=ExtendedForecastabilityFingerprint(
            information_geometry=_minimal_geometry(),
            spectral=SpectralForecastabilityResult(
                spectral_entropy=0.2,
                spectral_predictability=0.8,
                dominant_periods=[12, 6],
                spectral_concentration=0.7,
                periodicity_hint="strong",
                notes=["Seasonal peak dominates the spectrum."],
            ),
            ordinal=None,
            classical=None,
            memory=None,
        ),
        profile=_minimal_profile(),
        routing_metadata={"route_version": "phase0", "seasonal": True},
    )

    payload = json.loads(result.model_dump_json())
    restored = ExtendedForecastabilityAnalysisResult.model_validate_json(json.dumps(payload))

    assert isinstance(restored.fingerprint.information_geometry, AmiInformationGeometry)
    assert restored.profile.predictability_sources == ("lag_dependence", "seasonality")
    assert payload["profile"]["predictability_sources"] == ["lag_dependence", "seasonality"]
    np.testing.assert_allclose(restored.profile.values, result.profile.values)
    assert restored.profile.horizons == result.profile.horizons
    assert restored.profile.summary == result.profile.summary
    assert restored.routing_metadata == result.routing_metadata


def test_existing_forecastability_profile_contract_remains_unchanged() -> None:
    """The legacy public ForecastabilityProfile must keep its preexisting schema."""
    expected_fields = {
        "horizons",
        "values",
        "epsilon",
        "informative_horizons",
        "peak_horizon",
        "is_non_monotone",
        "summary",
        "model_now",
        "review_horizons",
        "avoid_horizons",
    }
    assert set(ForecastabilityProfile.model_fields) == expected_fields

    profile = ForecastabilityProfile(
        horizons=[1, 2, 3],
        values=np.array([0.3, 0.2, 0.1]),
        epsilon=0.1,
        informative_horizons=[1, 2, 3],
        peak_horizon=1,
        is_non_monotone=False,
        summary="Legacy profile contract stays intact.",
        model_now="HIGH",
        review_horizons=[1, 2, 3],
        avoid_horizons=[],
    )
    assert profile.peak_horizon == 1


def test_ordinal_complexity_rejects_invalid_embedding_dimension() -> None:
    """Embedding dimensions below two should fail the Phase 0 contract."""
    with pytest.raises(ValidationError, match="embedding_dimension"):
        OrdinalComplexityResult(
            permutation_entropy=0.8,
            weighted_permutation_entropy=0.8,
            ordinal_redundancy=0.2,
            embedding_dimension=1,
            delay=1,
            complexity_class="noise_like",
        )


@pytest.mark.parametrize("dominant_periods", ([0], [-1, 12]))
def test_spectral_forecastability_rejects_non_positive_dominant_periods(
    dominant_periods: list[int],
) -> None:
    """Dominant periods must stay strictly positive for physical interpretability."""
    with pytest.raises(ValidationError, match="dominant_periods"):
        SpectralForecastabilityResult(
            spectral_entropy=0.2,
            spectral_predictability=0.8,
            dominant_periods=dominant_periods,
            spectral_concentration=0.7,
            periodicity_hint="strong",
        )


def test_analysis_result_rejects_non_positive_period() -> None:
    """Seasonal periods must be positive when supplied."""
    with pytest.raises(ValidationError, match="period"):
        ExtendedForecastabilityAnalysisResult(
            series_name=None,
            n_observations=64,
            max_lag=12,
            period=0,
            fingerprint=ExtendedForecastabilityFingerprint(),
            profile=_minimal_profile(),
        )


@pytest.mark.parametrize("scale_range", [(0, 8), (8, 8), (9, 4)])
def test_memory_structure_rejects_invalid_scale_range(scale_range: tuple[int, int]) -> None:
    """DFA scale bounds must be positive and strictly increasing."""
    with pytest.raises(ValidationError, match="scale_range"):
        MemoryStructureResult(
            dfa_alpha=0.6,
            hurst_proxy=0.6,
            memory_type="persistent",
            scale_range=scale_range,
        )


def test_extended_models_are_reexported_from_triage_and_top_level() -> None:
    """The new Phase 0 models should resolve from both stable import roots."""
    exported_names = [
        "SpectralForecastabilityResult",
        "OrdinalComplexityResult",
        "ClassicalStructureResult",
        "MemoryStructureResult",
        "ExtendedForecastabilityFingerprint",
        "ExtendedForecastabilityProfile",
        "ExtendedForecastabilityAnalysisResult",
    ]

    for name in exported_names:
        assert getattr(forecastability, name) is getattr(triage, name)
