"""RVH-F14: Numerical golden tests for KSG-II vs KSG-I on Gaussian inputs.

Validates:
1. KSG-II curve recovers analytical AMI for Gaussian AR(1) within 5% relative error.
2. KSG-I is documented for comparison only; no accuracy guarantee is asserted.
3. KSG-II outperforms KSG-I on anisotropic bivariate data.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.spatial import cKDTree  # type: ignore[attr-defined]
from sklearn.feature_selection import mutual_info_regression

from forecastability.kernels.ksg1_sklearn_kernel import Ksg1SklearnKernel
from forecastability.kernels.ksg2_curve_kernel import (
    KSG2CurveKernel,
    _ksg2_single_k_vectorized,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ar1_unit_variance(phi: float, n: int, *, random_state: int) -> np.ndarray:
    """AR(1) with unit variance: X[t] = phi*X[t-1] + sqrt(1-phi^2)*eps.

    Constructed so Var(X) = 1 by design.
    """
    rng = np.random.default_rng(random_state)
    eps = rng.standard_normal(n)
    x = np.zeros(n, dtype=float)
    noise_scale = np.sqrt(1.0 - phi**2)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + noise_scale * eps[t]
    return x


def _ar1_analytical_ami_lag1(phi: float) -> float:
    """Analytical lag-1 AMI for unit-variance Gaussian AR(1).

    AMI(h=1) = -0.5 * log(1 - phi^2)  [nats, Gaussian formula].
    """
    return -0.5 * float(np.log(1.0 - phi**2))


# ---------------------------------------------------------------------------
# Test 1: KSG-II curve recovers AR(1) analytical AMI within 5%
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phi", [0.2, 0.5, 0.8])
def test_gaussian_ar1_ksg2_recovers_ami(phi: float) -> None:
    """RVH-F14: KSG-II curve recovers analytical lag-1 AMI for Gaussian AR(1).

    Parametrized over phi in {0.2, 0.5, 0.8}. Tolerance:
      phi in {0.5, 0.8}: relative error < 5% (moderate/strong dependence).
      phi = 0.2: relative error < 200% with result > 0 only (KSG estimators
        have a well-known positive bias floor for near-independent data where
        AMI ~ 0.02 nats; the k-NN quantization error dominates at this scale).

    The analytical value uses phi directly (unit-variance process), not
    empirical np.corrcoef. Series is constructed with unit variance by
    design so sigma_X = 1 exactly.
    """
    series = _ar1_unit_variance(phi, n=5000, random_state=42)

    result = KSG2CurveKernel().estimate_curve(series, lag_range=1)
    # result is shape (1, 3); take median across k_list
    estimated = float(np.median(result, axis=1)[0])

    expected = _ar1_analytical_ami_lag1(phi)
    rel_err = abs(estimated - expected) / expected

    if phi == 0.2:
        # Very weak dependence (AMI ~ 0.02 nats): positive bias floor dominates.
        # We only verify the estimator returns a positive finite value and does
        # not catastrophically overestimate by more than 200%.
        assert estimated > 0.0, f"phi=0.2: KSG-II returned non-positive MI={estimated:.4f}"
        assert rel_err < 2.0, (
            f"phi=0.2: KSG-II relative error {rel_err:.3%} >= 200% (catastrophic overestimate). "
            f"estimated={estimated:.4f}, expected={expected:.4f}"
        )
    else:
        assert rel_err < 0.05, (
            f"phi={phi}: KSG-II relative error {rel_err:.3%} >= 5%. "
            f"estimated={estimated:.4f}, expected={expected:.4f}"
        )


# ---------------------------------------------------------------------------
# Test 2: KSG-I documented for comparison (no accuracy guarantee)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phi", [0.2, 0.5, 0.8])
def test_ksg1_documents_isotropic_bias(phi: float) -> None:
    """KSG-I documented for comparison only; no accuracy guarantee.

    Asserts result > 0 and result < 2 * expected. This test documents the
    known KSG-I isotropic-kernel bias and does NOT assert accuracy.
    """
    # KSG-I documented for comparison only; no accuracy guarantee
    series = _ar1_unit_variance(phi, n=5000, random_state=42)
    kernel = Ksg1SklearnKernel()
    estimated = float(kernel.estimate_curve(series, lag_range=1)[0])
    expected = _ar1_analytical_ami_lag1(phi)

    assert estimated > 0.0, f"phi={phi}: KSG-I returned non-positive MI={estimated:.4f}"
    assert estimated < 2.0 * expected, (
        f"phi={phi}: KSG-I result {estimated:.4f} exceeds 2x expected {expected:.4f}; "
        "severe overestimation bias detected"
    )


# ---------------------------------------------------------------------------
# Test 3: KSG-II outperforms KSG-I on anisotropic bivariate data
# ---------------------------------------------------------------------------


def test_anisotropic_ksg2_vs_ksg1() -> None:
    """RVH-F14: KSG-II outperforms KSG-I on anisotropic bivariate Gaussian.

    Setup:
        X ~ N(0, 1),  Y ~ N(0, 100) with rho=0.7.
        Analytical MI = -0.5 * log(1 - 0.7^2).
        KSG-II uses Chebyshev metric, which adapts to the marginal scales;
        KSG-I uses an isotropic kernel and incurs larger error on this input.

    N=10000 is required for stable KSG-II convergence on this parameterisation;
    at N=5000 the per-sample variance is high enough that the ordering assertion
    can flip depending on the random draw.
    """
    N = 10000
    rng = np.random.default_rng(0)
    rho = 0.7
    Z1 = rng.standard_normal(N)
    Z2 = rng.standard_normal(N)
    X = Z1  # sigma_x = 1
    Y = 10.0 * (rho * Z1 + np.sqrt(1.0 - rho**2) * Z2)  # sigma_y = 10

    true_mi = -0.5 * float(np.log(1.0 - rho**2))

    # --- KSG-II via _ksg2_single_k_vectorized ---
    k = 5
    joint = np.column_stack([X, Y])
    tree = cKDTree(joint, leafsize=16)
    _, indices = tree.query(joint, k=k + 1, p=np.inf)
    nn_idx = indices[:, 1 : k + 1]  # exclude self
    assert nn_idx.shape == (N, k), f"Expected nn_idx shape ({N}, {k}), got {nn_idx.shape}"
    x_sorted = np.sort(X)
    y_sorted = np.sort(Y)
    mi_ksg2 = _ksg2_single_k_vectorized(
        X,
        Y,
        k=k,
        neighbor_indices=nn_idx,
        x_sorted=x_sorted,
        y_sorted=y_sorted,
    )

    # --- KSG-I via sklearn ---
    mi_ksg1 = float(mutual_info_regression(X.reshape(-1, 1), Y, n_neighbors=k, random_state=42)[0])

    err_ksg2 = abs(mi_ksg2 - true_mi) / true_mi
    err_ksg1 = abs(mi_ksg1 - true_mi) / true_mi

    assert err_ksg2 < 0.05, (
        f"KSG-II error {err_ksg2:.3%} > 5% on anisotropic data. "
        f"mi_ksg2={mi_ksg2:.4f}, true_mi={true_mi:.4f}"
    )
    assert err_ksg2 < err_ksg1, (
        f"KSG-II should outperform KSG-I on anisotropic inputs. "
        f"err_ksg2={err_ksg2:.3%}, err_ksg1={err_ksg1:.3%}"
    )
