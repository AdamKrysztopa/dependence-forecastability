"""Phase 3 lagged-exogenous semantics example.

Shows deterministic role invariants and sparse selected-lag behavior for the
Phase 3 lagged-exogenous triage surfaces.
"""

from __future__ import annotations

from forecastability import (
    generate_lagged_exog_panel,
    run_covariant_analysis,
    run_lagged_exogenous_triage,
)


def main() -> None:
    """Run the Phase 3 lagged-exog semantics demo."""
    panel = generate_lagged_exog_panel(n=1500, seed=42)
    target = panel["target"].to_numpy()
    drivers = {
        "direct_lag2": panel["direct_lag2"].to_numpy(),
        "mediated_lag1": panel["mediated_lag1"].to_numpy(),
        "redundant": panel["redundant"].to_numpy(),
        "instant_only": panel["instant_only"].to_numpy(),
    }

    lagged_bundle = run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=6,
        n_surrogates=99,
        random_state=42,
    )

    selected = sorted(
        (row for row in lagged_bundle.selected_lags if row.selected_for_tensor),
        key=lambda row: (row.driver, row.lag),
    )
    selected_lag_map: dict[str, list[int]] = {}
    for row in selected:
        selected_lag_map.setdefault(row.driver, []).append(row.lag)

    lag0_roles = {
        row.driver: (row.lag_role, row.tensor_role)
        for row in lagged_bundle.profile_rows
        if row.lag == 0
    }

    covariant_bundle = run_covariant_analysis(
        target,
        {"direct_lag2": drivers["direct_lag2"]},
        max_lag=3,
        methods=["cross_pami"],
        random_state=42,
    )
    cross_pami_tags = [
        row.lagged_exog_conditioning.cross_pami
        for row in sorted(covariant_bundle.summary_table, key=lambda row: row.lag)
    ]

    print("Phase 3 lagged exogenous semantics example")
    print("=" * 48)
    print(f"selected_lag_map={selected_lag_map}")
    print(f"lag0_role_invariants={lag0_roles}")
    print(f"cross_pami_conditioning_tags={cross_pami_tags}")


if __name__ == "__main__":
    main()
