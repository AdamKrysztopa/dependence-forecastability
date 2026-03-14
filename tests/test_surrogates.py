"""Surrogate and significance tests."""

from __future__ import annotations

import pytest

from forecastability.datasets import generate_sine_wave
from forecastability.surrogates import compute_significance_bands, phase_surrogates


def test_phase_surrogates_shape() -> None:
    ts = generate_sine_wave(n_samples=180, random_state=1)
    surrogates = phase_surrogates(ts, n_surrogates=7, random_state=4)
    assert surrogates.shape == (7, 180)


def test_significance_bands_shape() -> None:
    ts = generate_sine_wave(n_samples=180, random_state=1)
    lower, upper = compute_significance_bands(
        ts,
        metric_name="ami",
        max_lag=10,
        n_surrogates=99,
        random_state=4,
    )
    assert lower.shape == (10,)
    assert upper.shape == (10,)


def test_significance_rejects_too_few_surrogates() -> None:
    ts = generate_sine_wave(n_samples=180, random_state=1)
    with pytest.raises(ValueError, match=">= 99"):
        compute_significance_bands(ts, metric_name="ami", max_lag=8, n_surrogates=98)
