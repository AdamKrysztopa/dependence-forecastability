"""Minimal Phase 2 lagged-exogenous triage example."""

from __future__ import annotations

from forecastability import generate_lagged_exog_panel, run_lagged_exogenous_triage


def main() -> None:
    panel = generate_lagged_exog_panel(n=900, seed=42)
    target = panel["target"].to_numpy()
    drivers = {
        "direct_lag2": panel["direct_lag2"].to_numpy(),
        "instant_only": panel["instant_only"].to_numpy(),
        "known_future_calendar": panel["known_future_calendar"].to_numpy(),
    }

    bundle = run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=4,
        n_surrogates=99,
        random_state=42,
        known_future_drivers={"known_future_calendar": True},
    )

    selected = [row for row in bundle.selected_lags if row.selected_for_tensor]
    selected = sorted(selected, key=lambda row: (row.driver, row.lag))

    print("Lagged exogenous triage example")
    print("=" * 36)
    print(f"profile_rows={len(bundle.profile_rows)}")
    print(f"selected_rows={len(selected)}")
    print(f"known_future_drivers={bundle.known_future_drivers}")
    print("selected_lags=" + str([(row.driver, row.lag, row.tensor_role) for row in selected]))


if __name__ == "__main__":
    main()
