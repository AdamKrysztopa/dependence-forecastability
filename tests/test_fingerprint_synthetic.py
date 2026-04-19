"""Tests for the canonical fingerprint synthetic archetype panel."""

from __future__ import annotations

import numpy as np

from forecastability.utils.synthetic import generate_fingerprint_archetypes


def test_generate_fingerprint_archetypes_returns_expected_keys() -> None:
    """The archetype helper should expose the canonical four-series panel."""
    series_map = generate_fingerprint_archetypes(n=128, seed=42)
    assert list(series_map) == [
        "white_noise",
        "ar1_monotonic",
        "seasonal_periodic",
        "nonlinear_mixed",
    ]


def test_generate_fingerprint_archetypes_is_deterministic_by_seed() -> None:
    """The helper should be deterministic for a fixed seed."""
    first = generate_fingerprint_archetypes(n=128, seed=7)
    second = generate_fingerprint_archetypes(n=128, seed=7)
    for key in first:
        assert np.array_equal(first[key], second[key])


def test_generate_fingerprint_archetypes_respects_length_argument() -> None:
    """Every generated series should match the requested sample count."""
    n = 96
    series_map = generate_fingerprint_archetypes(n=n, seed=21)
    for series in series_map.values():
        assert len(series) == n
