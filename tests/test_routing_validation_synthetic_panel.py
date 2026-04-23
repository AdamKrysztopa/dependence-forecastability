"""Tests for the phase-0 synthetic routing-validation archetype panel."""

from __future__ import annotations

import hashlib

import numpy as np

from forecastability.utils.synthetic import (
    ExpectedFamilyMetadata,
    generate_routing_validation_archetypes,
)


def _digest_first32(series: np.ndarray) -> str:
    first = np.asarray(series[:32], dtype=np.float64)
    return hashlib.sha256(first.tobytes()).hexdigest()


def test_routing_validation_archetype_panel_has_expected_cases() -> None:
    """Phase-0 synthetic panel must expose all ten canonical archetypes."""
    panel = generate_routing_validation_archetypes(n=128, seed=42)
    assert set(panel.keys()) == {
        "white_noise",
        "ar1",
        "seasonal",
        "weak_seasonal_near_threshold",
        "nonlinear_mixed",
        "structural_break",
        "long_memory",
        "mediated_low_directness",
        "exogenous_driven",
        "low_directness_high_penalty",
    }


def test_routing_validation_archetypes_return_typed_metadata() -> None:
    """Every panel row must return (series, ExpectedFamilyMetadata)."""
    panel = generate_routing_validation_archetypes(n=96, seed=42)

    for series, metadata in panel.values():
        assert isinstance(series, np.ndarray)
        assert isinstance(metadata, ExpectedFamilyMetadata)
        assert len(series) == 96
        assert metadata.expected_primary_families


def test_routing_validation_archetype_panel_is_deterministic_by_seed() -> None:
    """Panel outputs must be deterministic for identical seed and n."""
    first = generate_routing_validation_archetypes(n=128, seed=7)
    second = generate_routing_validation_archetypes(n=128, seed=7)

    for key in first:
        first_series, first_meta = first[key]
        second_series, second_meta = second[key]
        assert np.array_equal(first_series, second_series)
        assert first_meta == second_meta


def test_routing_validation_archetype_first32_fingerprints() -> None:
    """Freeze first-32-sample fingerprints for regression stability."""
    panel = generate_routing_validation_archetypes(n=128, seed=42)
    observed = {
        key: _digest_first32(series_metadata[0]) for key, series_metadata in panel.items()
    }

    expected = {
        "white_noise": "0bd0cf25abf854961fd834d249d71b1e896c4f13b44bc106526b19c3f15719b4",
        "ar1": "87303bf0123cad6bdde7cc9d3cee96ab03b174047c29c4201b379d592a671272",
        "seasonal": "2cba06033e78350ec60485926a1fcab5b827bdfd6ea5e3ca5bb1ffd57de407f7",
        "weak_seasonal_near_threshold": (
            "f368c7a4ff4da917bd8eea08110772f7dca445fb3ebe89e561f2b21032e87a88"
        ),
        "nonlinear_mixed": "f5d0d98a995a39c755b5152bec54b892427165dd9c673f49a73f55109e40d67e",
        "structural_break": "297e35093acf84791b835fba806055422301b510e2e07006908b6b885a82f54e",
        "long_memory": "8c376f313b309eecd00beea5dba4aa5f68f41f26fe2b359be3d47169a6edcd23",
        "mediated_low_directness": (
            "8a41240ff0ef078406904df914d5587bce09141b33158d687d46a72a7300474f"
        ),
        "exogenous_driven": "e6e9f9af3755e1a8f12dbd32422213b11924d57a3bb2849641100d0770bf5a8d",
        "low_directness_high_penalty": (
            "3036277312ad75de7e5cb576f2902055c4780a214d8807833bcbea487888e045"
        ),
    }
    assert observed == expected
