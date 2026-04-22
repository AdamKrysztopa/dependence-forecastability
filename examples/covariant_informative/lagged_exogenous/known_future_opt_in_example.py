"""Known-future lag-0 opt-in example for lagged-exogenous triage."""

from __future__ import annotations

from forecastability import (
    LaggedExogBundle,
    generate_known_future_calendar_pair,
    run_lagged_exogenous_triage,
)


def _selected_lag_zero_count(*, bundle_target: LaggedExogBundle) -> int:
    return sum(
        1
        for row in bundle_target.selected_lags
        if row.selected_for_tensor and row.driver == "known_future_calendar" and row.lag == 0
    )


def main() -> None:
    panel = generate_known_future_calendar_pair(n=900, seed=42)
    target = panel["target"].to_numpy()
    drivers = {"known_future_calendar": panel["known_future_calendar"].to_numpy()}

    default_bundle = run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=4,
        n_surrogates=99,
        random_state=42,
    )

    opt_in_bundle = run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=4,
        n_surrogates=99,
        random_state=42,
        known_future_drivers={"known_future_calendar": True},
    )

    default_lag_zero = _selected_lag_zero_count(bundle_target=default_bundle)
    opt_in_lag_zero = _selected_lag_zero_count(bundle_target=opt_in_bundle)

    print("Known-future lag=0 opt-in example")
    print("=" * 40)
    print(f"default_known_future_drivers={default_bundle.known_future_drivers}")
    print(f"default_selected_lag0_count={default_lag_zero}")
    print(f"opt_in_known_future_drivers={opt_in_bundle.known_future_drivers}")
    print(f"opt_in_selected_lag0_count={opt_in_lag_zero}")
    print("selected_lag0_requires_explicit_known_future_opt_in=True")


if __name__ == "__main__":
    main()
