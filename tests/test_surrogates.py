"""Surrogate and significance tests."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.diagnostics.surrogates import compute_significance_bands, phase_surrogates
from forecastability.utils.datasets import generate_sine_wave


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


def test_legacy_significance_bands_fixed_seed_regression() -> None:
    ts = generate_sine_wave(n_samples=180, random_state=1)
    lower, upper = compute_significance_bands(
        ts,
        metric_name="ami",
        max_lag=10,
        n_surrogates=99,
        random_state=4,
    )

    expected_lower = np.array(
        [
            0.977722804491,
            0.703394845253,
            0.540963019741,
            0.504668553886,
            0.606559187144,
            0.806401779495,
            1.190128375604,
            1.188616343507,
            0.780253076211,
            0.5882066105,
        ],
    )
    expected_upper = np.array(
        [
            1.154001065862,
            0.908045592517,
            0.812497117106,
            0.798374122852,
            0.845115811032,
            0.969258248775,
            1.432652157276,
            1.422444721356,
            0.93366315876,
            0.78780168991,
        ],
    )

    np.testing.assert_allclose(lower, expected_lower)
    np.testing.assert_allclose(upper, expected_upper)
