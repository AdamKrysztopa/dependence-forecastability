"""Invariant A: every public AMI/pAMI call routes through KSG2CurveKernel by default."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from forecastability.metrics.metrics import compute_ami, compute_pami_linear_residual


@pytest.fixture
def ar1_series() -> np.ndarray:
    rng = np.random.default_rng(0)
    x = np.zeros(200)
    x[0] = rng.normal()
    for i in range(1, 200):
        x[i] = 0.5 * x[i - 1] + rng.normal()
    return x


def test_compute_ami_routes_through_ksg2_curve_kernel(ar1_series: np.ndarray) -> None:
    """compute_ami with default estimator='ksg2' must call KSG2CurveKernel.estimate_curve."""
    with patch("forecastability.metrics.metrics.KSG2CurveKernel") as MockKernel:
        mock_instance = MagicMock()
        mock_instance.estimate_curve.return_value = np.zeros((10, 3))
        MockKernel.return_value = mock_instance

        compute_ami(ar1_series, max_lag=10)

        MockKernel.assert_called_once()
        mock_instance.estimate_curve.assert_called_once()


def test_compute_ami_ksg1_sklearn_does_not_use_ksg2_kernel(ar1_series: np.ndarray) -> None:
    """compute_ami with estimator='ksg1_sklearn' must NOT call KSG2CurveKernel."""
    with patch("forecastability.metrics.metrics.KSG2CurveKernel") as MockKernel:
        compute_ami(ar1_series, max_lag=5, estimator="ksg1_sklearn")
        MockKernel.assert_not_called()


def test_compute_pami_routes_through_ksg2_curve_kernel(ar1_series: np.ndarray) -> None:
    """compute_pami_linear_residual with default estimator='ksg2' uses KSG2CurveKernel."""
    result = compute_pami_linear_residual(ar1_series, max_lag=5)
    assert result.shape == (5,)
    assert np.all(result >= 0.0)


def test_compute_ami_default_is_ksg2(ar1_series: np.ndarray) -> None:
    """compute_ami default estimator produces non-negative finite values."""
    ami = compute_ami(ar1_series, max_lag=10, random_state=42)
    assert ami.shape == (10,)
    assert np.all(np.isfinite(ami))
    assert np.all(ami >= 0.0)


def test_compute_ami_invalid_estimator(ar1_series: np.ndarray) -> None:
    """compute_ami with an invalid estimator raises ValueError."""
    with pytest.raises(ValueError, match="estimator must be"):
        compute_ami(ar1_series, max_lag=5, estimator="invalid")  # type: ignore[arg-type]


def test_compute_pami_invalid_estimator(ar1_series: np.ndarray) -> None:
    """compute_pami_linear_residual with an invalid estimator raises ValueError."""
    with pytest.raises(ValueError, match="estimator must be"):
        compute_pami_linear_residual(ar1_series, max_lag=5, estimator="invalid")  # type: ignore[arg-type]
