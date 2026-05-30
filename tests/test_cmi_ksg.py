"""Unit tests for the Frenzel-Pompe KSG-CMI estimator (cmi_ksg.py)."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np

from forecastability.diagnostics.cmi_ksg import (
    compute_conditional_mutual_information_ksg,
    compute_transfer_entropy_ksg,
)


def test_hard_cutoff_returns_nan() -> None:
    """N_eff < k^(d+2) triggers the hard cutoff and returns nan."""
    rng = np.random.default_rng(0)
    # N=10, k=5, d=1 → cutoff = 5^3 = 125 > 10 → nan
    x = rng.normal(size=10)
    y = rng.normal(size=10)
    z = rng.normal(size=(10, 1))
    result = compute_conditional_mutual_information_ksg(x, y, z, lag=1, k=5)
    assert np.isnan(result), f"Expected nan for N < cutoff, got {result}"


def test_valid_mask_all_false_returns_nan() -> None:
    """When all marginal counts are 0, the valid-mask guard returns nan.

    This tests the defensive guard introduced by CR-07: rather than clamping
    zero counts to 1 (which injects positive CMI bias), the implementation
    excludes those points. When no valid points remain, it returns nan.

    We force this by replacing the cKDTree class itself with a mock that
    returns empty neighbour lists (only self), simulating the degenerate-ball
    case where all marginal counts are 0.
    """
    from unittest.mock import MagicMock

    rng = np.random.default_rng(42)
    # N=200 passes hard cutoff (k=3, d=1 → cutoff=27)
    n = 200
    x = rng.normal(size=n)
    y = rng.normal(size=n)
    z_arr = rng.normal(size=(n, 1))

    # Build a mock cKDTree class:
    # - query() returns real distances so the eps computation works normally
    # - query_ball_point() returns [0] (length 1 → count 0 after -1 self-subtraction)
    #   for marginal trees (not the joint tree, which only calls query())
    real_distances = np.ones((n, 4)) * 0.5  # dummy eps > 0
    real_distances[:, 0] = 0.0  # self is 0

    mock_tree_instance = MagicMock()
    mock_tree_instance.query.return_value = (real_distances, np.zeros((n, 4), dtype=int))
    # return_length=True returns an int ndarray; mock must match that shape.
    mock_tree_instance.query_ball_point.return_value = np.zeros(n, dtype=int)

    MockCKDTree = MagicMock(return_value=mock_tree_instance)

    with patch("forecastability.diagnostics.cmi_ksg.cKDTree", MockCKDTree):
        result = compute_conditional_mutual_information_ksg(x, y, z_arr, lag=1, k=3)

    assert np.isnan(result), (
        f"Expected nan when all marginal counts are 0 (valid mask all-False), got {result}"
    )


def test_nan_raw_value_yields_blocked_not_computed_status() -> None:
    """When compute_conditional_mutual_information_ksg returns nan, status must not be 'computed'.

    This tests the caller-side guard in compute_transfer_entropy_ksg (CR-07):
    if the CMI estimator returns nan (e.g., degenerate-ball path), the result
    must use status='blocked_sample_size', not status='computed'.
    A 'computed' result with nan value would violate the schema contract.
    """
    rng = np.random.default_rng(7)
    n = 200
    x = rng.normal(size=n)
    y = rng.normal(size=n)

    # Patch the inner CMI call to return nan, simulating the degenerate path.
    with patch(
        "forecastability.diagnostics.cmi_ksg.compute_conditional_mutual_information_ksg",
        return_value=float("nan"),
    ):
        result = compute_transfer_entropy_ksg(x, y, lag=1, k=3)

    assert result.status == "blocked_sample_size", (
        f"Expected status='blocked_sample_size' when CMI returns nan, got '{result.status}'"
    )
    assert np.isnan(result.value), (
        f"Expected nan value for blocked_sample_size status, got {result.value}"
    )
    assert np.isnan(result.raw_value), (
        f"Expected nan raw_value for blocked_sample_size status, got {result.raw_value}"
    )


def test_computed_status_never_carries_nan_value() -> None:
    """status='computed' result must always have a finite (non-nan) value.

    Schema contract: computed implies value is a valid float (possibly 0.0
    after non-negativity clamping).
    """
    rng = np.random.default_rng(123)
    n = 500
    x = rng.normal(size=n)
    y = 0.6 * x + rng.normal(scale=0.5, size=n)
    result = compute_transfer_entropy_ksg(x, y, lag=1, k=3)
    if result.status == "computed":
        assert not np.isnan(result.value), "status='computed' must never carry a nan value"
        assert result.value >= 0.0, "status='computed' value must be non-negative after clamping"
