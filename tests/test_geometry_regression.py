"""Geometry boundary and threshold regression tests for v0.3.1."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from forecastability.services import ami_information_geometry_service as geometry_service
from forecastability.services.ami_information_geometry_service import (
    AmiInformationGeometryConfig,
    compute_ami_information_geometry,
)

_GEOMETRY_EXPECTED_DIR = Path("docs/fixtures/geometry_regression/expected")
_TIEBREAK_FIXTURE_PATH = _GEOMETRY_EXPECTED_DIR / "tiebreak_metadata_case.json"


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


def test_geometry_classifier_tiebreak_metadata_is_emitted(monkeypatch) -> None:
    """Crafted corrected profiles should emit classifier_used_tiebreak metadata."""

    fixture_payload = json.loads(_TIEBREAK_FIXTURE_PATH.read_text())
    expected_tiebreak = int(fixture_payload["expected_classifier_used_tiebreak"])

    def fake_raw_profile(
        series: np.ndarray,
        *,
        max_horizon: int,
        config: AmiInformationGeometryConfig,
        random_state: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        del series, config, random_state
        assert max_horizon == 6
        corrected = np.array([0.52, 0.20, 0.15, 0.10, 0.08, 0.05])
        bias = np.full(6, 0.01)
        return corrected + bias, np.array([True, True, True, True, True, True])

    def fake_shuffle_matrix(
        series: np.ndarray,
        *,
        max_horizon: int,
        config: AmiInformationGeometryConfig,
        random_state: int,
    ) -> np.ndarray:
        del series, config, random_state
        assert max_horizon == 6
        return np.tile(np.full(6, 0.01), (99, 1))

    monkeypatch.setattr(geometry_service, "_compute_raw_profile", fake_raw_profile)
    monkeypatch.setattr(geometry_service, "_compute_shuffle_matrix", fake_shuffle_matrix)

    geometry = compute_ami_information_geometry(
        np.linspace(-1.0, 1.0, 120),
        config=AmiInformationGeometryConfig(
            min_n=80,
            n_surrogates=99,
            max_horizon=6,
            signal_to_noise_none_threshold=0.05,
        ),
        random_state=7,
    )

    assert int(geometry.metadata.get("classifier_used_tiebreak", 0)) == expected_tiebreak


def test_geometry_expected_fixture_contract_present() -> None:
    """Geometry regression fixtures should expose at least one stable expected file."""
    assert _GEOMETRY_EXPECTED_DIR.exists(), (
        f"Missing expected fixture dir: {_GEOMETRY_EXPECTED_DIR}"
    )
    assert _TIEBREAK_FIXTURE_PATH.exists(), (
        f"Missing expected fixture file: {_TIEBREAK_FIXTURE_PATH}"
    )