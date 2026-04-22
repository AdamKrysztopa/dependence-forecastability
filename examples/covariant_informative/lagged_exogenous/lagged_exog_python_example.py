"""Minimal lagged-exogenous triage example.

This example keeps the public usage surface minimal: build arrays, then call
``run_lagged_exogenous_triage``.
"""

from __future__ import annotations

import numpy as np

from forecastability import run_lagged_exogenous_triage


def _build_demo_series(
    *,
    n: int,
    seed: int,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Build deterministic target/driver arrays for a minimal demo."""
    rng = np.random.default_rng(seed)

    direct_lag2 = rng.normal(0.0, 1.0, size=n)
    instant_only = rng.normal(0.0, 1.0, size=n)
    target = np.zeros(n, dtype=float)

    for t in range(2, n):
        target[t] = (
            0.25 * target[t - 1]
            + 0.85 * direct_lag2[t - 2]
            + 0.70 * instant_only[t]
            + rng.normal(0.0, 0.8)
        )

    drivers = {
        "direct_lag2": direct_lag2,
        "instant_only": instant_only,
    }
    return target, drivers


def main() -> None:
    target, drivers = _build_demo_series(n=700, seed=42)

    bundle = run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=4,
        n_surrogates=99,
        random_state=42,
    )

    selected = [row for row in bundle.selected_lags if row.selected_for_tensor]
    selected = sorted(selected, key=lambda row: (row.driver, row.lag))

    print("Lagged exogenous triage example")
    print("=" * 36)
    print(f"profile_rows={len(bundle.profile_rows)}")
    print(f"selected_rows={len(selected)}")
    print("selected_lags=" + str([(row.driver, row.lag, row.tensor_role) for row in selected]))


if __name__ == "__main__":
    main()
