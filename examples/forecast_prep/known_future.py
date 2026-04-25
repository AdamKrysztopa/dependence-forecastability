"""Known-future driver opt-in walkthrough for ForecastPrepContract.

Demonstrates how to mark a lagged-exogenous driver as known at forecast
time so that it appears in ``future_covariates`` rather than
``past_covariates``:

    1. Generate the synthetic lagged-exogenous benchmark panel.
    2. Run ``run_lagged_exogenous_triage``.
    3. Build a ``ForecastPrepContract`` declaring ``known_future_calendar``
       as a known-future driver via ``known_future_drivers``.
    4. Verify it lands in ``future_covariates`` and not in ``past_covariates``.

No downstream library is imported.
"""

from forecastability import (
    TriageRequest,
    build_forecast_prep_contract,
    generate_lagged_exog_panel,
    run_lagged_exogenous_triage,
    run_triage,
)
from forecastability.triage import AnalysisGoal

_KNOWN_FUTURE_DRIVER = "known_future_calendar"
_DRIVER_ORDER = (
    "direct_lag2",
    "mediated_lag1",
    "redundant",
    "noise",
    "instant_only",
    "nonlinear_lag1",
    _KNOWN_FUTURE_DRIVER,
)


def main() -> None:
    """Show that a known-future driver routes to future_covariates."""
    # n=700 gives stable sparse-selection results; n=300 is too small and produces
    # spurious past-covariate selections for instant_only / noise drivers (Type I error).
    n = 700

    panel = generate_lagged_exog_panel(n=n, seed=42)
    target = panel["target"].to_numpy()
    drivers = {driver: panel[driver].to_numpy() for driver in _DRIVER_ORDER}

    lagged_exog_bundle = run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=6,
        n_surrogates=99,
        random_state=42,
        known_future_drivers={_KNOWN_FUTURE_DRIVER: True},
    )

    triage_result = run_triage(
        TriageRequest(
            series=target,
            goal=AnalysisGoal.univariate,
            max_lag=20,
            n_surrogates=99,
            random_state=42,
        )
    )

    contract = build_forecast_prep_contract(
        triage_result,
        horizon=12,
        target_frequency="D",
        lagged_exog_bundle=lagged_exog_bundle,
        known_future_drivers={_KNOWN_FUTURE_DRIVER: True},
        add_calendar_features=False,
    )

    print("=== Known-future driver routing ===")
    print(f"  past_covariates    : {contract.past_covariates}")
    print(f"  future_covariates  : {contract.future_covariates}")

    assert _KNOWN_FUTURE_DRIVER in contract.future_covariates, (
        f"{_KNOWN_FUTURE_DRIVER!r} should appear in future_covariates"
    )
    assert _KNOWN_FUTURE_DRIVER not in contract.past_covariates, (
        f"{_KNOWN_FUTURE_DRIVER!r} must NOT appear in past_covariates"
    )

    print(f"\n[OK] '{_KNOWN_FUTURE_DRIVER}' is correctly routed to future_covariates.")


if __name__ == "__main__":
    main()
