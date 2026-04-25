"""Minimal deterministic univariate triage → ForecastPrepContract example.

Demonstrates the simplest possible path from raw series to a
ForecastPrepContract using only the ``forecastability`` public API:

    1. Generate a synthetic AR(1) series.
    2. Run deterministic triage via ``run_triage``.
    3. Build a ``ForecastPrepContract`` via ``build_forecast_prep_contract``.
    4. Print key contract fields.

No downstream library is imported. The contract is the hand-off artifact
that downstream libraries (darts, mlforecast, etc.) consume per their own
framework-specific adapters.
"""

from forecastability import (
    TriageRequest,
    build_forecast_prep_contract,
    generate_ar1,
    run_triage,
)
from forecastability.triage import AnalysisGoal


def main() -> None:
    """Run minimal univariate triage and build a ForecastPrepContract."""
    series = generate_ar1(n_samples=300, phi=0.8, random_state=42)

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
        add_calendar_features=False,
    )

    print("=== ForecastPrepContract (minimal univariate) ===")
    print(f"  blocked             : {contract.blocked}")
    print(f"  readiness_status    : {contract.readiness_status}")
    print(f"  confidence_label    : {contract.confidence_label}")
    print(f"  recommended_target_lags : {list(contract.recommended_target_lags)}")
    print(f"  recommended_families    : {list(contract.recommended_families)}")
    print(f"  source_goal         : {contract.source_goal}")
    print(f"  contract_version    : {contract.contract_version}")


if __name__ == "__main__":
    main()
