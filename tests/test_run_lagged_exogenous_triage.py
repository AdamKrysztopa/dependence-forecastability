"""Tests for the lagged-exogenous triage use case."""

from __future__ import annotations

import pandas as pd
import pytest

from forecastability.use_cases.run_lagged_exogenous_triage import run_lagged_exogenous_triage
from forecastability.utils.synthetic import generate_lagged_exog_panel


@pytest.fixture
def lagged_panel() -> pd.DataFrame:
    """Return deterministic lagged-exogenous benchmark data."""
    return generate_lagged_exog_panel(n=700, seed=42)


def test_zero_lag_never_selected_for_tensor_by_default(lagged_panel: pd.DataFrame) -> None:
    """Lag-0 should remain diagnostic-only without known-future opt-in."""
    target = lagged_panel["target"].to_numpy()
    drivers = {
        "direct_lag2": lagged_panel["direct_lag2"].to_numpy(),
        "instant_only": lagged_panel["instant_only"].to_numpy(),
    }

    bundle = run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=3,
        n_surrogates=99,
        include_cross_ami=False,
        include_cross_correlation=True,
        random_state=42,
    )

    lag0_rows = [row for row in bundle.profile_rows if row.lag == 0]
    assert len(lag0_rows) == len(drivers)
    assert all(row.lag_role == "instant" for row in lag0_rows)
    assert all(row.tensor_role == "diagnostic" for row in lag0_rows)

    assert all(row.lag >= 1 for row in bundle.selected_lags)
    assert all(row.lag_role == "predictive" for row in bundle.profile_rows if row.lag >= 1)


def test_known_future_opt_in_flips_zero_lag_to_selected(lagged_panel: pd.DataFrame) -> None:
    """Known-future opt-in should emit a lag-0 selected row with known_future role."""
    target = lagged_panel["target"].to_numpy()
    drivers = {
        "known_future_calendar": lagged_panel["known_future_calendar"].to_numpy(),
        "instant_only": lagged_panel["instant_only"].to_numpy(),
    }

    bundle = run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=3,
        n_surrogates=99,
        known_future_drivers={"known_future_calendar": True},
        include_cross_ami=False,
        include_cross_correlation=True,
        random_state=42,
    )

    assert bundle.known_future_drivers == ["known_future_calendar"]
    assert "known_future_contract_caution" in bundle.metadata

    known_profile_lag0 = [
        row for row in bundle.profile_rows if row.driver == "known_future_calendar" and row.lag == 0
    ]
    assert len(known_profile_lag0) == 1
    assert known_profile_lag0[0].tensor_role == "known_future"

    known_selected_lag0 = [
        row
        for row in bundle.selected_lags
        if row.driver == "known_future_calendar" and row.lag == 0
    ]
    assert len(known_selected_lag0) == 1
    assert known_selected_lag0[0].selected_for_tensor is True
    assert known_selected_lag0[0].tensor_role == "known_future"

    instant_selected_lag0 = [
        row for row in bundle.selected_lags if row.driver == "instant_only" and row.lag == 0
    ]
    assert instant_selected_lag0 == []


def test_rejects_mismatched_driver_length(lagged_panel: pd.DataFrame) -> None:
    """Mismatched target and driver lengths should raise ValueError."""
    target = lagged_panel["target"].to_numpy()
    drivers = {
        "bad_driver": lagged_panel["direct_lag2"].to_numpy()[:-1],
    }

    with pytest.raises(ValueError, match="must exactly match target length"):
        run_lagged_exogenous_triage(
            target,
            drivers,
            target_name="target",
            max_lag=3,
            n_surrogates=99,
        )


def test_rejects_low_surrogate_count(lagged_panel: pd.DataFrame) -> None:
    """Use-case contract requires at least 99 surrogates."""
    target = lagged_panel["target"].to_numpy()
    drivers = {"direct_lag2": lagged_panel["direct_lag2"].to_numpy()}

    with pytest.raises(ValueError, match="n_surrogates must be >= 99"):
        run_lagged_exogenous_triage(
            target,
            drivers,
            target_name="target",
            max_lag=3,
            n_surrogates=98,
        )


def test_default_path_computes_cross_ami_significance(lagged_panel: pd.DataFrame) -> None:
    """Default path should compute cross-AMI profile and surrogate significance tags."""
    target = lagged_panel["target"].to_numpy()
    drivers = {"direct_lag2": lagged_panel["direct_lag2"].to_numpy()}

    bundle = run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=2,
        n_surrogates=99,
        random_state=42,
    )

    assert len(bundle.profile_rows) == 3
    assert all(row.cross_ami is not None for row in bundle.profile_rows)
    assert all(row.significance in ("above_band", "below_band") for row in bundle.profile_rows)
    assert all(row.significance_source == "phase_surrogate_xami" for row in bundle.profile_rows)
