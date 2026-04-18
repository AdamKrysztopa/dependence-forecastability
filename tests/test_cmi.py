"""Tests for conditional-MI backend extensions."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.diagnostics.cmi import (
    compute_conditional_mi_with_backend,
    compute_pami_with_backend,
)
from forecastability.utils.datasets import generate_sine_wave


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


def test_compute_conditional_mi_requires_min_pairs_floor() -> None:
    rng = np.random.default_rng(8)
    past = rng.normal(size=120)
    future = 0.4 * past + rng.normal(scale=0.8, size=120)

    with pytest.raises(ValueError, match="min_pairs must be >= 50"):
        compute_conditional_mi_with_backend(past, future, min_pairs=30, random_state=7)


def test_compute_conditional_mi_requires_robust_rows_when_conditioning_present() -> None:
    rng = np.random.default_rng(10)
    past = rng.normal(size=90)
    future = 0.5 * past + rng.normal(scale=0.6, size=90)
    conditioning = rng.normal(size=(90, 3))

    with pytest.raises(ValueError, match=r"at least 2 \* min_pairs"):
        compute_conditional_mi_with_backend(
            past,
            future,
            conditioning=conditioning,
            min_pairs=50,
            random_state=7,
        )
