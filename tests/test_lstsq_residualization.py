"""Numeric parity tests for the lstsq-based residualization helper (PBE-F06)."""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.linear_model import LinearRegression

from forecastability.metrics._lag_design import residualize_with_intercept

_SHAPES: tuple[tuple[int, int], ...] = (
    (64, 1),
    (64, 2),
    (64, 5),
    (128, 2),
    (128, 5),
    (128, 10),
    (256, 1),
    (256, 5),
    (256, 10),
)


def _sklearn_residual(z: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Reference residual via scikit-learn's LinearRegression."""
    model = LinearRegression().fit(z, target)
    return target - model.predict(z)


@pytest.mark.parametrize("shape", _SHAPES)
@pytest.mark.parametrize("seed", [0, 1])
def test_helper_single_target_matches_sklearn(shape: tuple[int, int], seed: int) -> None:
    """Single-target residual matches LinearRegression to ~1e-10."""
    rng = np.random.default_rng(seed)
    n_rows, n_cols = shape
    z = rng.standard_normal((n_rows, n_cols))
    target = rng.standard_normal(n_rows)

    (res_helper,) = residualize_with_intercept(z, (target,))
    res_ref = _sklearn_residual(z, target)

    assert np.allclose(res_helper, res_ref, atol=1e-10, rtol=1e-9)


@pytest.mark.parametrize("shape", _SHAPES)
@pytest.mark.parametrize("seed", [10, 11])
def test_helper_multi_target_matches_sklearn(shape: tuple[int, int], seed: int) -> None:
    """Two-target residuals (past, future) match LinearRegression to ~1e-10."""
    rng = np.random.default_rng(seed)
    n_rows, n_cols = shape
    z = rng.standard_normal((n_rows, n_cols))
    past = rng.standard_normal(n_rows)
    future = rng.standard_normal(n_rows)

    res_past, res_future = residualize_with_intercept(z, (past, future))

    assert np.allclose(res_past, _sklearn_residual(z, past), atol=1e-10, rtol=1e-9)
    assert np.allclose(res_future, _sklearn_residual(z, future), atol=1e-10, rtol=1e-9)


def test_helper_empty_features_short_circuits_to_mean_centering() -> None:
    """Zero-column design yields mean-centered targets (sklearn intercept-only)."""
    rng = np.random.default_rng(42)
    target = rng.standard_normal(50)
    z_empty = np.empty((50, 0))

    (res_helper,) = residualize_with_intercept(z_empty, (target,))

    assert np.allclose(res_helper, target - target.mean(), atol=1e-12)


def test_helper_returns_in_input_order() -> None:
    """Output tuple preserves input ordering."""
    rng = np.random.default_rng(7)
    z = rng.standard_normal((80, 3))
    a = rng.standard_normal(80)
    b = rng.standard_normal(80)
    c = rng.standard_normal(80)

    res_a, res_b, res_c = residualize_with_intercept(z, (a, b, c))

    assert np.allclose(res_a, _sklearn_residual(z, a), atol=1e-10, rtol=1e-9)
    assert np.allclose(res_b, _sklearn_residual(z, b), atol=1e-10, rtol=1e-9)
    assert np.allclose(res_c, _sklearn_residual(z, c), atol=1e-10, rtol=1e-9)
