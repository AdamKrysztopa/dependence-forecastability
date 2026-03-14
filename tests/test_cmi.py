"""Tests for conditional-MI backend extensions."""

from __future__ import annotations

import numpy as np

from forecastability.cmi import compute_pami_with_backend
from forecastability.datasets import generate_sine_wave


def test_compute_pami_with_linear_backend_shape_and_finiteness() -> None:
    ts = generate_sine_wave(n_samples=260, random_state=3)
    out = compute_pami_with_backend(ts, max_lag=14, backend="linear_residual", random_state=7)
    assert out.shape == (14,)
    assert np.all(np.isfinite(out))
    assert np.all(out >= 0.0)


def test_compute_pami_with_rf_backend_shape_and_finiteness() -> None:
    ts = generate_sine_wave(n_samples=260, random_state=3)
    out = compute_pami_with_backend(ts, max_lag=10, backend="rf_residual", random_state=7)
    assert out.shape == (10,)
    assert np.all(np.isfinite(out))
    assert np.all(out >= 0.0)
