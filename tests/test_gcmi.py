"""Tests for V3-F02 Gaussian Copula Mutual Information (GCMI).

Covers:
- Mathematical properties (non-negativity, symmetry, determinism, high/low MI)
- Lagged computation and lag validation
- Curve computation shape and validity
- Scorer protocol conformance and registry entry
- GcmiResult round-trip and frozen-model mutation rejection
- Edge cases (constant, misaligned, short arrays)
- Service facade import
"""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RNG = np.random.default_rng(42)


def _iid(n: int = 300) -> np.ndarray:
    return np.random.default_rng(99).standard_normal(n)


# ---------------------------------------------------------------------------
# 1. Mathematical properties
# ---------------------------------------------------------------------------


def test_compute_gcmi_high_mi_for_identical_arrays() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi

    rng = np.random.default_rng(0)
    x = rng.standard_normal(200)
    mi = compute_gcmi(x, x)
    # Identical arrays → rho = 1 → MI ≈ 14.4 bits
    assert mi > 13.0


def test_compute_gcmi_low_mi_for_independent_arrays() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi

    rng = np.random.default_rng(7)
    mi = compute_gcmi(rng.standard_normal(500), rng.standard_normal(500))
    assert mi < 0.1


def test_compute_gcmi_non_negative() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi

    rng = np.random.default_rng(3)
    for _ in range(10):
        mi = compute_gcmi(rng.standard_normal(80), rng.standard_normal(80))
        assert mi >= 0.0


def test_compute_gcmi_deterministic() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi

    rng = np.random.default_rng(55)
    x = rng.standard_normal(120)
    y = rng.standard_normal(120)
    assert compute_gcmi(x, y) == compute_gcmi(x, y)


def test_compute_gcmi_symmetric_at_zero_lag() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi

    rng = np.random.default_rng(11)
    x = rng.standard_normal(150)
    y = 0.6 * x + 0.4 * rng.standard_normal(150)
    assert compute_gcmi(x, y) == pytest.approx(compute_gcmi(y, x))


# ---------------------------------------------------------------------------
# 2. Lagged computation
# ---------------------------------------------------------------------------


def test_compute_gcmi_at_lag_peaks_at_true_lag() -> None:
    """MI at the true lag-3 shift should be near maximum (~14 bits)."""
    from forecastability.diagnostics.gcmi import compute_gcmi_at_lag

    n = 200
    rng = np.random.default_rng(0)
    x = rng.standard_normal(n)
    # y[3:] == x[:-3] → perfectly aligned at lag=3
    y = np.concatenate([rng.standard_normal(3), x[:-3]])

    mi_lag3 = compute_gcmi_at_lag(x, y, lag=3)
    mi_lag1 = compute_gcmi_at_lag(x, y, lag=1)

    # Perfect alignment at lag=3 should produce near-maximum MI
    assert mi_lag3 > 10.0
    # And substantially higher than a misaligned lag
    assert mi_lag3 > mi_lag1 * 5


def test_compute_gcmi_at_lag_zero_raises_value_error() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi_at_lag

    x = _iid()
    with pytest.raises(ValueError, match="lag must be >= 1"):
        compute_gcmi_at_lag(x, x.copy(), lag=0)


def test_compute_gcmi_at_lag_negative_lag_raises_value_error() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi_at_lag

    x = _iid()
    with pytest.raises(ValueError):
        compute_gcmi_at_lag(x, x.copy(), lag=-1)


def test_compute_gcmi_at_lag_too_large_raises_value_error() -> None:
    """lag > len(x) - min_pairs should raise ValueError."""
    from forecastability.diagnostics.gcmi import compute_gcmi_at_lag

    x = _iid(60)
    # min_pairs=30, so lag=31 requires 61 samples but we have 60
    with pytest.raises(ValueError):
        compute_gcmi_at_lag(x, x.copy(), lag=31, min_pairs=30)


# ---------------------------------------------------------------------------
# 3. Curve computation
# ---------------------------------------------------------------------------


def test_compute_gcmi_curve_shape_and_dtype() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi_curve

    x = _iid(200)
    y = _iid(200)
    curve = compute_gcmi_curve(x, y, max_lag=10)
    assert curve.shape == (10,)
    assert curve.dtype == float


def test_compute_gcmi_curve_max_lag_zero_raises_value_error() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi_curve

    x = _iid()
    with pytest.raises(ValueError, match="max_lag must be >= 1"):
        compute_gcmi_curve(x, x.copy(), max_lag=0)


def test_compute_gcmi_curve_all_non_negative() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi_curve

    x = _iid(200)
    y = _iid(200)
    curve = compute_gcmi_curve(x, y, max_lag=8)
    assert np.all(curve >= 0.0)


# ---------------------------------------------------------------------------
# 4. Scorer protocol
# ---------------------------------------------------------------------------


def test_gcmi_scorer_satisfies_dependence_scorer_protocol() -> None:
    from forecastability.metrics.scorers import DependenceScorer, gcmi_scorer

    scorer = gcmi_scorer()
    assert isinstance(scorer, DependenceScorer)


def test_gcmi_scorer_ignores_random_state() -> None:
    from forecastability.metrics.scorers import gcmi_scorer

    rng = np.random.default_rng(1)
    past = rng.standard_normal(100)
    future = 0.7 * past + 0.3 * rng.standard_normal(100)
    scorer = gcmi_scorer()
    assert scorer(past, future, random_state=0) == scorer(past, future, random_state=99999)


def test_gcmi_scorer_lag_2() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi_at_lag
    from forecastability.metrics.scorers import gcmi_scorer

    rng = np.random.default_rng(5)
    past = rng.standard_normal(120)
    future = rng.standard_normal(120)
    scorer = gcmi_scorer(lag=2)
    expected = compute_gcmi_at_lag(past, future, lag=2)
    assert scorer(past, future) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# 5. Registry entry
# ---------------------------------------------------------------------------


def test_default_registry_has_gcmi_entry() -> None:
    from forecastability.metrics.scorers import default_registry

    registry = default_registry()
    assert "gcmi" in registry


def test_gcmi_registry_entry_family_is_nonlinear() -> None:
    from forecastability.metrics.scorers import default_registry

    registry = default_registry()
    info = registry.get("gcmi")
    assert info.family == "nonlinear"


def test_gcmi_registry_scorer_returns_non_negative_float() -> None:
    from forecastability.metrics.scorers import DependenceScorer, default_registry

    registry = default_registry()
    scorer = registry.get("gcmi").scorer
    assert isinstance(scorer, DependenceScorer)
    rng = np.random.default_rng(17)
    past = rng.standard_normal(100)
    future = rng.standard_normal(100)
    result = scorer(past, future, random_state=0)
    assert isinstance(result, float)
    assert result >= 0.0


# ---------------------------------------------------------------------------
# 6. GcmiResult round-trip and frozen mutation
# ---------------------------------------------------------------------------


def test_gcmi_result_serialise_round_trip() -> None:
    from forecastability.utils.types import GcmiResult

    obj = GcmiResult(source="x", target="y", lag=2, gcmi_value=0.45)
    dumped = obj.model_dump()
    assert dumped["source"] == "x"
    assert dumped["target"] == "y"
    assert dumped["lag"] == 2
    assert dumped["gcmi_value"] == pytest.approx(0.45)
    reconstructed = GcmiResult(**dumped)
    assert reconstructed == obj


def test_gcmi_result_frozen_rejects_mutation() -> None:
    from forecastability.utils.types import GcmiResult

    obj = GcmiResult(source="x", target="y", lag=1, gcmi_value=0.3)
    with pytest.raises((ValidationError, TypeError)):
        obj.gcmi_value = 9.9  # pyright: ignore[reportAttributeAccessIssue]


# ---------------------------------------------------------------------------
# 7. Edge cases
# ---------------------------------------------------------------------------


def test_compute_gcmi_constant_array_raises_value_error() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi

    const = np.ones(100)
    valid = _iid(100)
    with pytest.raises(ValueError):
        compute_gcmi(const, valid)


def test_compute_gcmi_misaligned_arrays_raises_value_error() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi

    rng = np.random.default_rng(21)
    x = rng.standard_normal(100)
    y = rng.standard_normal(80)
    with pytest.raises(ValueError):
        compute_gcmi(x, y)


def test_compute_gcmi_too_short_raises_value_error() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi

    rng = np.random.default_rng(22)
    short = rng.standard_normal(10)
    # default min_pairs=30, so 10 samples < 30 → ValueError
    with pytest.raises(ValueError):
        compute_gcmi(short, short.copy())


# ---------------------------------------------------------------------------
# 8. Service facade import
# ---------------------------------------------------------------------------


def test_service_facade_functions_are_importable() -> None:
    from forecastability.services.gcmi_service import (  # noqa: F401
        compute_gcmi,
        compute_gcmi_at_lag,
        compute_gcmi_curve,
    )


def test_service_facade_functions_are_callable() -> None:
    from forecastability.services.gcmi_service import (
        compute_gcmi,
        compute_gcmi_at_lag,
        compute_gcmi_curve,
    )

    assert callable(compute_gcmi)
    assert callable(compute_gcmi_at_lag)
    assert callable(compute_gcmi_curve)


# ---------------------------------------------------------------------------
# 9. PBE-F16: curve hoist parity and validation guards
# ---------------------------------------------------------------------------


def test_compute_gcmi_curve_matches_per_lag_calls() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi_at_lag, compute_gcmi_curve

    rng = np.random.default_rng(2026)
    x = rng.standard_normal(400)
    y = 0.7 * x + 0.3 * rng.standard_normal(400)
    curve = compute_gcmi_curve(x, y, max_lag=10, min_pairs=30)
    expected = np.array(
        [compute_gcmi_at_lag(x, y, lag=h, min_pairs=30) for h in range(1, 11)],
        dtype=float,
    )
    assert np.array_equal(curve, expected)


def test_compute_gcmi_curve_rejects_mismatched_lengths() -> None:
    from forecastability.diagnostics.gcmi import compute_gcmi_curve

    rng = np.random.default_rng(0)
    x = rng.standard_normal(300)
    y = rng.standard_normal(280)
    with pytest.raises(ValueError, match="identical lengths"):
        compute_gcmi_curve(x, y, max_lag=5, min_pairs=30)
