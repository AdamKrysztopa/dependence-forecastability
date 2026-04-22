"""Tests for sparse lag selection service (xami_sparse)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from forecastability.metrics.scorers import DependenceScorer, default_registry
from forecastability.services.sparse_lag_selection_service import (
    SparseLagSelectionConfig,
    select_sparse_lags,
)
from forecastability.utils.synthetic import generate_lagged_exog_panel
from forecastability.utils.types import LaggedExogSelectionRow


def _selected_rows(rows: Sequence[LaggedExogSelectionRow]) -> list[LaggedExogSelectionRow]:
    """Extract selected rows preserving selection order."""
    selected = [row for row in rows if row.selected_for_tensor]
    return sorted(selected, key=lambda row: row.selection_order or 0)


def _weak_noise_scorer(
    past: np.ndarray,
    future: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Deterministic weak scorer used to lock strongest-first selection behavior."""
    del future, random_state
    return float(past.size) * 1e-5


def _insufficient_pairs_error_scorer(
    past: np.ndarray,
    future: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Raise a scorer ValueError that represents expected sample-size failure."""
    del past, future, random_state
    raise ValueError("insufficient pairs for scorer evaluation")


def _unexpected_value_error_scorer(
    past: np.ndarray,
    future: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Raise an unexpected scorer ValueError that must propagate."""
    del past, future, random_state
    raise ValueError("unexpected scorer failure")


def test_sparse_selector_emits_predictive_rows_only_and_is_deterministic() -> None:
    """Selector should be deterministic and never emit lag-0 candidates."""
    panel = generate_lagged_exog_panel(n=1500, seed=42)
    target = panel["target"].to_numpy()
    driver = panel["direct_lag2"].to_numpy()

    registry = default_registry()
    scorer = registry.get("mi").scorer
    assert isinstance(scorer, DependenceScorer)

    rows_first = select_sparse_lags(
        target,
        driver,
        max_lag=6,
        scorer=scorer,
        random_state=42,
        target_name="target",
        driver_name="direct_lag2",
    )
    rows_second = select_sparse_lags(
        target,
        driver,
        max_lag=6,
        scorer=scorer,
        random_state=42,
        target_name="target",
        driver_name="direct_lag2",
    )

    assert rows_first == rows_second
    assert len(rows_first) == 6
    assert all(row.lag >= 1 for row in rows_first)
    assert all(row.selector_name == "xami_sparse" for row in rows_first)
    assert all(row.tensor_role == "predictive" for row in rows_first)

    selected = _selected_rows(rows_first)
    assert len(selected) <= 3
    expected_orders = list(range(1, len(selected) + 1))
    actual_orders = [row.selection_order for row in selected]
    assert actual_orders == expected_orders
    assert any(row.lag == 2 for row in selected)


def test_sparse_selector_respects_config_and_never_returns_lag0() -> None:
    """Selector should honor ``min_lag`` and produce one row per candidate lag."""
    panel = generate_lagged_exog_panel(n=1200, seed=7)
    target = panel["target"].to_numpy()
    driver = panel["mediated_lag1"].to_numpy()

    registry = default_registry()
    scorer = registry.get("mi").scorer
    assert isinstance(scorer, DependenceScorer)

    config = SparseLagSelectionConfig(min_lag=2, max_selected_per_driver=2)
    rows = select_sparse_lags(
        target,
        driver,
        max_lag=6,
        scorer=scorer,
        config=config,
        random_state=100,
    )

    assert [row.lag for row in rows] == [2, 3, 4, 5, 6]
    assert all(row.lag != 0 for row in rows)
    assert sum(1 for row in rows if row.selected_for_tensor) <= config.max_selected_per_driver


def test_sparse_selector_selects_strongest_first_even_for_weak_scores() -> None:
    """The strongest evaluated lag must always be selected first, even below threshold."""
    rng = np.random.default_rng(123)
    target = rng.normal(size=256)
    driver = rng.normal(size=256)

    config = SparseLagSelectionConfig(score_threshold=0.02, relative_threshold=0.20)
    rows = select_sparse_lags(
        target,
        driver,
        max_lag=6,
        scorer=_weak_noise_scorer,
        config=config,
        random_state=17,
    )

    selected = _selected_rows(rows)
    strongest = min(rows, key=lambda row: (-(row.score or 0.0), row.lag))

    assert max((row.score or 0.0) for row in rows) < config.score_threshold
    assert len(selected) == 1
    assert selected[0].lag == strongest.lag
    assert selected[0].selection_order == 1
    assert all(row.lag >= 1 for row in rows)


def test_sparse_selector_handles_insufficient_pairs_value_error_as_zero_score() -> None:
    """Expected insufficient-sample scorer errors should be treated as zero score."""
    rng = np.random.default_rng(321)
    target = rng.normal(size=256)
    driver = rng.normal(size=256)

    rows = select_sparse_lags(
        target,
        driver,
        max_lag=4,
        scorer=_insufficient_pairs_error_scorer,
        random_state=11,
    )

    assert len(rows) == 4
    assert all((row.score or 0.0) == 0.0 for row in rows)


def test_sparse_selector_propagates_unexpected_scorer_value_error() -> None:
    """Unexpected scorer ValueErrors must not be silently masked."""
    rng = np.random.default_rng(654)
    target = rng.normal(size=256)
    driver = rng.normal(size=256)

    try:
        _ = select_sparse_lags(
            target,
            driver,
            max_lag=4,
            scorer=_unexpected_value_error_scorer,
            random_state=12,
        )
    except ValueError as exc:
        assert "unexpected scorer failure" in str(exc)
    else:
        raise AssertionError("Expected unexpected scorer ValueError to propagate")


def test_sparse_selector_config_rejects_invalid_min_lag() -> None:
    """Config should reject ``min_lag < 1`` to enforce predictive-only output."""
    try:
        SparseLagSelectionConfig(min_lag=0)
    except ValueError as exc:
        assert "min_lag" in str(exc)
    else:
        raise AssertionError("Expected ValueError for min_lag=0")


def test_sparse_selector_rejects_mismatched_lengths() -> None:
    """Selector should reject non-aligned target/driver lengths."""
    registry = default_registry()
    scorer = registry.get("mi").scorer
    assert isinstance(scorer, DependenceScorer)

    target = np.linspace(0.0, 1.0, 200)
    driver = np.linspace(0.0, 1.0, 199)

    try:
        select_sparse_lags(target, driver, max_lag=3, scorer=scorer)
    except ValueError as exc:
        assert "identical lengths" in str(exc)
    else:
        raise AssertionError("Expected ValueError for mismatched lengths")
