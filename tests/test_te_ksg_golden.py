"""Golden test for compute_transfer_entropy_ksg against VAR(1) analytical formula.

# Analytical TE for bivariate VAR(1):
#   X_t = a*X_{t-1} + noise_x
#   Y_t = b*Y_{t-1} + c*X_{t-1} + noise_y
#   TE_{X→Y}(L=1) = 0.5 * log((σ_x² + c²σ_x²) / σ_x²) [simplified Gaussian TE]
# More precisely for unit-variance Gaussians with coupling c:
#   TE_{X→Y} = 0.5 * log(1 + c² * (1 - a²) / (1 - (b + ca)²))
# (Barnett et al. 2009, Eq. 14 special case)
"""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.diagnostics.cmi_ksg import compute_transfer_entropy_ksg


def _var1_te_analytical(
    a: float, b: float, c: float, sigma_x: float = 1.0, sigma_y: float = 1.0
) -> float:
    """Analytical TE_{X→Y} at lag=1 for VAR(1) with Gaussian noise.

    # TE = 0.5 * log((var_y_given_history) / (var_y_given_full_history))
    # Under Gaussian VAR(1): TE_{X→Y} = 0.5 * log(1 + c² * var_x / var_innov_y)
    """
    # Steady-state variances
    var_x = sigma_x**2 / (1 - a**2)
    var_y_innov = sigma_y**2  # innovation variance
    # TE = 0.5 * log(sigma_y_without_x / sigma_y_with_x)
    return 0.5 * np.log(1 + (c**2 * var_x) / var_y_innov)


@pytest.mark.parametrize("coupling", [0.0, 0.3, 0.6])
def test_gaussian_var1_recovers_analytical_te(coupling: float) -> None:
    rng = np.random.default_rng(42)
    N = 5000
    a, b, c = 0.5, 0.3, coupling
    X = np.zeros(N)
    Y = np.zeros(N)
    for t in range(1, N):
        X[t] = a * X[t - 1] + rng.normal()
        Y[t] = b * Y[t - 1] + c * X[t - 1] + rng.normal()
    result = compute_transfer_entropy_ksg(X, Y, lag=1, history_depth=1, k=5)
    expected = _var1_te_analytical(a, b, c)
    if coupling == 0.0:
        assert result.value == pytest.approx(0.0, abs=0.05)
    else:
        assert result.status == "computed"
        # KSG-CMI has finite-sample upward bias when N/k^(d+2) < 2 ("unreliable" regime).
        # At N=5000, k=5, d_total=3: ratio=N_eff/k^5 ≈ 1.6 — tolerance is 30% to
        # accommodate known KSG bias; the test validates sign and correct order of magnitude.
        # For reliable regime (ratio>=10) 15% is achievable; see quality_warning field.
        assert result.value == pytest.approx(expected, rel=0.30)  # 30% tolerance at N=5000
