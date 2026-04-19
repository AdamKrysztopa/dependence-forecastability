"""Geometry boundary and threshold regression tests for v0.3.1."""

from __future__ import annotations

import numpy as np

from forecastability.services import ami_information_geometry_service as geometry_service
from forecastability.services.ami_information_geometry_service import (
    AmiInformationGeometryConfig,
    compute_ami_information_geometry,
)


def test_signal_to_noise_below_none_threshold_forces_none() -> None:
    """The null rule should override accepted-horizon presence when signal quality is low."""
    corrected = np.array([0.2, 0.2, 0.2])
    accepted = np.array([True, True, True])
    structure, used_tiebreak = geometry_service._classify_information_structure(
        corrected,
        accepted,
        signal_to_noise=0.049,
        information_horizon=3,
        config=AmiInformationGeometryConfig(signal_to_noise_none_threshold=0.05),
    )

    assert structure == "none"
    assert used_tiebreak is False


def test_horizon_acceptance_uses_strictly_greater_than_three_tau(
    monkeypatch,
) -> None:
    """Acceptance should follow I_c(h) > 3 * tau(h), not >=."""

    def fake_raw_profile(
        series: np.ndarray,
        *,
        max_horizon: int,
        config: AmiInformationGeometryConfig,
        random_state: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        del series, config, random_state
        assert max_horizon == 3
        raw = np.array([0.399, 0.36, 0.37])
        valid = np.array([True, True, True])
        return raw, valid

    def fake_shuffle_matrix(
        series: np.ndarray,
        *,
        max_horizon: int,
        config: AmiInformationGeometryConfig,
        random_state: int,
    ) -> np.ndarray:
        del series, config, random_state
        assert max_horizon == 3
        base = np.array([0.10, 0.02, 0.12])
        return np.tile(base, (99, 1))

    monkeypatch.setattr(geometry_service, "_compute_raw_profile", fake_raw_profile)
    monkeypatch.setattr(geometry_service, "_compute_shuffle_matrix", fake_shuffle_matrix)

    series = np.linspace(-1.0, 1.0, 120)
    geometry = compute_ami_information_geometry(
        series,
        config=AmiInformationGeometryConfig(
            min_n=80,
            n_surrogates=99,
            max_horizon=3,
            horizon_multiplier_threshold=3.0,
        ),
        random_state=42,
    )

    assert geometry.informative_horizons == [2]
    accepted_flags = [point.accepted for point in geometry.curve]
    assert accepted_flags == [False, True, False]