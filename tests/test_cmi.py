"""Tests for conditional-MI backend extensions."""

from __future__ import annotations

import numpy as np
import pytest

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


def test_compute_pami_with_extra_trees_backend_shape_and_finiteness() -> None:
    ts = generate_sine_wave(n_samples=260, random_state=3)
    out = compute_pami_with_backend(
        ts,
        max_lag=10,
        backend="extra_trees_residual",
        random_state=7,
    )
    assert out.shape == (10,)
    assert np.all(np.isfinite(out))
    assert np.all(out >= 0.0)


def test_compute_pami_with_backend_rejects_unknown_backend() -> None:
    ts = generate_sine_wave(n_samples=260, random_state=3)
    with pytest.raises(ValueError, match="Unsupported pAMI backend"):
        compute_pami_with_backend(ts, max_lag=8, backend="unsupported_backend", random_state=7)
