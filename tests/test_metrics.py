"""Metric computation tests."""

from __future__ import annotations

import numpy as np

from forecastability.metrics import compute_ami, compute_pami_linear_residual
from forecastability.utils.datasets import generate_sine_wave


def test_ami_returns_non_negative_finite_values() -> None:
    ts = generate_sine_wave(n_samples=260, random_state=7)
    ami = compute_ami(ts, max_lag=24, random_state=11)
    assert ami.shape == (24,)
    assert np.all(np.isfinite(ami))
    assert np.all(ami >= 0.0)


def test_pami_returns_non_negative_finite_values_with_expected_shape() -> None:
    ts = generate_sine_wave(n_samples=260, random_state=7)
    pami = compute_pami_linear_residual(ts, max_lag=16, random_state=11)
    assert pami.shape == (16,)
    assert np.all(np.isfinite(pami))
    assert np.all(pami >= 0.0)


def test_metrics_are_deterministic_for_same_seed() -> None:
    ts = generate_sine_wave(n_samples=260, random_state=7)
    ami_a = compute_ami(ts, max_lag=18, random_state=123)
    ami_b = compute_ami(ts, max_lag=18, random_state=123)
    pami_a = compute_pami_linear_residual(ts, max_lag=12, random_state=123)
    pami_b = compute_pami_linear_residual(ts, max_lag=12, random_state=123)
    np.testing.assert_allclose(ami_a, ami_b)
    np.testing.assert_allclose(pami_a, pami_b)
