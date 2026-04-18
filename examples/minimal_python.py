"""Minimal deterministic univariate triage example."""

from forecastability import TriageRequest, generate_ar1, run_triage
from forecastability.triage import AnalysisGoal


def main() -> None:
    """Run minimal univariate triage and print a compact summary."""
    series = generate_ar1(n_samples=300, phi=0.8, random_state=42)
    result = run_triage(
        TriageRequest(
            series=series,
            goal=AnalysisGoal.univariate,
            max_lag=20,
            n_surrogates=99,
            random_state=42,
        )
    )

    summary = {
        "blocked": result.blocked,
        "readiness_status": result.readiness.status.value,
        "forecastability_class": (
            None if result.interpretation is None else result.interpretation.forecastability_class
        ),
        "primary_lags": (
            []
            if result.interpretation is None
            else list(result.interpretation.primary_lags)
        ),
    }
    print(summary)


if __name__ == "__main__":
    main()
