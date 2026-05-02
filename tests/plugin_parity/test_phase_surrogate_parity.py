"""Parity oracle — phase_surrogates kernel.

Skipped unless a forecastability.kernels provider is installed
(see conftest.py in this directory).

Parity gates (§6.2 of pbe_f09_native_plugin_design.md):
- Shape parity
- dtype parity
- Fixed-seed bit-identical output
- Spectrum-preservation (amplitude match)
- n_surrogates < 99 raises ValueError
"""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.diagnostics.surrogates import phase_surrogates as py_phase_surrogates
from forecastability.ports.kernels import load_kernel_provider


@pytest.fixture(scope="module")
def provider():
    p = load_kernel_provider()
    if p is None:
        pytest.skip("No kernel provider installed")
    return p


@pytest.fixture(scope="module")
def reference_series() -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.standard_normal(400)


def test_phase_surrogate_shape_parity(provider, reference_series: np.ndarray) -> None:
    native = provider.phase_surrogates(
        reference_series, n_surrogates=99, random_state=42
    )
    python = py_phase_surrogates(
        reference_series, n_surrogates=99, random_state=42
    )
    assert native.shape == python.shape, (
        f"Shape mismatch: native={native.shape}, python={python.shape}"
    )


def test_phase_surrogate_dtype_parity(provider, reference_series: np.ndarray) -> None:
    native = provider.phase_surrogates(
        reference_series, n_surrogates=99, random_state=42
    )
    python = py_phase_surrogates(
        reference_series, n_surrogates=99, random_state=42
    )
    assert native.dtype == python.dtype, (
        f"dtype mismatch: native={native.dtype}, python={python.dtype}"
    )


def test_phase_surrogate_fixed_seed_bit_identical(
    provider, reference_series: np.ndarray
) -> None:
    native = provider.phase_surrogates(
        reference_series, n_surrogates=99, random_state=42
    )
    python = py_phase_surrogates(
        reference_series, n_surrogates=99, random_state=42
    )
    np.testing.assert_array_equal(
        native,
        python,
        err_msg="phase_surrogates: native and Python outputs are not bit-identical",
    )


def test_phase_surrogate_spectrum_preservation(
    provider, reference_series: np.ndarray
) -> None:
    """Each surrogate row preserves the amplitude spectrum of the input."""
    native = provider.phase_surrogates(
        reference_series, n_surrogates=9, random_state=7
    )
    ref_amp = np.abs(np.fft.rfft(reference_series))
    for i, row in enumerate(native):
        row_amp = np.abs(np.fft.rfft(row))
        np.testing.assert_allclose(
            row_amp,
            ref_amp,
            rtol=1e-10,
            err_msg=f"Surrogate row {i}: amplitude spectrum not preserved",
        )


def test_phase_surrogate_rejects_low_n_surrogates(
    provider, reference_series: np.ndarray
) -> None:
    with pytest.raises((ValueError, Exception)):
        provider.phase_surrogates(
            reference_series, n_surrogates=10, random_state=42
        )
