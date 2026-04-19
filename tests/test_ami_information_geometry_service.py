"""Tests for the AMI Information Geometry service."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.services import ami_information_geometry_service as geometry_service
from forecastability.services.ami_information_geometry_service import (
    AmiInformationGeometryConfig,
    compute_ami_information_geometry,
)
from forecastability.utils.synthetic import generate_seasonal_periodic, generate_white_noise


def _config(*, max_horizon: int) -> AmiInformationGeometryConfig:
    """Build a test-friendly geometry config."""
    return AmiInformationGeometryConfig(
        n_surrogates=99,
        max_horizon=max_horizon,
        n_jobs=1,
    )


def test_white_noise_geometry_has_low_signal_to_noise() -> None:
    """White noise should collapse to a low-signal geometry profile."""
    series = generate_white_noise(n=240, seed=42)
    geometry = compute_ami_information_geometry(
        series,
        config=_config(max_horizon=12),
        random_state=42,
    )

    assert 0.0 <= geometry.signal_to_noise <= 1.0
    assert geometry.signal_to_noise < 0.30
    assert geometry.information_structure == "none"
    assert geometry.information_horizon == 0


def test_seasonal_periodic_geometry_detects_periodic_structure() -> None:
    """The canonical seasonal archetype should register repeated accepted peaks."""
    series = generate_seasonal_periodic(n=360, period=12, seed=42)
    geometry = compute_ami_information_geometry(
        series,
        config=_config(max_horizon=24),
        random_state=42,
    )

    assert geometry.signal_to_noise > 0.10
    assert geometry.information_structure == "periodic"
    assert geometry.information_horizon >= 12
    assert len(geometry.informative_horizons) > 0


def test_longer_seasonal_window_stays_periodic() -> None:
    """Longer evaluated windows should not collapse the seasonal archetype to monotonic."""
    series = generate_seasonal_periodic(n=600, period=12, seed=42)
    geometry = compute_ami_information_geometry(
        series,
        config=_config(max_horizon=24),
        random_state=42,
    )

    assert geometry.information_structure == "periodic"
    assert geometry.information_horizon == 24


def test_geometry_curve_points_expose_threshold_fields() -> None:
    """The returned curve points should include corrected AMI and tau values."""
    series = generate_seasonal_periodic(n=240, period=12, seed=9)
    geometry = compute_ami_information_geometry(
        series,
        config=_config(max_horizon=12),
        random_state=9,
    )

    assert len(geometry.curve) == 12
    first_valid = next(point for point in geometry.curve if point.valid)
    assert first_valid.ami_raw is not None
    assert first_valid.ami_bias is not None
    assert first_valid.ami_corrected is not None
    assert first_valid.tau is not None


def test_short_series_rejected_at_geometry_min_n() -> None:
    """The geometry service should reject series shorter than the configured minimum."""
    series = generate_white_noise(n=60, seed=0)
    with pytest.raises(ValueError):
        compute_ami_information_geometry(
            series,
            config=AmiInformationGeometryConfig(n_surrogates=99, min_n=80, max_horizon=12),
            random_state=0,
        )


def test_corrected_profile_clamps_negative_values_to_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """When raw AMI drops below surrogate bias, corrected AMI should floor at zero."""

    def fake_raw_profile(
        series: np.ndarray,
        *,
        max_horizon: int,
        config: AmiInformationGeometryConfig,
        random_state: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        del series, config, random_state
        assert max_horizon == 2
        return np.array([0.05, 0.30]), np.array([True, True])

    def fake_shuffle_matrix(
        series: np.ndarray,
        *,
        max_horizon: int,
        config: AmiInformationGeometryConfig,
        random_state: int,
    ) -> np.ndarray:
        del series, config, random_state
        assert max_horizon == 2
        return np.tile(np.array([0.10, 0.05]), (99, 1))

    monkeypatch.setattr(geometry_service, "_compute_raw_profile", fake_raw_profile)
    monkeypatch.setattr(geometry_service, "_compute_shuffle_matrix", fake_shuffle_matrix)

    series = np.linspace(-1.0, 1.0, 120)
    geometry = compute_ami_information_geometry(
        series,
        config=AmiInformationGeometryConfig(min_n=80, n_surrogates=99, max_horizon=2),
        random_state=123,
    )

    first_point = geometry.curve[0]
    assert first_point.valid is True
    assert first_point.ami_corrected == pytest.approx(0.0)
    assert first_point.accepted is False
    assert 0.0 <= geometry.signal_to_noise <= 1.0
