"""Calendar feature generation walkthrough for ForecastPrepContract.

Demonstrates how to attach deterministic calendar covariates to a
ForecastPrepContract when a pandas DatetimeIndex is available:

    1. Create a daily DatetimeIndex for 300 days starting 2020-01-01.
    2. Generate a synthetic AR(1) series aligned to that index.
    3. Run deterministic triage via ``run_triage``.
    4. Build a ``ForecastPrepContract`` with ``add_calendar_features=True``.
    5. Inspect ``calendar_features`` and ``future_covariates``.

Calendar features always start with ``_calendar__`` and are classified as
``future`` covariates (deterministically known at forecast time).
No forecasting framework is imported.
"""

import pandas as pd

from forecastability import (
    TriageRequest,
    build_forecast_prep_contract,
    generate_ar1,
    run_triage,
)
from forecastability.triage import AnalysisGoal


def main() -> None:
    """Run triage on a date-indexed series and attach calendar features."""
    n = 300
    dates = pd.date_range(start="2020-01-01", periods=n, freq="D")
    series = generate_ar1(n_samples=n, phi=0.8, random_state=42)

    triage_result = run_triage(
        TriageRequest(
            series=series,
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
        add_calendar_features=True,
        datetime_index=dates,
        calendar_locale=None,
    )

    print("=== Calendar features ===")
    print(f"  count              : {len(contract.calendar_features)}")
    print(f"  names              : {contract.calendar_features}")

    print("\n=== Future covariates (should include calendar features) ===")
    print(f"  future_covariates  : {contract.future_covariates}")

    assert len(contract.calendar_features) >= 5, (
        f"Expected at least 5 calendar features, got {len(contract.calendar_features)}"
    )
    assert all(name.startswith("_calendar__") for name in contract.calendar_features), (
        "All calendar feature names must start with '_calendar__'"
    )
    assert set(contract.calendar_features).issubset(set(contract.future_covariates)), (
        "Calendar features must all appear in future_covariates"
    )

    print("\n[OK] All calendar feature assertions passed.")


if __name__ == "__main__":
    main()
