"""Tests for the geometry-backed forecastability fingerprint use case."""

from __future__ import annotations

import json

import numpy as np
import pytest
from pydantic import ValidationError

from forecastability.services.ami_information_geometry_service import AmiInformationGeometryConfig
from forecastability.services.routing_policy_service import RoutingPolicyConfig
from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.utils.synthetic import (
    generate_ar1_monotonic,
    generate_seasonal_periodic,
    generate_white_noise,
)
from forecastability.utils.types import (
    AmiInformationGeometry,
    FingerprintBundle,
    ForecastabilityFingerprint,
    RoutingRecommendation,
)

_N = 320
_MAX_LAG = 12
_N_SURROGATES = 99


@pytest.fixture(scope="module")
def ar1_bundle() -> FingerprintBundle:
    """Return one geometry-backed AR(1) fingerprint bundle."""
    return run_forecastability_fingerprint(
        generate_ar1_monotonic(n=_N, seed=42),
        target_name="ar1",
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=42,
    )


@pytest.fixture(scope="module")
def white_noise_bundle() -> FingerprintBundle:
    """Return one geometry-backed white-noise fingerprint bundle."""
    return run_forecastability_fingerprint(
        generate_white_noise(n=_N, seed=42),
        target_name="white_noise",
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=42,
    )


def test_returns_typed_bundle(ar1_bundle: FingerprintBundle) -> None:
    """The use case should return geometry, fingerprint, and routing objects."""
    assert isinstance(ar1_bundle, FingerprintBundle)
    assert isinstance(ar1_bundle.geometry, AmiInformationGeometry)
    assert isinstance(ar1_bundle.fingerprint, ForecastabilityFingerprint)
    assert isinstance(ar1_bundle.recommendation, RoutingRecommendation)


def test_profile_summary_contains_geometry_fields(ar1_bundle: FingerprintBundle) -> None:
    """The compact summary should surface geometry and routing context together."""
    assert ar1_bundle.profile_summary["max_lag"] == _MAX_LAG
    assert ar1_bundle.profile_summary["n_surrogates"] == _N_SURROGATES
    assert "geometry_method" in ar1_bundle.profile_summary
    assert "signal_to_noise" in ar1_bundle.profile_summary
    assert "confidence" in ar1_bundle.profile_summary
    assert ar1_bundle.profile_summary["input_window_contract"] == (
        "train_window_only_for_rolling_origin"
    )
    assert ar1_bundle.metadata["input_window_contract"] == "train_window_only_for_rolling_origin"


def test_white_noise_abstains_from_family_routing(white_noise_bundle: FingerprintBundle) -> None:
    """The white-noise archetype should emit no primary families."""
    assert white_noise_bundle.geometry.information_horizon == 0
    assert white_noise_bundle.geometry.information_structure == "none"
    assert white_noise_bundle.recommendation.primary_families == []
    assert white_noise_bundle.recommendation.confidence_label == "abstain"


def test_ar1_bundle_keeps_geometry_and_fingerprint_aligned(ar1_bundle: FingerprintBundle) -> None:
    """Geometry and fingerprint should agree on horizon and structure semantics."""
    assert ar1_bundle.fingerprint.signal_to_noise == pytest.approx(
        ar1_bundle.geometry.signal_to_noise
    )
    assert ar1_bundle.fingerprint.information_horizon == ar1_bundle.geometry.information_horizon
    assert ar1_bundle.fingerprint.information_structure == ar1_bundle.geometry.information_structure


def test_monotonic_structure_on_ar1(ar1_bundle: FingerprintBundle) -> None:
    """AR(1) archetype should preserve the monotonic structure contract."""
    assert ar1_bundle.fingerprint.information_structure == "monotonic"


def test_periodic_structure_on_seasonal_series() -> None:
    """Seasonal archetype should preserve the periodic structure contract."""
    bundle = run_forecastability_fingerprint(
        generate_seasonal_periodic(n=_N, period=12, seed=42),
        target_name="seasonal_periodic",
        max_lag=24,
        n_surrogates=_N_SURROGATES,
        random_state=42,
    )
    assert bundle.fingerprint.information_structure == "periodic"


def test_target_name_preserved() -> None:
    """Custom target names should survive the full use case."""
    bundle = run_forecastability_fingerprint(
        generate_ar1_monotonic(n=_N, seed=0),
        target_name="custom_target",
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=0,
    )
    assert bundle.target_name == "custom_target"


def test_custom_routing_config_is_accepted() -> None:
    """A custom routing config should be plumbed through the use case."""
    bundle = run_forecastability_fingerprint(
        generate_ar1_monotonic(n=_N, seed=2),
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=2,
        routing_config=RoutingPolicyConfig(high_nonlinear_share_min=0.8),
    )
    assert isinstance(bundle, FingerprintBundle)


def test_bundle_is_json_serializable(ar1_bundle: FingerprintBundle) -> None:
    """The full bundle should remain JSON-serializable after adding geometry."""
    dumped = json.dumps(ar1_bundle.model_dump())
    assert isinstance(dumped, str)


def test_routing_periodic_to_seasonal_family() -> None:
    """Seasonal archetype should route to at least one seasonal model family."""
    bundle = run_forecastability_fingerprint(
        generate_seasonal_periodic(n=_N, period=12, seed=13),
        max_lag=24,
        n_surrogates=_N_SURROGATES,
        random_state=13,
    )
    assert any(
        family in bundle.recommendation.primary_families
        for family in ("seasonal_naive", "harmonic_regression", "tbats")
    )


def test_max_lag_respected_on_geometry_curve() -> None:
    """The geometry engine should honor the use-case max_lag surface."""
    bundle = run_forecastability_fingerprint(
        generate_seasonal_periodic(n=_N, period=12, seed=4),
        max_lag=12,
        n_surrogates=_N_SURROGATES,
        random_state=4,
    )
    assert len(bundle.geometry.curve) == 12
    for horizon in bundle.fingerprint.informative_horizons:
        assert horizon <= 12


def test_explicit_max_lag_not_reduced_by_default_fractional_cap() -> None:
    """Explicit max_lag should be the evaluated cap, not clipped by default max_lag_frac."""
    bundle = run_forecastability_fingerprint(
        generate_ar1_monotonic(n=120, seed=11),
        max_lag=60,
        n_surrogates=_N_SURROGATES,
        random_state=11,
    )
    assert len(bundle.geometry.curve) == 60
    assert bundle.profile_summary["max_lag"] == 60
    assert bundle.profile_summary["evaluated_max_horizon"] == 60


def test_short_series_raises_value_error() -> None:
    """Short series should still fail fast through the use-case seam."""
    short = np.random.default_rng(0).standard_normal(20)
    with pytest.raises(ValueError):
        run_forecastability_fingerprint(short, max_lag=12, n_surrogates=_N_SURROGATES)


@pytest.mark.parametrize("invalid_ratio", [-0.01, 1.01])
def test_invalid_directness_ratio_raises_value_error(invalid_ratio: float) -> None:
    """directness_ratio must be bounded on [0, 1] at the use-case seam."""
    with pytest.raises(ValueError, match="directness_ratio"):
        run_forecastability_fingerprint(
            generate_ar1_monotonic(n=_N, seed=12),
            max_lag=_MAX_LAG,
            n_surrogates=_N_SURROGATES,
            random_state=12,
            directness_ratio=invalid_ratio,
        )


def test_deterministic_for_same_seed() -> None:
    """Geometry-backed bundles should be deterministic for a fixed random_state."""
    series = generate_ar1_monotonic(n=_N, seed=9)
    first = run_forecastability_fingerprint(
        series,
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=7,
    )
    second = run_forecastability_fingerprint(
        series,
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=7,
    )
    assert first.geometry == second.geometry
    assert first.fingerprint == second.fingerprint
    assert first.recommendation == second.recommendation


def test_geometry_config_allows_use_case_overrides() -> None:
    """Caller-provided geometry config should still allow max_lag and n_surrogates overrides."""
    bundle = run_forecastability_fingerprint(
        generate_ar1_monotonic(n=_N, seed=5),
        max_lag=16,
        n_surrogates=120,
        random_state=5,
        geometry_config=AmiInformationGeometryConfig(n_surrogates=200, max_horizon=8),
    )
    assert len(bundle.geometry.curve) == 16
    assert int(bundle.geometry.metadata["n_surrogates"]) == 120


def test_geometry_config_override_revalidates_n_surrogates_floor() -> None:
    """Use-case overrides should be revalidated against geometry config invariants."""
    with pytest.raises(ValidationError):
        run_forecastability_fingerprint(
            generate_ar1_monotonic(n=_N, seed=6),
            max_lag=12,
            n_surrogates=98,
            random_state=6,
            geometry_config=AmiInformationGeometryConfig(),
        )
