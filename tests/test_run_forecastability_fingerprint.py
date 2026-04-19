"""Tests for the geometry-backed forecastability fingerprint use case."""

from __future__ import annotations

import json

import numpy as np
import pytest

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


def test_white_noise_routes_to_naive_families(white_noise_bundle: FingerprintBundle) -> None:
    """The white-noise archetype should downscope to naive-style families."""
    assert white_noise_bundle.geometry.information_horizon == 0
    assert white_noise_bundle.geometry.information_structure == "none"
    assert any(
        family in white_noise_bundle.recommendation.primary_families
        for family in ("naive", "seasonal_naive", "downscope")
    )


def test_ar1_bundle_keeps_geometry_and_fingerprint_aligned(ar1_bundle: FingerprintBundle) -> None:
    """Geometry and fingerprint should agree on horizon and structure semantics."""
    assert ar1_bundle.fingerprint.signal_to_noise == pytest.approx(
        ar1_bundle.geometry.signal_to_noise
    )
    assert ar1_bundle.fingerprint.information_horizon == ar1_bundle.geometry.information_horizon
    assert ar1_bundle.fingerprint.information_structure == ar1_bundle.geometry.information_structure


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


def test_short_series_raises_value_error() -> None:
    """Short series should still fail fast through the use-case seam."""
    short = np.random.default_rng(0).standard_normal(20)
    with pytest.raises(ValueError):
        run_forecastability_fingerprint(short, max_lag=12, n_surrogates=_N_SURROGATES)


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
