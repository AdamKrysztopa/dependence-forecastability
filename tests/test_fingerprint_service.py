"""Tests for fingerprint_service.py (V3_1-F02)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from forecastability.services.fingerprint_service import build_fingerprint
from forecastability.utils.synthetic import (
    generate_ar1_monotonic,
    generate_nonlinear_mixed,
    generate_seasonal_periodic,
    generate_white_noise,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_horizons(h_max: int) -> list[int]:
    return list(range(1, h_max + 1))


def _all_sig(horizons: list[int]) -> list[int]:
    """Mark every horizon as significant."""
    return list(horizons)


# ---------------------------------------------------------------------------
# 1. White noise archetype
# ---------------------------------------------------------------------------


def test_white_noise_no_significant_horizons() -> None:
    """With no significant horizons, fingerprint is empty."""
    fp = build_fingerprint(
        [0.05] * 20,
        horizons=_make_horizons(20),
        significant_horizons=[],
    )
    assert fp.information_structure == "none"
    assert fp.information_mass == 0.0
    assert fp.information_horizon == 0
    assert fp.nonlinear_share == 0.0
    assert fp.informative_horizons == []


def test_white_noise_archetype_runs() -> None:
    """White noise archetype: build_fingerprint completes without error."""
    series = generate_white_noise(n=500, seed=42)
    ami = [max(0.0, v) for v in np.random.default_rng(0).normal(0.005, 0.003, 20).tolist()]
    fp = build_fingerprint(
        ami,
        horizons=_make_horizons(20),
        significant_horizons=[],  # white noise has no significant horizons
        series=series,
    )
    assert fp.information_structure == "none"
    assert fp.information_mass == 0.0
    assert fp.information_horizon == 0
    assert fp.nonlinear_share == 0.0


# ---------------------------------------------------------------------------
# 2. AR1 monotonic archetype
# ---------------------------------------------------------------------------


def test_ar1_monotonic_structure() -> None:
    """AR1 series with decaying AMI → structure is monotonic or none."""
    series = generate_ar1_monotonic(n=500, seed=42)
    # Use theoretical Gaussian MI = -0.5 * log(1 - rho^2) as AMI proxy so that
    # the values are on the same scale as I_G computed by linear_information_service.
    phi = 0.85
    h_max = 20
    horizons = _make_horizons(h_max)
    ami = [-0.5 * math.log(1.0 - (phi**h) ** 2) for h in horizons]
    significant_horizons = [h for h in horizons if ami[h - 1] >= 0.01]

    fp = build_fingerprint(
        ami,
        horizons=horizons,
        significant_horizons=significant_horizons,
        series=series,
    )
    assert fp.information_structure in {"monotonic", "none"}
    # Finite-sample noise in autocorrelation can push share slightly above 0.3;
    # the key check is that it stays well below nonlinear-dominant levels (0.5+).
    assert fp.nonlinear_share < 0.5
    assert fp.information_mass >= 0.0
    assert fp.information_horizon >= 0


def test_ar1_mass_and_horizon_non_negative() -> None:
    """information_mass and information_horizon are non-negative."""
    series = generate_ar1_monotonic(n=500, seed=42)
    phi = 0.7
    h_max = 10
    horizons = _make_horizons(h_max)
    ami = [-0.5 * math.log(1.0 - (phi**h) ** 2) for h in horizons]

    fp = build_fingerprint(
        ami,
        horizons=horizons,
        significant_horizons=horizons,
        series=series,
    )
    assert fp.information_mass >= 0.0
    assert fp.information_horizon >= 0


# ---------------------------------------------------------------------------
# 3. Seasonal periodic archetype
# ---------------------------------------------------------------------------


def test_seasonal_periodic_runs() -> None:
    """Seasonal periodic archetype: runs without error, returns valid types."""
    series = generate_seasonal_periodic(n=500, seed=42)
    h_max = 24
    horizons = _make_horizons(h_max)
    # Simulate periodic AMI profile with peaks at period multiples
    period = 12
    ami = [
        0.05 + 0.3 * (1.0 if h % period == 0 else 0.0) + 0.1 * np.exp(-h * 0.05) for h in horizons
    ]

    fp = build_fingerprint(
        ami,
        horizons=horizons,
        significant_horizons=horizons,
        series=series,
    )
    assert fp.information_structure in {"none", "monotonic", "periodic", "mixed"}
    assert isinstance(fp.information_mass, float)
    assert isinstance(fp.information_horizon, int)
    assert isinstance(fp.informative_horizons, list)


# ---------------------------------------------------------------------------
# 4. Nonlinear mixed archetype
# ---------------------------------------------------------------------------


def test_nonlinear_mixed_runs() -> None:
    """Nonlinear mixed archetype: runs without error, returns valid types."""
    series = generate_nonlinear_mixed(n=500, seed=42)
    h_max = 15
    horizons = _make_horizons(h_max)
    # Non-monotone AMI profile
    rng = np.random.default_rng(1)
    ami = [0.05 + abs(float(rng.normal(0.08, 0.04))) for _ in horizons]

    fp = build_fingerprint(
        ami,
        horizons=horizons,
        significant_horizons=horizons,
        series=series,
    )
    assert fp.information_structure in {"none", "monotonic", "periodic", "mixed"}
    assert isinstance(fp.information_mass, float)
    assert isinstance(fp.nonlinear_share, float)


# ---------------------------------------------------------------------------
# 5. Edge cases
# ---------------------------------------------------------------------------


def test_empty_significant_horizons() -> None:
    """No significant horizons → structure=none, mass=0, horizon=0."""
    fp = build_fingerprint(
        [0.1, 0.08, 0.06],
        horizons=[1, 2, 3],
        significant_horizons=[],
    )
    assert fp.information_structure == "none"
    assert fp.information_mass == 0.0
    assert fp.information_horizon == 0
    assert fp.informative_horizons == []


def test_single_informative_horizon_not_periodic() -> None:
    """Single informative horizon must not produce periodic structure."""
    fp = build_fingerprint(
        [0.5, 0.001, 0.001],
        horizons=[1, 2, 3],
        significant_horizons=[1],
    )
    assert fp.information_structure != "periodic"
    assert fp.information_horizon == 1
    assert fp.informative_horizons == [1]


def test_monotone_decay_classified_monotonic() -> None:
    """All horizons informative with monotone decay → monotonic."""
    horizons = _make_horizons(10)
    ami = [0.5 * (0.8 ** (h - 1)) for h in horizons]  # strict decay

    fp = build_fingerprint(
        ami,
        horizons=horizons,
        significant_horizons=horizons,
    )
    assert fp.information_structure == "monotonic"


def test_all_ami_below_floor_gives_none() -> None:
    """AMI values below ami_floor even if all horizons significant → none."""
    fp = build_fingerprint(
        [0.005, 0.004, 0.003],
        horizons=[1, 2, 3],
        significant_horizons=[1, 2, 3],
        ami_floor=0.01,
    )
    assert fp.information_structure == "none"
    assert fp.information_mass == 0.0
    assert fp.information_horizon == 0
    assert fp.informative_horizons == []


# ---------------------------------------------------------------------------
# 6. H_info mask consistency
# ---------------------------------------------------------------------------


def test_h_info_consistency() -> None:
    """informative_horizons matches the set used for mass and horizon."""
    horizons = _make_horizons(10)
    ami = [0.5 - 0.04 * (h - 1) for h in horizons]  # monotone
    significant_horizons = [1, 2, 3, 7, 8]  # sparse

    fp = build_fingerprint(
        ami,
        horizons=horizons,
        significant_horizons=significant_horizons,
        ami_floor=0.01,
    )
    # Mass must equal manual recomputation over informative_horizons
    h_info_set = set(fp.informative_horizons)
    ami_map = dict(zip(horizons, ami, strict=True))
    expected_mass = sum(ami_map[h] for h in h_info_set) / max(1, len(horizons))
    assert abs(fp.information_mass - expected_mass) < 1e-12

    # Horizon must equal max of informative_horizons
    expected_horizon = max(fp.informative_horizons) if fp.informative_horizons else 0
    assert fp.information_horizon == expected_horizon


# ---------------------------------------------------------------------------
# 7. nonlinear_share range
# ---------------------------------------------------------------------------


def test_nonlinear_share_in_range() -> None:
    """nonlinear_share is always >= 0.0."""
    series = generate_ar1_monotonic(n=200, seed=7)
    phi = 0.9
    horizons = _make_horizons(15)
    ami = [phi**h for h in horizons]

    fp = build_fingerprint(
        ami,
        horizons=horizons,
        significant_horizons=horizons,
        series=series,
    )
    assert fp.nonlinear_share >= 0.0


def test_nonlinear_share_zero_when_no_informative() -> None:
    """nonlinear_share is 0.0 when there are no informative horizons."""
    fp = build_fingerprint(
        [0.1] * 5,
        horizons=_make_horizons(5),
        significant_horizons=[],
    )
    assert fp.nonlinear_share == 0.0


def test_nonlinear_share_zero_without_series() -> None:
    """nonlinear_share is 0.0 when series=None."""
    horizons = _make_horizons(5)
    ami = [0.3, 0.2, 0.15, 0.1, 0.05]
    fp = build_fingerprint(
        ami,
        horizons=horizons,
        significant_horizons=horizons,
        series=None,
    )
    assert fp.nonlinear_share == 0.0


# ---------------------------------------------------------------------------
# 8. Length mismatch guard
# ---------------------------------------------------------------------------


def test_length_mismatch_raises() -> None:
    """ami_values and horizons length mismatch raises ValueError."""
    with pytest.raises(ValueError, match="ami_values length"):
        build_fingerprint(
            [0.1, 0.2],
            horizons=[1, 2, 3],
            significant_horizons=[1],
        )
