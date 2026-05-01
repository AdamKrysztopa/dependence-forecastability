"""Tests for directional transfer entropy service and scorer integration."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.metrics.scorers import DependenceScorer, default_registry, te_scorer
from forecastability.services.transfer_entropy_service import (
    compute_transfer_entropy,
    compute_transfer_entropy_curve,
)


def _generate_directional_pair(
    n: int = 1800,
    *,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate a synthetic directional pair with x_{t-1} -> y_t structure."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n, dtype=float)
    y = np.zeros(n, dtype=float)
    for t in range(1, n):
        x[t] = 0.8 * x[t - 1] + rng.normal(scale=0.8)
        y[t] = 0.7 * y[t - 1] + 0.5 * x[t - 1] + rng.normal(scale=0.8)
    return x, y


def test_transfer_entropy_is_directional_for_synthetic_pair() -> None:
    x, y = _generate_directional_pair(seed=7)
    te_xy = compute_transfer_entropy(x, y, lag=1, random_state=11, min_pairs=100)
    te_yx = compute_transfer_entropy(y, x, lag=1, random_state=11, min_pairs=100)

    assert te_xy >= 0.0
    assert te_yx >= 0.0
    assert te_xy > te_yx


def test_transfer_entropy_curve_shape_and_non_negative_values() -> None:
    x, y = _generate_directional_pair(seed=21)
    curve = compute_transfer_entropy_curve(
        x,
        y,
        max_lag=5,
        history_mode="canonical",
        random_state=13,
        min_pairs=80,
    )

    assert curve.shape == (5,)
    assert np.all(np.isfinite(curve))
    assert np.all(curve >= 0.0)


def test_transfer_entropy_rejects_invalid_lag() -> None:
    x, y = _generate_directional_pair(seed=5)
    with pytest.raises(ValueError, match="lag must be >= 1"):
        compute_transfer_entropy(x, y, lag=0)


def test_transfer_entropy_rejects_history_above_lag_minus_one() -> None:
    x, y = _generate_directional_pair(seed=5)
    with pytest.raises(ValueError, match="history must be <= lag - 1"):
        compute_transfer_entropy(x, y, lag=2, history=2)


def test_transfer_entropy_rejects_mismatched_series_lengths() -> None:
    x, y = _generate_directional_pair(seed=5)
    with pytest.raises(ValueError, match="identical lengths"):
        compute_transfer_entropy(x[:-1], y, lag=1)


def test_transfer_entropy_rejects_too_short_series() -> None:
    x = np.linspace(0.0, 1.0, 20)
    y = np.linspace(1.0, 2.0, 20)
    with pytest.raises(ValueError, match="too short"):
        compute_transfer_entropy(x, y, lag=3, min_pairs=30)


def test_transfer_entropy_rejects_min_pairs_below_conditional_floor() -> None:
    x, y = _generate_directional_pair(seed=15)
    with pytest.raises(ValueError, match="min_pairs must be >= 50"):
        compute_transfer_entropy(x, y, lag=1, min_pairs=30)


def test_transfer_entropy_rejects_too_few_rows_for_nonempty_history() -> None:
    x, y = _generate_directional_pair(n=90, seed=15)
    with pytest.raises(ValueError, match=r"at least 2 \* min_pairs"):
        compute_transfer_entropy(x, y, lag=3, min_pairs=50)


def test_te_scorer_factory_matches_service_value() -> None:
    x, y = _generate_directional_pair(seed=17)
    scorer = te_scorer(lag=1)

    direct = compute_transfer_entropy(x, y, lag=1, random_state=23)
    via_scorer = scorer(x, y, random_state=23)
    assert via_scorer == pytest.approx(direct)


def test_default_registry_exposes_te_scorer() -> None:
    registry = default_registry()
    info = registry.get("te")

    assert info.family == "nonlinear"
    scorer = info.scorer
    assert isinstance(scorer, DependenceScorer)


# ---------------------------------------------------------------------------
# PBE-F16: curve hoist parity and validation guards
# ---------------------------------------------------------------------------


def test_compute_transfer_entropy_curve_matches_per_lag_calls() -> None:
    x, y = _generate_directional_pair(seed=1234)
    curve = compute_transfer_entropy_curve(
        x,
        y,
        max_lag=4,
        min_pairs=50,
        backend="linear_residual",
        random_state=42,
    )
    expected = np.array(
        [
            compute_transfer_entropy(
                x,
                y,
                lag=lag,
                backend="linear_residual",
                min_pairs=50,
                random_state=42 + lag,
            )
            for lag in range(1, 5)
        ],
        dtype=float,
    )
    assert np.array_equal(curve, expected)


def test_compute_transfer_entropy_curve_rejects_invalid_max_lag() -> None:
    x, y = _generate_directional_pair(seed=3)
    with pytest.raises(ValueError, match="max_lag must be >= 1"):
        compute_transfer_entropy_curve(x, y, max_lag=0)


def test_compute_transfer_entropy_curve_rejects_invalid_history_mode() -> None:
    x, y = _generate_directional_pair(seed=4)
    with pytest.raises(ValueError, match="history_mode must be one of"):
        compute_transfer_entropy_curve(x, y, max_lag=2, history_mode="bogus")  # type: ignore[arg-type]


def test_compute_transfer_entropy_curve_rejects_mismatched_lengths() -> None:
    rng = np.random.default_rng(5)
    x = rng.standard_normal(400)
    y = rng.standard_normal(380)
    with pytest.raises(ValueError, match="identical lengths"):
        compute_transfer_entropy_curve(x, y, max_lag=2, min_pairs=50)
