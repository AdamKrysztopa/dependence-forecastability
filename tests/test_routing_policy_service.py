"""Tests for routing_policy_service (V3_1-F06)."""

from __future__ import annotations

import pytest

from forecastability.services.routing_policy_service import (
    RoutingPolicyConfig,
    route_fingerprint,
)
from forecastability.utils.types import ForecastabilityFingerprint

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_CFG = RoutingPolicyConfig()


def _fp(
    *,
    structure: str = "monotonic",
    mass: float = 0.2,
    nl_share: float = 0.05,
    horizon: int = 5,
    informative_horizons: list[int] | None = None,
    directness_ratio: float | None = None,
) -> ForecastabilityFingerprint:
    """Convenience factory for test fingerprints."""
    return ForecastabilityFingerprint(
        information_mass=mass,
        information_horizon=horizon,
        information_structure=structure,  # type: ignore[arg-type]
        nonlinear_share=nl_share,
        directness_ratio=directness_ratio,
        informative_horizons=informative_horizons if informative_horizons is not None else [],
    )


# ---------------------------------------------------------------------------
# Routing bucket tests
# ---------------------------------------------------------------------------


def test_routing_white_noise_to_naive_family() -> None:
    """structure 'none' must route to naive / downscope primary families."""
    fp = _fp(structure="none", mass=0.0, nl_share=0.01)
    rec = route_fingerprint(fp)
    assert any(f in rec.primary_families for f in ("naive", "downscope", "seasonal_naive"))


def test_routing_periodic_to_seasonal_family() -> None:
    """structure 'periodic' must route to seasonal primary families."""
    fp = _fp(structure="periodic", mass=0.15, nl_share=0.05)
    rec = route_fingerprint(fp)
    assert any(
        f in rec.primary_families for f in ("seasonal_naive", "tbats", "seasonal_state_space")
    )


def test_routing_nonlinear_to_nonlinear_family() -> None:
    """High nonlinear_share with 'mixed' structure routes to nonlinear families."""
    fp = _fp(structure="mixed", mass=0.2, nl_share=0.5)
    rec = route_fingerprint(fp)
    assert any(f in rec.primary_families for f in ("nbeats", "tree_on_lags", "nhits", "tcn"))


def test_routing_ar1_to_linear_family() -> None:
    """'monotonic' structure with high mass and low nonlinear_share routes to linear families."""
    fp = _fp(structure="monotonic", mass=0.2, nl_share=0.05, informative_horizons=[1, 2, 3, 4, 5])
    rec = route_fingerprint(fp)
    assert any(f in rec.primary_families for f in ("arima", "ets"))


def test_routing_low_mass_to_naive() -> None:
    """Low mass with non-none structure routes to naive primary families."""
    fp = _fp(structure="monotonic", mass=0.01, nl_share=0.05)
    rec = route_fingerprint(fp)
    assert "naive" in rec.primary_families


# ---------------------------------------------------------------------------
# Confidence level tests
# ---------------------------------------------------------------------------


def test_confidence_high_when_no_penalties() -> None:
    """Unambiguous fingerprint (0 penalties) must yield confidence 'high'."""
    # mass=0.2 (far above 0.05), nl=0.05 (far below 0.3),
    # directness=0.8 (far above 0.4), 5 informative horizons (>= 3)
    fp = _fp(
        structure="monotonic",
        mass=0.2,
        nl_share=0.05,
        directness_ratio=0.8,
        informative_horizons=[1, 2, 3, 4, 5],
    )
    rec = route_fingerprint(fp)
    assert rec.confidence_label == "high"


def test_confidence_medium_when_one_penalty() -> None:
    """A single near-threshold penalty must yield confidence 'medium'."""
    # mass=0.052 → |0.052-0.05|/0.05 = 0.04 < 0.1 → near_threshold
    # nl and directness well away from their thresholds → no other threshold penalty
    # structure=monotonic, 5 informative_horizons → taxonomy_penalty=0
    # signal_conflict=0 (linear route + low nl)
    fp = _fp(
        structure="monotonic",
        mass=0.052,
        nl_share=0.05,
        directness_ratio=0.8,
        informative_horizons=[1, 2, 3, 4, 5],
    )
    rec = route_fingerprint(fp)
    assert rec.confidence_label == "medium"


def test_confidence_low_when_two_penalties() -> None:
    """Two penalties (near-threshold mass + mixed structure) must yield confidence 'low'."""
    # near_threshold → threshold_penalty=1
    # structure="mixed" → taxonomy_penalty=1
    # total=2 → "low"
    fp = _fp(
        structure="mixed",
        mass=0.052,
        nl_share=0.05,
    )
    rec = route_fingerprint(fp)
    assert rec.confidence_label == "low"


# ---------------------------------------------------------------------------
# Caution flag tests
# ---------------------------------------------------------------------------


def test_caution_near_threshold_flag() -> None:
    """Value near decision threshold must produce 'near_threshold' caution flag."""
    fp = _fp(structure="monotonic", mass=0.052, nl_share=0.05, informative_horizons=[1, 2, 3])
    rec = route_fingerprint(fp)
    assert "near_threshold" in rec.caution_flags


def test_caution_low_directness_flag() -> None:
    """directness_ratio below threshold must produce 'low_directness' caution flag."""
    fp = _fp(
        structure="monotonic",
        mass=0.2,
        nl_share=0.05,
        directness_ratio=0.2,
    )
    rec = route_fingerprint(fp)
    assert "low_directness" in rec.caution_flags


def test_caution_mixed_structure_flag() -> None:
    """'mixed' information_structure must produce 'mixed_structure' caution flag."""
    fp = _fp(structure="mixed", mass=0.2, nl_share=0.05)
    rec = route_fingerprint(fp)
    assert "mixed_structure" in rec.caution_flags


def test_caution_high_nonlinear_share_flag() -> None:
    """nonlinear_share >= threshold must produce 'high_nonlinear_share' caution flag."""
    fp = _fp(structure="monotonic", mass=0.2, nl_share=0.5)
    rec = route_fingerprint(fp)
    assert "high_nonlinear_share" in rec.caution_flags


# ---------------------------------------------------------------------------
# Config and API tests
# ---------------------------------------------------------------------------


def test_routing_uses_custom_config() -> None:
    """Custom config thresholds must override defaults."""
    # Raise mass threshold so that mass=0.2 is still "high" but nl threshold is 0.8
    # so nl=0.5 is treated as low — routing should go to linear families
    custom_cfg = RoutingPolicyConfig(nonlinear_share_high_threshold=0.8)
    fp = _fp(
        structure="monotonic",
        mass=0.2,
        nl_share=0.5,
        informative_horizons=[1, 2, 3, 4],
    )
    rec = route_fingerprint(fp, config=custom_cfg)
    # With custom threshold 0.8 and nl=0.5 → low_nl → linear route
    assert any(f in rec.primary_families for f in ("arima", "ets"))


def test_directness_ratio_none_skips_directness_caution() -> None:
    """When directness_ratio is None, 'low_directness' must not appear in caution_flags."""
    fp = _fp(structure="monotonic", mass=0.2, nl_share=0.05, directness_ratio=None)
    rec = route_fingerprint(fp)
    assert "low_directness" not in rec.caution_flags


def test_metadata_contains_policy_version() -> None:
    """metadata must contain the policy_version key equal to the config version."""
    fp = _fp(structure="monotonic", mass=0.2, nl_share=0.05, informative_horizons=[1, 2, 3])
    rec = route_fingerprint(fp)
    assert rec.metadata.get("policy_version") == _DEFAULT_CFG.policy_version


def test_low_directness_adds_caution_and_secondary_families() -> None:
    """Low directness_ratio must add 'low_directness' caution and enrich secondary families."""
    fp = _fp(
        structure="monotonic",
        mass=0.2,
        nl_share=0.05,
        directness_ratio=0.2,  # below threshold → not high_directness
    )
    rec = route_fingerprint(fp)
    assert "low_directness" in rec.caution_flags
    # low directness, high mass, low nl, monotonic →
    # secondary should include linear_state_space and dynamic_regression
    assert any(f in rec.secondary_families for f in ("linear_state_space", "dynamic_regression"))


def test_rationale_is_non_empty() -> None:
    """rationale list must be non-empty for any non-trivial fingerprint."""
    for structure in ("monotonic", "periodic", "mixed", "none"):
        fp = _fp(structure=structure, mass=0.15, nl_share=0.1)
        rec = route_fingerprint(fp)
        assert len(rec.rationale) > 0, f"Empty rationale for structure={structure!r}"


# ---------------------------------------------------------------------------
# Additional coverage
# ---------------------------------------------------------------------------


def test_routing_periodic_has_harmonic_regression_secondary() -> None:
    """Periodic routing must include 'harmonic_regression' in secondary families."""
    fp = _fp(structure="periodic", mass=0.15, nl_share=0.05)
    rec = route_fingerprint(fp)
    assert "harmonic_regression" in rec.secondary_families


def test_routing_none_structure_has_no_secondary() -> None:
    """White-noise routing must have empty secondary families."""
    fp = _fp(structure="none", mass=0.0, nl_share=0.0)
    rec = route_fingerprint(fp)
    assert rec.secondary_families == []


@pytest.mark.parametrize("policy_version", ["v0.3.1"])
def test_default_config_policy_version(policy_version: str) -> None:
    """Default RoutingPolicyConfig must have the expected policy_version."""
    assert _DEFAULT_CFG.policy_version == policy_version
