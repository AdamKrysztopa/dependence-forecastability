"""Tests for the shared lag-design scaffolding helper."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.diagnostics.cmi import _build_conditioning_matrix as legacy_cmi
from forecastability.metrics._lag_design import build_intermediate_design
from forecastability.metrics.metrics import _build_conditioning_matrix as legacy_metrics


def test_shape_basic() -> None:
    arr = np.arange(20.0, dtype=float)
    out = build_intermediate_design(arr, h=5)
    assert out.shape == (15, 4)
    assert out.dtype == np.float64


def test_h_one_edge_case() -> None:
    arr = np.arange(20.0, dtype=float)
    out = build_intermediate_design(arr, h=1)
    assert out.shape == (19, 0)
    assert out.dtype == np.float64


def test_h_zero_edge_case() -> None:
    arr = np.arange(20.0, dtype=float)
    out = build_intermediate_design(arr, h=0)
    assert out.shape == (20, 0)
    assert out.dtype == np.float64


@pytest.mark.parametrize("h", [2, 3, 5, 8, 12])
def test_column_content_invariant(h: int) -> None:
    arr = np.arange(40.0, dtype=float)
    out = build_intermediate_design(arr, h=h)
    n_rows = arr.size - h
    for k in range(h - 1):
        expected = arr[k + 1 : n_rows + k + 1]
        assert np.array_equal(out[:, k], expected)


@pytest.mark.parametrize("h", list(range(1, 17)))
def test_bit_identical_to_legacy_implementations(h: int) -> None:
    rng = np.random.default_rng(seed=20260501)
    arr = rng.standard_normal(256).astype(np.float64)
    new_out = build_intermediate_design(arr, h)
    metrics_out = legacy_metrics(arr, h)
    cmi_out = legacy_cmi(arr, h)
    assert np.array_equal(new_out, metrics_out)
    assert np.array_equal(new_out, cmi_out)
    assert new_out.shape == metrics_out.shape == cmi_out.shape
