"""Tests for the geometry-aware routing policy service."""

from __future__ import annotations

import math

import pytest

from forecastability.services.fingerprint_service import FingerprintThresholdConfig
from forecastability.services.routing_policy_service import (
    RoutingPolicyConfig,
    route_fingerprint,
)
from forecastability.utils.types import ForecastabilityFingerprint

_DEFAULT_CFG = RoutingPolicyConfig()


def _fp(
    *,
    structure: str = "monotonic",
    mass: float = 0.20,
    nl_share: float = 0.05,
    signal_to_noise: float = 0.40,
    horizon: int = 5,
    informative_horizons: list[int] | None = None,
    directness_ratio: float | None = None,
    metadata: dict[str, str | int | float] | None = None,
) -> ForecastabilityFingerprint:
    """Convenience factory for routing-policy tests."""
    return ForecastabilityFingerprint(
        information_mass=mass,
        information_horizon=horizon,
        information_structure=structure,  # type: ignore[arg-type]
        nonlinear_share=nl_share,
        signal_to_noise=signal_to_noise,
        directness_ratio=directness_ratio,
        informative_horizons=informative_horizons if informative_horizons is not None else [],
        metadata=metadata or {},
    )


def test_routing_none_structure_abstains_from_family_routing() -> None:
    """A none-structure fingerprint must abstain from family-level routing."""
    rec = route_fingerprint(_fp(structure="none", mass=0.0, nl_share=0.0, signal_to_noise=0.0))
    assert rec.primary_families == []
    assert rec.confidence_label == "abstain"


def test_routing_periodic_to_seasonal_family() -> None:
    """A periodic fingerprint with low nonlinear share should route seasonally."""
    rec = route_fingerprint(_fp(structure="periodic", mass=0.18, nl_share=0.05))
    assert any(
        family in rec.primary_families
        for family in ("seasonal_naive", "harmonic_regression", "tbats")
    )


def test_routing_nonlinear_to_nonlinear_family() -> None:
    """High nonlinear share with mixed structure should route nonlinearly."""
    rec = route_fingerprint(_fp(structure="mixed", mass=0.20, nl_share=0.50))
    assert any(f in rec.primary_families for f in ("tree_on_lags", "tcn", "nbeats", "nhits"))


def test_routing_monotonic_high_directness_to_linear_family() -> None:
    """Monotonic, low-nonlinear, high-directness fingerprints should route linearly."""
    rec = route_fingerprint(
        _fp(
            structure="monotonic",
            mass=0.20,
            nl_share=0.05,
            directness_ratio=0.80,
            informative_horizons=[1, 2, 3, 4, 5],
        )
    )
    assert any(f in rec.primary_families for f in ("arima", "ets", "linear_state_space"))


def test_routing_low_mass_to_naive() -> None:
    """Low mass should override a non-none structure and downscope the route."""
    rec = route_fingerprint(_fp(structure="monotonic", mass=0.01, nl_share=0.05))
    assert "naive" in rec.primary_families


def test_confidence_high_when_no_penalties() -> None:
    """A clean monotonic fingerprint should yield high confidence."""
    rec = route_fingerprint(
        _fp(
            structure="monotonic",
            mass=0.20,
            nl_share=0.05,
            signal_to_noise=0.40,
            directness_ratio=0.80,
            informative_horizons=[1, 2, 3, 4, 5],
        )
    )
    assert rec.confidence_label == "high"


def test_confidence_medium_when_only_near_threshold_penalty() -> None:
    """One threshold-margin penalty should downgrade confidence to medium."""
    rec = route_fingerprint(
        _fp(
            structure="monotonic",
            mass=0.101,
            nl_share=0.05,
            signal_to_noise=0.40,
            directness_ratio=0.80,
            informative_horizons=[1, 2, 3, 4, 5],
        )
    )
    assert rec.confidence_label == "medium"
    assert "near_threshold" in rec.caution_flags


def test_confidence_low_when_multiple_penalties_fire() -> None:
    """Mixed structure and weak signal quality should yield low confidence."""
    rec = route_fingerprint(
        _fp(
            structure="mixed",
            mass=0.20,
            nl_share=0.05,
            signal_to_noise=0.05,
            informative_horizons=[1, 2],
        )
    )
    assert rec.confidence_label == "low"


def test_low_signal_to_noise_adds_caution_and_penalty() -> None:
    """Weak signal quality should appear explicitly in the caution surface."""
    rec = route_fingerprint(
        _fp(
            structure="monotonic",
            mass=0.20,
            nl_share=0.05,
            signal_to_noise=0.05,
            informative_horizons=[1, 2, 3, 4],
        ),
        fingerprint_config=FingerprintThresholdConfig(
            low_signal_to_noise_confidence_threshold=0.10
        ),
    )
    assert "low_signal_to_noise" in rec.caution_flags
    assert rec.metadata["low_signal_quality_penalty"] == 1


def test_low_signal_to_noise_downgrades_confidence() -> None:
    """Low signal quality should reduce confidence even without other major conflicts."""
    rec = route_fingerprint(
        _fp(
            structure="monotonic",
            mass=0.20,
            nl_share=0.05,
            signal_to_noise=0.05,
            directness_ratio=0.80,
            informative_horizons=[1, 2, 3, 4],
        ),
        fingerprint_config=FingerprintThresholdConfig(
            low_signal_to_noise_confidence_threshold=0.10
        ),
    )
    assert rec.confidence_label in {"medium", "low"}


def test_low_directness_adds_caution() -> None:
    """Low directness should be surfaced separately from nonlinear share."""
    rec = route_fingerprint(
        _fp(
            structure="monotonic",
            mass=0.20,
            nl_share=0.05,
            directness_ratio=0.20,
            informative_horizons=[1, 2, 3, 4],
        )
    )
    assert "low_directness" in rec.caution_flags


def test_geometry_threshold_borderline_flag_is_propagated() -> None:
    """Geometry-borderline metadata should surface as a routing caution."""
    rec = route_fingerprint(
        _fp(
            metadata={"geometry_threshold_borderline": 1},
            informative_horizons=[1, 2, 3, 4],
        )
    )
    assert "geometry_threshold_borderline" in rec.caution_flags


def test_string_metadata_flags_are_parsed_robustly() -> None:
    """String-like metadata flags should be parsed safely instead of cast-crashing."""
    rec_true = route_fingerprint(
        _fp(
            metadata={
                "classifier_used_tiebreak": "true",
                "geometry_threshold_borderline": "1",
            },
            informative_horizons=[1, 2, 3, 4],
        )
    )
    rec_false = route_fingerprint(
        _fp(
            metadata={
                "classifier_used_tiebreak": "false",
                "geometry_threshold_borderline": "0",
            },
            informative_horizons=[1, 2, 3, 4],
        )
    )
    assert rec_true.metadata["taxonomy_uncertainty_penalty"] == 1
    assert "geometry_threshold_borderline" in rec_true.caution_flags
    assert "geometry_threshold_borderline" not in rec_false.caution_flags


def test_custom_config_overrides_nonlinear_threshold() -> None:
    """Custom configs should still be honored after the geometry refactor."""
    rec = route_fingerprint(
        _fp(
            structure="monotonic",
            mass=0.20,
            nl_share=0.50,
            directness_ratio=0.80,
            informative_horizons=[1, 2, 3, 4],
        ),
        config=RoutingPolicyConfig(high_nonlinear_share_min=0.80),
    )
    assert any(f in rec.primary_families for f in ("arima", "ets", "linear_state_space"))


def test_metadata_contains_policy_version() -> None:
    """The routing metadata should retain the versioned policy identifier."""
    rec = route_fingerprint(_fp(informative_horizons=[1, 2, 3, 4]))
    assert rec.metadata["policy_version"] == _DEFAULT_CFG.policy_version


@pytest.mark.parametrize("invalid_ratio", [-0.01, 1.01, math.inf, math.nan])
def test_route_fingerprint_rejects_invalid_directness_ratio(invalid_ratio: float) -> None:
    """Routing seam should reject out-of-contract directness_ratio values."""
    with pytest.raises(ValueError, match="directness_ratio"):
        route_fingerprint(
            _fp(
                structure="monotonic",
                mass=0.20,
                nl_share=0.05,
                directness_ratio=invalid_ratio,
                informative_horizons=[1, 2, 3, 4],
            )
        )
