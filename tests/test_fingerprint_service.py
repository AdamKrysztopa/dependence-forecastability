"""Tests for the geometry-backed fingerprint service."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.services.fingerprint_service import (
    build_fingerprint,
    build_forecastability_fingerprint,
)
from forecastability.services.linear_information_service import (
    LinearInformationCurve,
    LinearInformationPoint,
)
from forecastability.utils.synthetic import generate_ar1_monotonic
from forecastability.utils.types import AmiGeometryCurvePoint, AmiInformationGeometry


def _geometry(
    *,
    signal_to_noise: float,
    structure: str,
    rows: list[tuple[int, float | None, float | None, bool, bool]],
    tiebreak: int = 0,
    borderline: int = 0,
) -> AmiInformationGeometry:
    """Build a minimal geometry object for fingerprint tests."""
    informative_horizons = [h for h, _, _, accepted, valid in rows if accepted and valid]
    curve = [
        AmiGeometryCurvePoint(
            horizon=horizon,
            ami_raw=None if corrected is None else corrected + 0.05,
            ami_bias=None if corrected is None else 0.05,
            ami_corrected=corrected,
            tau=tau,
            accepted=accepted,
            valid=valid,
            caution=None if valid else "insufficient_pairs_for_ksg2",
        )
        for horizon, corrected, tau, accepted, valid in rows
    ]
    return AmiInformationGeometry(
        signal_to_noise=signal_to_noise,
        information_horizon=max(informative_horizons, default=0),
        information_structure=structure,  # type: ignore[arg-type]
        informative_horizons=informative_horizons,
        curve=curve,
        metadata={
            "classifier_used_tiebreak": tiebreak,
            "geometry_threshold_borderline": borderline,
        },
    )


def _baseline(values: dict[int, float | None]) -> LinearInformationCurve:
    """Build a minimal linear-information baseline curve."""
    points: list[LinearInformationPoint] = []
    for horizon, gi in values.items():
        if gi is None:
            points.append(
                LinearInformationPoint(
                    horizon=horizon,
                    rho=None,
                    gaussian_information=None,
                    valid=False,
                    caution="undefined_autocorrelation",
                )
            )
            continue
        points.append(
            LinearInformationPoint(
                horizon=horizon,
                rho=0.5,
                gaussian_information=gi,
                valid=True,
                caution=None,
            )
        )
    return LinearInformationCurve(points=points)


def test_information_mass_uses_geometry_acceptance_mask() -> None:
    """Mass should sum corrected AMI over accepted horizons and normalize by valid H."""
    geometry = _geometry(
        signal_to_noise=0.42,
        structure="monotonic",
        rows=[
            (1, 0.30, 0.05, True, True),
            (2, 0.20, 0.04, True, True),
            (3, 0.08, 0.04, False, True),
            (4, 0.10, 0.03, True, True),
            (5, 0.02, 0.03, False, True),
        ],
    )

    fingerprint = build_forecastability_fingerprint(geometry=geometry, baseline=None)

    assert fingerprint.informative_horizons == [1, 2, 4]
    assert fingerprint.information_horizon == 4
    assert fingerprint.information_mass == pytest.approx((0.30 + 0.20 + 0.10) / 5.0)


def test_information_horizon_zero_when_no_informative_horizons() -> None:
    """No accepted horizons should yield the empty fingerprint semantics."""
    geometry = _geometry(
        signal_to_noise=0.0,
        structure="none",
        rows=[
            (1, 0.01, 0.04, False, True),
            (2, 0.00, 0.03, False, True),
            (3, None, None, False, False),
        ],
    )

    fingerprint = build_forecastability_fingerprint(geometry=geometry, baseline=None)

    assert fingerprint.information_structure == "none"
    assert fingerprint.information_horizon == 0
    assert fingerprint.information_mass == 0.0
    assert fingerprint.nonlinear_share == 0.0
    assert fingerprint.informative_horizons == []


def test_signal_to_noise_is_mirrored_from_geometry() -> None:
    """The fingerprint should expose signal_to_noise from the geometry layer."""
    geometry = _geometry(
        signal_to_noise=0.37,
        structure="periodic",
        rows=[
            (1, 0.18, 0.05, True, True),
            (2, 0.05, 0.04, False, True),
        ],
    )

    fingerprint = build_forecastability_fingerprint(geometry=geometry, baseline=None)

    assert fingerprint.signal_to_noise == pytest.approx(0.37)


def test_nonlinear_share_uses_corrected_profile_over_accepted_mask() -> None:
    """nonlinear_share should compare accepted corrected AMI to the linear baseline."""
    geometry = _geometry(
        signal_to_noise=0.48,
        structure="mixed",
        rows=[
            (1, 0.30, 0.05, True, True),
            (2, 0.20, 0.04, True, True),
            (3, 0.08, 0.04, False, True),
            (4, 0.10, 0.03, True, True),
        ],
    )
    baseline = _baseline({1: 0.10, 2: 0.05, 4: 0.05})

    fingerprint = build_forecastability_fingerprint(geometry=geometry, baseline=baseline)

    expected = ((0.30 - 0.10) + (0.20 - 0.05) + (0.10 - 0.05)) / (0.30 + 0.20 + 0.10)
    assert fingerprint.nonlinear_share == pytest.approx(expected)


def test_invalid_baseline_horizons_are_excluded_from_nonlinear_share_denominator() -> None:
    """Horizons with invalid I_G should be excluded conservatively from the ratio."""
    geometry = _geometry(
        signal_to_noise=0.31,
        structure="monotonic",
        rows=[
            (1, 0.40, 0.05, True, True),
            (2, 0.20, 0.04, True, True),
        ],
    )
    baseline = _baseline({1: 0.10, 2: None})

    fingerprint = build_forecastability_fingerprint(geometry=geometry, baseline=baseline)

    assert fingerprint.nonlinear_share == pytest.approx((0.40 - 0.10) / 0.40)
    assert "excluded h=2" in str(fingerprint.metadata)


def test_legacy_build_fingerprint_keeps_backward_compatible_surface() -> None:
    """The pre-geometry wrapper should still produce a valid fingerprint object."""
    series = generate_ar1_monotonic(n=256, seed=42)
    fingerprint = build_fingerprint(
        [0.20, 0.12, 0.08, 0.03],
        horizons=[1, 2, 3, 4],
        significant_horizons=[1, 2, 3],
        series=np.asarray(series),
    )

    assert fingerprint.signal_to_noise >= 0.0
    assert fingerprint.information_horizon == 3
    assert fingerprint.information_mass > 0.0


def test_legacy_build_fingerprint_length_mismatch_raises() -> None:
    """The legacy compatibility wrapper should still guard against length mismatch."""
    with pytest.raises(ValueError, match="ami_values length"):
        build_fingerprint(
            [0.1, 0.2],
            horizons=[1, 2, 3],
            significant_horizons=[1],
        )
