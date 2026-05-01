"""Surrogate and significance tests."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.diagnostics import surrogates as surrogates_module
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


def _raise_phase_surrogates(*_args: object, **_kwargs: object) -> np.ndarray:
    raise AssertionError("phase_surrogates should not be called")


def test_legacy_significance_rejects_invalid_metric_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(surrogates_module, "phase_surrogates", _raise_phase_surrogates)
    ts = generate_sine_wave(n_samples=180, random_state=1)
    with pytest.raises(ValueError, match="metric_name"):
        compute_significance_bands(ts, metric_name="bogus", max_lag=4, n_surrogates=99)


def test_legacy_significance_rejects_zero_max_lag_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(surrogates_module, "phase_surrogates", _raise_phase_surrogates)
    ts = generate_sine_wave(n_samples=180, random_state=1)
    with pytest.raises(ValueError, match="max_lag"):
        compute_significance_bands(ts, metric_name="ami", max_lag=0, n_surrogates=99)


def test_legacy_significance_rejects_zero_n_jobs_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(surrogates_module, "phase_surrogates", _raise_phase_surrogates)
    ts = generate_sine_wave(n_samples=180, random_state=1)
    with pytest.raises(ValueError, match="n_jobs"):
        compute_significance_bands(ts, metric_name="ami", max_lag=4, n_surrogates=99, n_jobs=0)


def test_legacy_significance_n_jobs_serial_vs_parallel_bit_identical() -> None:
    ts = generate_sine_wave(n_samples=180, random_state=1)
    serial_lower, serial_upper = compute_significance_bands(
        ts,
        metric_name="ami",
        max_lag=6,
        n_surrogates=99,
        random_state=4,
        n_jobs=1,
    )
    parallel_lower, parallel_upper = compute_significance_bands(
        ts,
        metric_name="ami",
        max_lag=6,
        n_surrogates=99,
        random_state=4,
        n_jobs=2,
    )
    assert np.array_equal(serial_lower, parallel_lower)
    assert np.array_equal(serial_upper, parallel_upper)
