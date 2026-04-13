"""Tests for spectral_utils: compute_normalised_psd and spectral_entropy."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.spectral_utils import compute_normalised_psd, spectral_entropy


def test_psd_sums_to_one() -> None:
    rng = np.random.default_rng(0)
    series = rng.standard_normal(256)
    _, p = compute_normalised_psd(series)
    assert abs(p.sum() - 1.0) < 1e-9


def test_psd_shape() -> None:
    rng = np.random.default_rng(1)
    series = rng.standard_normal(128)
    freqs, p = compute_normalised_psd(series)
    assert freqs.shape == p.shape


def test_psd_raises_for_short_series() -> None:
    series = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    with pytest.raises(ValueError):
        compute_normalised_psd(series)


def test_psd_raises_for_2d_input() -> None:
    series = np.ones((10, 2))
    with pytest.raises(ValueError):
        compute_normalised_psd(series)


def test_entropy_periodic_vs_white_noise() -> None:
    rng = np.random.default_rng(0)
    noise = rng.standard_normal(512)
    periodic = np.sin(np.linspace(0, 8 * np.pi, 512))

    _, p_noise = compute_normalised_psd(noise)
    _, p_periodic = compute_normalised_psd(periodic)

    h_noise = spectral_entropy(p_noise)
    h_periodic = spectral_entropy(p_periodic)

    assert h_periodic < h_noise


def test_entropy_base_invariance() -> None:
    rng = np.random.default_rng(2)
    series = rng.standard_normal(256)
    _, p = compute_normalised_psd(series)
    h_nat = spectral_entropy(p, base=np.e)
    h_2 = spectral_entropy(p, base=2.0)
    assert abs(h_2 - h_nat / np.log(2)) < 1e-9


def test_entropy_nonnegative() -> None:
    rng = np.random.default_rng(3)
    for _ in range(5):
        series = rng.standard_normal(64)
        _, p = compute_normalised_psd(series)
        assert spectral_entropy(p) >= 0.0


def test_entropy_uniform_distribution() -> None:
    n = 100
    p = np.full(n, 1.0 / n)
    h = spectral_entropy(p, base=np.e)
    assert abs(h - np.log(n)) < 1e-9


def test_entropy_degenerate_distribution() -> None:
    n = 50
    p = np.zeros(n)
    p[0] = 1.0
    h = spectral_entropy(p, base=np.e)
    # The clipping at 1e-12 causes a small residual ~1e-9; use a slightly looser tolerance
    assert abs(h) < 1e-7


def test_nperseg_override() -> None:
    rng = np.random.default_rng(4)
    series = rng.standard_normal(256)
    freqs, p = compute_normalised_psd(series, nperseg=64)
    assert freqs.shape == p.shape
    assert abs(p.sum() - 1.0) < 1e-9
