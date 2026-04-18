"""Tests for run_forecastability_fingerprint use case (V3_1-F04)."""

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
    FingerprintBundle,
    ForecastabilityFingerprint,
    RoutingRecommendation,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_N = 500
_MAX_LAG = 12
_N_SURROGATES = 99


@pytest.fixture(scope="module")
def ar1_bundle() -> FingerprintBundle:
    series = generate_ar1_monotonic(n=1000, seed=42)
    return run_forecastability_fingerprint(
        series,
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=42,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_fingerprint_bundle(ar1_bundle: FingerprintBundle) -> None:
    """Call with AR1 series returns a FingerprintBundle instance."""
    assert isinstance(ar1_bundle, FingerprintBundle)


def test_fingerprint_bundle_has_all_four_fields(ar1_bundle: FingerprintBundle) -> None:
    """All four structural fields of FingerprintBundle are present and typed."""
    assert isinstance(ar1_bundle.fingerprint, ForecastabilityFingerprint)
    assert isinstance(ar1_bundle.recommendation, RoutingRecommendation)
    assert isinstance(ar1_bundle.profile_summary, dict)
    assert isinstance(ar1_bundle.target_name, str)


def test_recommendation_is_non_empty(ar1_bundle: FingerprintBundle) -> None:
    """Routing recommendation has at least one primary model family."""
    assert len(ar1_bundle.recommendation.primary_families) > 0


def test_white_noise_structure_is_none_or_has_naive_routing() -> None:
    """White noise → structure 'none' OR primary families include a naive/downscope label."""
    series = generate_white_noise(n=_N, seed=42)
    bundle = run_forecastability_fingerprint(
        series,
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=42,
    )
    naive_like = {"naive", "seasonal_naive", "theta", "ets"}
    structure_is_none = bundle.fingerprint.information_structure == "none"
    has_naive_primary = bool(naive_like & set(bundle.recommendation.primary_families))
    assert structure_is_none or has_naive_primary, (
        f"Expected 'none' structure or naive routing for white noise; got "
        f"structure={bundle.fingerprint.information_structure}, "
        f"primary={bundle.recommendation.primary_families}"
    )


def test_ar1_series_structure_monotonic_or_has_linear_routing(
    ar1_bundle: FingerprintBundle,
) -> None:
    """AR1 series → structure 'monotonic' OR primary families include ARIMA/ETS.

    Note: Phase-randomisation preserves linear autocorrelation, so a purely
    linear AR(1) may not produce surrogate-significant lags (the test correctly
    detects no nonlinear structure beyond linear).  Accept either route.
    """
    linear_like = {"arima", "ets", "linear_state_space", "dynamic_regression"}
    structure_ok = ar1_bundle.fingerprint.information_structure in {"monotonic", "none"}
    has_linear_primary = bool(linear_like & set(ar1_bundle.recommendation.primary_families))
    assert structure_ok or has_linear_primary, (
        f"Expected monotonic/none structure or linear routing for AR1; got "
        f"structure={ar1_bundle.fingerprint.information_structure}, "
        f"primary={ar1_bundle.recommendation.primary_families}"
    )


def test_target_name_preserved() -> None:
    """Custom target_name is stored in the bundle."""
    series = generate_ar1_monotonic(n=_N, seed=0)
    bundle = run_forecastability_fingerprint(
        series,
        target_name="my_custom_series",
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=0,
    )
    assert bundle.target_name == "my_custom_series"


def test_profile_summary_contains_max_lag_and_sig_count() -> None:
    """profile_summary dict contains 'max_lag' and 'sig_horizons_count' keys."""
    series = generate_ar1_monotonic(n=_N, seed=1)
    bundle = run_forecastability_fingerprint(
        series,
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=1,
    )
    assert "max_lag" in bundle.profile_summary
    assert "sig_horizons_count" in bundle.profile_summary
    assert bundle.profile_summary["max_lag"] == _MAX_LAG


def test_short_series_raises_value_error() -> None:
    """Series shorter than max_lag + 10 raises ValueError."""
    short = np.random.default_rng(0).standard_normal(10)
    with pytest.raises(ValueError):
        run_forecastability_fingerprint(short, max_lag=12, n_surrogates=_N_SURROGATES)


def test_deterministic_for_same_seed() -> None:
    """Two calls with identical seed produce identical fingerprints."""
    series = generate_ar1_monotonic(n=_N, seed=99)
    b1 = run_forecastability_fingerprint(
        series, max_lag=_MAX_LAG, n_surrogates=_N_SURROGATES, random_state=7
    )
    b2 = run_forecastability_fingerprint(
        series, max_lag=_MAX_LAG, n_surrogates=_N_SURROGATES, random_state=7
    )
    assert b1.fingerprint == b2.fingerprint


def test_custom_routing_config_accepted() -> None:
    """Passing a custom RoutingPolicyConfig does not raise."""
    series = generate_ar1_monotonic(n=_N, seed=2)
    config = RoutingPolicyConfig(mass_high_threshold=0.03)
    bundle = run_forecastability_fingerprint(
        series,
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=2,
        routing_config=config,
    )
    assert isinstance(bundle, FingerprintBundle)


def test_bundle_is_json_serializable() -> None:
    """bundle.model_dump() can be serialised to JSON without error."""
    series = generate_ar1_monotonic(n=_N, seed=3)
    bundle = run_forecastability_fingerprint(
        series,
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=3,
    )
    raw = bundle.model_dump()
    dumped = json.dumps(raw)
    assert isinstance(dumped, str)


def test_max_lag_respected() -> None:
    """With max_lag=12 the fingerprint's informative_horizons are all <= 12."""
    series = generate_seasonal_periodic(n=_N, period=12, seed=4)
    bundle = run_forecastability_fingerprint(
        series,
        max_lag=12,
        n_surrogates=_N_SURROGATES,
        random_state=4,
    )
    for h in bundle.fingerprint.informative_horizons:
        assert h <= 12, f"horizon {h} exceeds max_lag=12"
    assert bundle.profile_summary["max_lag"] == 12
