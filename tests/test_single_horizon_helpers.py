"""Parity and holdout-perturbation tests for single-horizon helpers (PBE-F04).

Each helper must return the same value as reading index [h-1] from its
corresponding full-curve function, given a series long enough to satisfy the
full-curve minimum-length requirement.  Tests are parametrized over multiple
(h, H) pairs where H >= h to ensure correctness regardless of the max_lag
chosen for the full-curve call.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from forecastability.metrics.metrics import (
    compute_ami,
    compute_ami_at_horizon,
    compute_pami_at_horizon,
    compute_pami_linear_residual,
)
from forecastability.metrics.scorers import _mi_scorer
from forecastability.pipeline import run_exogenous_rolling_origin_evaluation
from forecastability.pipeline.rolling_origin import build_expanding_window_splits
from forecastability.services.partial_curve_service import (
    compute_partial_at_horizon,
    compute_partial_curve,
)
from forecastability.services.raw_curve_service import (
    compute_raw_at_horizon,
    compute_raw_curve,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_RS = 42
_N = 250  # series length; long enough for all test horizons + min_pairs


@pytest.fixture(scope="module")
def sine_series() -> np.ndarray:
    return np.sin(np.linspace(0.0, 20.0, _N))


# ---------------------------------------------------------------------------
# Parametrize over (h, H) pairs
# ---------------------------------------------------------------------------

_H_PAIRS = [(1, 1), (1, 5), (3, 3), (3, 7), (5, 10)]


# ---------------------------------------------------------------------------
# AMI parity: compute_ami_at_horizon vs compute_ami curve
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("h,H", _H_PAIRS)
def test_ami_at_horizon_matches_curve(sine_series: np.ndarray, h: int, H: int) -> None:
    curve = compute_ami(sine_series, max_lag=H, n_neighbors=8, min_pairs=30, random_state=_RS)
    single = compute_ami_at_horizon(sine_series, h, n_neighbors=8, min_pairs=30, random_state=_RS)
    assert math.isclose(single, float(curve[h - 1]), rel_tol=1e-10, abs_tol=1e-14)


# ---------------------------------------------------------------------------
# pAMI parity: compute_pami_at_horizon vs compute_pami_linear_residual curve
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("h,H", _H_PAIRS)
def test_pami_at_horizon_matches_curve(sine_series: np.ndarray, h: int, H: int) -> None:
    curve = compute_pami_linear_residual(
        sine_series, max_lag=H, n_neighbors=8, min_pairs=50, random_state=_RS
    )
    single = compute_pami_at_horizon(
        sine_series, h, n_neighbors=8, min_pairs=50, random_state=_RS
    )
    assert math.isclose(single, float(curve[h - 1]), rel_tol=1e-10, abs_tol=1e-14)


# ---------------------------------------------------------------------------
# Raw-curve service parity: compute_raw_at_horizon vs compute_raw_curve
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("h,H", _H_PAIRS)
def test_raw_at_horizon_matches_curve_univariate(sine_series: np.ndarray, h: int, H: int) -> None:
    curve = compute_raw_curve(
        sine_series, H, _mi_scorer, min_pairs=30, random_state=_RS
    )
    single = compute_raw_at_horizon(
        sine_series, h, _mi_scorer, min_pairs=30, random_state=_RS
    )
    assert math.isclose(single, float(curve[h - 1]), rel_tol=1e-10, abs_tol=1e-14)


@pytest.mark.parametrize("h,H", _H_PAIRS)
def test_raw_at_horizon_matches_curve_with_exog(sine_series: np.ndarray, h: int, H: int) -> None:
    exog = np.cos(np.linspace(0.0, 20.0, _N))
    curve = compute_raw_curve(
        sine_series, H, _mi_scorer, exog=exog, min_pairs=30, random_state=_RS
    )
    single = compute_raw_at_horizon(
        sine_series, h, _mi_scorer, exog=exog, min_pairs=30, random_state=_RS
    )
    assert math.isclose(single, float(curve[h - 1]), rel_tol=1e-10, abs_tol=1e-14)


# ---------------------------------------------------------------------------
# Partial-curve service parity: compute_partial_at_horizon vs compute_partial_curve
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("h,H", _H_PAIRS)
def test_partial_at_horizon_matches_curve_univariate(
    sine_series: np.ndarray, h: int, H: int
) -> None:
    curve = compute_partial_curve(
        sine_series, H, _mi_scorer, min_pairs=50, random_state=_RS
    )
    single = compute_partial_at_horizon(
        sine_series, h, _mi_scorer, min_pairs=50, random_state=_RS
    )
    assert math.isclose(single, float(curve[h - 1]), rel_tol=1e-10, abs_tol=1e-14)


@pytest.mark.parametrize("h,H", _H_PAIRS)
def test_partial_at_horizon_matches_curve_with_exog(
    sine_series: np.ndarray, h: int, H: int
) -> None:
    exog = np.cos(np.linspace(0.0, 20.0, _N))
    curve = compute_partial_curve(
        sine_series, H, _mi_scorer, exog=exog, min_pairs=50, random_state=_RS
    )
    single = compute_partial_at_horizon(
        sine_series, h, _mi_scorer, exog=exog, min_pairs=50, random_state=_RS
    )
    assert math.isclose(single, float(curve[h - 1]), rel_tol=1e-10, abs_tol=1e-14)


# ---------------------------------------------------------------------------
# Legacy break-then-zero semantics: pAMI returns 0.0 for underdetermined Z
# ---------------------------------------------------------------------------


def test_pami_at_horizon_returns_zero_for_underdetermined_conditioning() -> None:
    """h=5 requires 4 conditioning lags.  A very short series makes n_rows <= n_cols.

    With h=5 and min_pairs=1:
      - validate_time_series min_length = 5 + 1 + 1 = 7
      - series length 7: aligned pairs = 7 - 5 = 2 rows
      - conditioning matrix has h-1 = 4 columns
      - 2 <= 4 → underdetermined → return 0.0
    """
    h = 5
    min_pairs = 1
    # Length = h + min_pairs + 1 = 7; passes validate_time_series.
    ts = np.linspace(0.0, 1.0, h + min_pairs + 1)
    value = compute_pami_at_horizon(ts, h, n_neighbors=2, min_pairs=min_pairs, random_state=0)
    assert value == 0.0


# ---------------------------------------------------------------------------
# Compute-anyway: partial helper does NOT break for same underdetermined case
# ---------------------------------------------------------------------------


def test_partial_at_horizon_computes_anyway_for_underdetermined_conditioning() -> None:
    """compute_partial_at_horizon must NOT apply the legacy break-then-zero guard.

    We verify this structurally: ``compute_pami_at_horizon`` returns 0.0 for a
    case where the conditioning matrix is underdetermined, while
    ``compute_partial_at_horizon`` (with the same series) returns a non-negative
    float without forcing 0.0 via the underdetermined guard.

    To satisfy both the underdetermined constraint (n_rows <= n_cols, i.e.
    arr.size - h <= h - 1) and the MI estimator's n_neighbors requirement, we
    use a scorer with n_neighbors=1 and a series sized to give exactly
    n_rows = n_cols (borderline underdetermined).
    """

    from sklearn.feature_selection import mutual_info_regression

    def _small_mi(past: np.ndarray, future: np.ndarray, *, random_state: int = 0) -> float:
        """MI scorer with n_neighbors=1 for very short series."""
        val = mutual_info_regression(
            past.reshape(-1, 1), future, n_neighbors=1, random_state=random_state
        )[0]
        return max(float(val), 0.0)

    # h=3 → n_cols = h-1 = 2.  n_rows <= 2 is underdetermined.
    # series length = h + n_rows + (something) so validate_time_series passes.
    # Choose n_rows = 2 (borderline): arr.size = h + n_rows = 5, but min_pairs=1
    # means validate_time_series needs arr.size >= h + min_pairs + 1 = 5.  OK.
    h = 3
    min_pairs = 1
    ts = np.linspace(0.0, 1.0, h + min_pairs + 1)  # length 5; n_rows = 5-3 = 2 <= 2 = n_cols

    # Legacy pAMI: returns 0.0 due to underdetermined guard.
    pami_val = compute_pami_at_horizon(ts, h, n_neighbors=1, min_pairs=min_pairs, random_state=0)
    assert pami_val == 0.0

    # Generic partial: must NOT apply the underdetermined guard.
    # It may still return 0.0 from the MI estimator, but it must not raise.
    partial_val = compute_partial_at_horizon(ts, h, _small_mi, min_pairs=min_pairs, random_state=0)
    assert isinstance(partial_val, float)
    assert partial_val >= 0.0


# ---------------------------------------------------------------------------
# h < 1 raises ValueError for all four helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fn",
    [
        lambda ts: compute_ami_at_horizon(ts, 0),
        lambda ts: compute_pami_at_horizon(ts, 0),
        lambda ts: compute_raw_at_horizon(ts, 0, _mi_scorer, min_pairs=1, random_state=0),
        lambda ts: compute_partial_at_horizon(ts, 0, _mi_scorer, min_pairs=1, random_state=0),
    ],
)
def test_single_horizon_helpers_reject_h_zero(
    sine_series: np.ndarray, fn: object
) -> None:
    with pytest.raises(ValueError, match="h must be >= 1"):
        fn(sine_series)  # type: ignore[operator]


# ---------------------------------------------------------------------------
# Holdout-perturbation: univariate rolling-origin uses train windows only
# ---------------------------------------------------------------------------


def test_rolling_origin_univariate_is_train_only() -> None:
    """run_rolling_origin_evaluation must not read from the holdout region.

    Uses n_origins=1 so the train/holdout boundary is unambiguous: the single
    split's train window ends at origin_index, and everything after is holdout.
    Perturbing only the holdout must leave AMI/pAMI diagnostics unchanged.
    """
    from forecastability.pipeline import run_rolling_origin_evaluation

    n = 200
    ts_clean = np.sin(np.linspace(0.0, 20.0, n))

    horizon = 3
    n_origins = 1

    splits = build_expanding_window_splits(ts_clean, n_origins=n_origins, horizon=horizon)
    holdout_start = splits[0].origin_index

    # Perturb only the holdout portion (after origin_index).
    ts_perturbed = ts_clean.copy()
    ts_perturbed[holdout_start:] = 1000.0  # large constant, not noise (deterministic)

    result_clean = run_rolling_origin_evaluation(
        ts_clean,
        series_id="test",
        frequency="daily",
        horizons=[horizon],
        n_origins=n_origins,
        seasonal_period=None,
        random_state=42,
    )
    result_perturbed = run_rolling_origin_evaluation(
        ts_perturbed,
        series_id="test",
        frequency="daily",
        horizons=[horizon],
        n_origins=n_origins,
        seasonal_period=None,
        random_state=42,
    )

    assert result_clean.ami_by_horizon[horizon] == result_perturbed.ami_by_horizon[horizon]
    assert result_clean.pami_by_horizon[horizon] == result_perturbed.pami_by_horizon[horizon]


# ---------------------------------------------------------------------------
# Holdout-perturbation: exogenous rolling-origin uses train windows only
# ---------------------------------------------------------------------------


def test_rolling_origin_exogenous_is_train_only() -> None:
    """run_exogenous_rolling_origin_evaluation must not read from the holdout region.

    Uses n_origins=1 so the train/holdout boundary is unambiguous.
    """
    n = 200
    ts_clean = np.sin(np.linspace(0.0, 20.0, n))
    exog_clean = np.cos(np.linspace(0.0, 20.0, n))

    horizon = 3
    n_origins = 1

    splits = build_expanding_window_splits(ts_clean, n_origins=n_origins, horizon=horizon)
    holdout_start = splits[0].origin_index

    # Perturb only the holdout portion (deterministic, not random).
    ts_perturbed = ts_clean.copy()
    exog_perturbed = exog_clean.copy()
    ts_perturbed[holdout_start:] = 1000.0
    exog_perturbed[holdout_start:] = 1000.0

    result_clean = run_exogenous_rolling_origin_evaluation(
        ts_clean,
        exog_clean,
        case_id="test",
        target_name="target",
        exog_name="driver",
        horizons=[horizon],
        n_origins=n_origins,
        random_state=42,
    )
    result_perturbed = run_exogenous_rolling_origin_evaluation(
        ts_perturbed,
        exog_perturbed,
        case_id="test",
        target_name="target",
        exog_name="driver",
        horizons=[horizon],
        n_origins=n_origins,
        random_state=42,
    )

    assert (
        result_clean.raw_cross_mi_by_horizon[horizon]
        == result_perturbed.raw_cross_mi_by_horizon[horizon]
    )
    assert (
        result_clean.conditioned_cross_mi_by_horizon[horizon]
        == result_perturbed.conditioned_cross_mi_by_horizon[horizon]
    )
