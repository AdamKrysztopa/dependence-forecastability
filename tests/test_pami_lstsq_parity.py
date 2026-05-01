"""Numeric parity tests for lstsq-based pAMI residualization (PBE-F06).

The pre-change reference values were captured by running the legacy
``LinearRegression``-based implementation immediately before the F06
refactor.  The tolerance accounts for the ~1e-12 perturbation between
``np.linalg.lstsq`` and scikit-learn's solver propagating through the
non-bit-stable kNN MI estimator downstream.
"""
# ruff: noqa: E501

from __future__ import annotations

import numpy as np
import pytest

from forecastability.metrics.metrics import compute_pami_linear_residual
from forecastability.metrics.scorers import default_registry
from forecastability.services.partial_curve_service import compute_partial_curve

_RTOL = 1e-7
_ATOL = 1e-9


def _ar1(n: int, phi: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def _seasonal_ar(n: int, period: int, phi_s: float, phi_1: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n)
    x = np.zeros(n)
    for i in range(max(period, 1), n):
        x[i] = phi_s * x[i - period] + phi_1 * x[i - 1] + e[i]
    return x


def _white_noise(n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(n)


SERIES_BUILDERS = {
    "ar1": lambda: _ar1(512, 0.7, 0),
    "seasonal": lambda: _seasonal_ar(512, 12, 0.5, 0.2, 1),
    "wn": lambda: _white_noise(512, 2),
}


PRE_PAMI: dict[tuple[str, int], list[float]] = {
    ("ar1", 8): [
        0.3192411708068179,
        0.0,
        0.02905951939844975,
        0.005319973247519094,
        0.0,
        0.0,
        0.01978939859121276,
        0.0,
    ],
    ("ar1", 16): [
        0.3192411708068179,
        0.0,
        0.02905951939844975,
        0.005319973247519094,
        0.0,
        0.0,
        0.01978939859121276,
        0.0,
        0.0,
        0.009385608424314462,
        0.018801990260323365,
        0.009992200026682774,
        0.006411824228194085,
        0.0,
        0.03151568679178052,
        0.001396280595698407,
    ],
    ("seasonal", 8): [
        0.0772080804306503,
        0.07913149814274245,
        0.03926045029422376,
        0.019206018483055587,
        0.01993151452519104,
        0.0,
        0.015241556221599062,
        0.02534235933175122,
    ],
    ("seasonal", 16): [
        0.0772080804306503,
        0.07913149814274245,
        0.03926045029422376,
        0.019206018483055587,
        0.01993151452519104,
        0.0,
        0.015241556221599062,
        0.02534235933175122,
        9.70576995484862e-05,
        0.011490795052978342,
        0.03603389502994325,
        0.18192736592173198,
        0.0,
        0.0,
        0.0,
        0.0,
    ],
    ("wn", 8): [
        0.006574131137655037,
        0.02229708896155369,
        0.0,
        0.0,
        0.005840522555327965,
        0.024041425123124682,
        0.0,
        0.0,
    ],
    ("wn", 16): [
        0.006574131137655037,
        0.02229708896155369,
        0.0,
        0.0,
        0.005840522555327965,
        0.024041425123124682,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.003732150013290969,
        0.016933940450230445,
        0.0,
        0.0,
        0.017899587696635244,
    ],
}


PRE_PARTIAL_NO_EXOG: dict[tuple[str, int], list[float]] = {
    # Generic partial-curve with the MI scorer reduces to the same residualization
    # path as compute_pami_linear_residual when no exog is supplied, hence values
    # match PRE_PAMI exactly.
    key: list(values)
    for key, values in PRE_PAMI.items()
}


PRE_PARTIAL_EXOG: dict[tuple[str, int], list[float]] = {
    ("ar1", 8): [
        0.0841415972347006,
        0.0014392497768955792,
        0.025540057243891745,
        0.008724803963075622,
        0.0,
        0.000716399429525616,
        0.011068729382468057,
        0.013844165359200744,
    ],
    ("ar1", 16): [
        0.0841415972347006,
        0.0014392497768955792,
        0.025540057243891745,
        0.008724803963075622,
        0.0,
        0.000716399429525616,
        0.011068729382468057,
        0.013844165359200744,
        0.0,
        0.0,
        0.027261429134643578,
        0.010365563088898355,
        0.0020016999209451214,
        0.021836725927797396,
        0.0,
        0.0,
    ],
    ("seasonal", 8): [
        0.05706593618529787,
        0.03065256007197359,
        0.05391442636423793,
        0.05668524410787246,
        0.0,
        0.04465020993301749,
        0.040231240258817635,
        0.0,
    ],
    ("seasonal", 16): [
        0.05706593618529787,
        0.03065256007197359,
        0.05391442636423793,
        0.05668524410787246,
        0.0,
        0.04465020993301749,
        0.040231240258817635,
        0.0,
        0.0,
        0.031089830925347783,
        0.2001131144514705,
        0.03367810404359428,
        0.015414064917972148,
        0.004629766080820552,
        0.0,
        0.0,
    ],
}


@pytest.mark.parametrize(("name", "max_lag"), sorted(PRE_PAMI.keys()))
def test_compute_pami_linear_residual_matches_pre_change(name: str, max_lag: int) -> None:
    """compute_pami_linear_residual is numerically equivalent to the pre-F06 path."""
    ts = SERIES_BUILDERS[name]()
    expected = np.asarray(PRE_PAMI[(name, max_lag)], dtype=float)

    actual = compute_pami_linear_residual(ts, max_lag=max_lag, min_pairs=50, random_state=42)

    assert np.allclose(actual, expected, atol=_ATOL, rtol=_RTOL)


@pytest.mark.parametrize(("name", "max_lag"), sorted(PRE_PARTIAL_NO_EXOG.keys()))
def test_compute_partial_curve_no_exog_matches_pre_change(name: str, max_lag: int) -> None:
    """Generic partial-curve (no exog, mi scorer) matches the pre-F06 path."""
    ts = SERIES_BUILDERS[name]()
    expected = np.asarray(PRE_PARTIAL_NO_EXOG[(name, max_lag)], dtype=float)
    mi = default_registry().get("mi").scorer

    actual = compute_partial_curve(
        ts,
        max_lag=max_lag,
        scorer=mi,
        min_pairs=50,
        random_state=42,
    )

    assert np.allclose(actual, expected, atol=_ATOL, rtol=_RTOL)


@pytest.mark.parametrize(("name", "max_lag"), sorted(PRE_PARTIAL_EXOG.keys()))
def test_compute_partial_curve_with_exog_matches_pre_change(name: str, max_lag: int) -> None:
    """Generic partial-curve with exog (mi scorer) matches the pre-F06 path."""
    ts = SERIES_BUILDERS[name]()
    exog = np.roll(ts, 1)
    expected = np.asarray(PRE_PARTIAL_EXOG[(name, max_lag)], dtype=float)
    mi = default_registry().get("mi").scorer

    actual = compute_partial_curve(
        ts,
        max_lag=max_lag,
        scorer=mi,
        min_pairs=50,
        random_state=42,
        exog=exog,
    )

    assert np.allclose(actual, expected, atol=_ATOL, rtol=_RTOL)
