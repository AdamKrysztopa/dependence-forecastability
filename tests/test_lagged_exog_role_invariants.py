"""Lagged-exogenous role and selection invariants (Phase 3)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forecastability import (
    generate_lagged_exog_panel,
    run_covariant_analysis,
    run_lagged_exogenous_triage,
)
from forecastability.metrics.scorers import DependenceScorer, default_registry
from forecastability.services.cross_correlation_profile_service import (
    compute_cross_correlation_profile,
)
from forecastability.services.exog_partial_curve_service import compute_exog_partial_curve
from forecastability.services.exog_raw_curve_service import compute_exog_raw_curve


@pytest.fixture
def lagged_panel() -> pd.DataFrame:
    """Return deterministic lagged-exogenous benchmark panel."""
    return generate_lagged_exog_panel(n=1500, seed=42)


def test_zero_lag_row_is_diagnostic_only(lagged_panel: pd.DataFrame) -> None:
    """Lag-0 rows must remain instant/diagnostic by default."""
    target = lagged_panel["target"].to_numpy()
    drivers = {
        "direct_lag2": lagged_panel["direct_lag2"].to_numpy(),
        "mediated_lag1": lagged_panel["mediated_lag1"].to_numpy(),
        "redundant": lagged_panel["redundant"].to_numpy(),
        "instant_only": lagged_panel["instant_only"].to_numpy(),
    }

    bundle = run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=6,
        n_surrogates=99,
        random_state=42,
    )

    lag0_rows = [row for row in bundle.profile_rows if row.lag == 0]
    assert len(lag0_rows) == len(drivers)
    assert all(row.lag_role == "instant" for row in lag0_rows)
    assert all(row.tensor_role == "diagnostic" for row in lag0_rows)
    assert all(row.lag != 0 for row in bundle.selected_lags)


def test_direct_driver_selected_at_expected_lag(lagged_panel: pd.DataFrame) -> None:
    """Direct benchmark driver should select lag 2 under default selector settings."""
    target = lagged_panel["target"].to_numpy()
    direct = lagged_panel["direct_lag2"].to_numpy()

    bundle = run_lagged_exogenous_triage(
        target,
        {"direct_lag2": direct},
        target_name="target",
        max_lag=6,
        n_surrogates=99,
        random_state=42,
    )

    selected = [row for row in bundle.selected_lags if row.selected_for_tensor]
    assert len(selected) == 1
    assert selected[0].driver == "direct_lag2"
    assert selected[0].lag == 2


def test_mediated_driver_selected_at_expected_lag(lagged_panel: pd.DataFrame) -> None:
    """Mediated benchmark driver should select lag 1 under default selector settings."""
    target = lagged_panel["target"].to_numpy()
    mediated = lagged_panel["mediated_lag1"].to_numpy()

    bundle = run_lagged_exogenous_triage(
        target,
        {"mediated_lag1": mediated},
        target_name="target",
        max_lag=6,
        n_surrogates=99,
        random_state=42,
    )

    selected = [row for row in bundle.selected_lags if row.selected_for_tensor]
    assert len(selected) == 1
    assert selected[0].driver == "mediated_lag1"
    assert selected[0].lag == 1


def test_contemporaneous_only_driver_not_selected_by_default(lagged_panel: pd.DataFrame) -> None:
    """Contemporaneous driver may pick a predictive lag, but never lag 0 by default."""
    target = lagged_panel["target"].to_numpy()
    instant = lagged_panel["instant_only"].to_numpy()

    bundle = run_lagged_exogenous_triage(
        target,
        {"instant_only": instant},
        target_name="target",
        max_lag=6,
        n_surrogates=99,
        random_state=42,
    )

    selected = [row for row in bundle.selected_lags if row.selected_for_tensor]
    assert len(selected) == 1
    assert selected[0].lag >= 1

    lag0_rows = [row for row in bundle.profile_rows if row.lag == 0]
    assert len(lag0_rows) == 1
    assert lag0_rows[0].tensor_role == "diagnostic"


def test_no_default_callsite_behavior_change_in_existing_curve_services() -> None:
    """Default curve call paths should match explicit predictive lag-range behavior."""
    panel = generate_lagged_exog_panel(n=900, seed=42)
    target = panel["target"].to_numpy()
    driver = panel["direct_lag2"].to_numpy()

    registry = default_registry()
    scorer = registry.get("mi").scorer
    assert isinstance(scorer, DependenceScorer)

    max_lag = 4
    raw_default = compute_exog_raw_curve(
        target,
        driver,
        max_lag,
        scorer,
        min_pairs=30,
        random_state=42,
    )
    raw_explicit = compute_exog_raw_curve(
        target,
        driver,
        max_lag,
        scorer,
        min_pairs=30,
        random_state=42,
        lag_range=(1, max_lag),
    )

    partial_default = compute_exog_partial_curve(
        target,
        driver,
        max_lag,
        scorer,
        min_pairs=50,
        random_state=42,
    )
    partial_explicit = compute_exog_partial_curve(
        target,
        driver,
        max_lag,
        scorer,
        min_pairs=50,
        random_state=42,
        lag_range=(1, max_lag),
    )

    assert np.allclose(raw_default, raw_explicit)
    assert np.allclose(partial_default, partial_explicit)


def test_redundant_driver_pruned_by_xami_sparse(lagged_panel: pd.DataFrame) -> None:
    """Redundant benchmark driver should keep only one selected lag at default settings."""
    target = lagged_panel["target"].to_numpy()
    redundant = lagged_panel["redundant"].to_numpy()

    bundle = run_lagged_exogenous_triage(
        target,
        {"redundant": redundant},
        target_name="target",
        max_lag=6,
        n_surrogates=99,
        random_state=42,
    )

    selected = [row for row in bundle.selected_lags if row.selected_for_tensor]
    assert len(selected) == 1
    assert selected[0].lag == 2


def test_nonlinear_driver_can_exceed_linear_baseline_at_k1(lagged_panel: pd.DataFrame) -> None:
    """Lag-1 nonlinear signal should remain visible despite weak linear baseline."""
    target = lagged_panel["target"].to_numpy()
    nonlinear = lagged_panel["nonlinear_lag1"].to_numpy()

    registry = default_registry()
    scorer = registry.get("mi").scorer
    assert isinstance(scorer, DependenceScorer)

    xcorr_profile = compute_cross_correlation_profile(target, nonlinear, max_lag=6)
    ami_curve = compute_exog_raw_curve(
        target,
        nonlinear,
        6,
        scorer,
        min_pairs=30,
        random_state=42,
    )

    assert abs(float(xcorr_profile[1])) < 0.10
    assert float(ami_curve[0]) > 0.02


def test_shipped_cross_pami_semantics_not_overwritten() -> None:
    """cross_pami rows must preserve target_only conditioning semantics."""
    benchmark = generate_lagged_exog_panel(n=1500, seed=42)
    target = benchmark["target"].to_numpy()
    drivers = {"direct_lag2": benchmark["direct_lag2"].to_numpy()}

    result = run_covariant_analysis(
        target,
        drivers,
        max_lag=3,
        methods=["cross_pami"],
        random_state=42,
    )

    assert all(
        row.lagged_exog_conditioning.cross_pami == "target_only" for row in result.summary_table
    )
    disclaimer = str(result.metadata.get("conditioning_scope_disclaimer", ""))
    assert "target_only" in disclaimer
