"""Golden test for compute_transfer_entropy_ksg against VAR(1) analytical formula.

# Analytical TE for bivariate VAR(1):
#   X_t = a*X_{t-1} + noise_x,  Y_t = b*Y_{t-1} + c*X_{t-1} + noise_y
#   TE_{X→Y}(L=1) = 0.5 * log((c² * var_x + σ_y²) / σ_y²)
#   where var_x = σ_x² / (1 - a²)   [Barnett et al. 2009, Eq. 14 special case]
"""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.diagnostics.cmi_ksg import compute_transfer_entropy_ksg


def _var1_te_analytical(
    a: float, b: float, c: float, sigma_x: float = 1.0, sigma_y: float = 1.0
) -> float:
    """Analytical TE_{X→Y} at lag=1 for Gaussian VAR(1).

    # TE = 0.5 * log(var(Y|Y_past) / var(Y|Y_past, X_past))
    # var(Y|Y_past) = c² * var_x + σ_y²  (X_{t-1} contributes full variance)
    # var(Y|Y_past, X_past) = σ_y²       (noise only)
    # where var_x = σ_x² / (1 - a²)   [Barnett et al. 2009, Eq. 14 special case]
    """
    var_x = sigma_x**2 / (1 - a**2)
    return 0.5 * np.log((c**2 * var_x + sigma_y**2) / sigma_y**2)


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
    # N_eff≈4998, d_total=3, k^(d_total+2)=5^5=3125 → ratio≈1.6 ("unreliable" regime)
    # See TransferEntropyKsgResult.quality_warning for regime interpretation.
    assert result.quality_warning in ("marginal", "unreliable")
    if coupling == 0.0:
        assert result.value == pytest.approx(0.0, abs=0.05)
    else:
        assert result.status == "computed"
        assert result.value == pytest.approx(expected, rel=0.30)
