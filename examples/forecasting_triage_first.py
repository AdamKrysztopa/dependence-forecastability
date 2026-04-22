"""Tiny triage-first forecasting example using the stable public facade."""

from forecastability import TriageRequest, generate_ar1, run_triage


def main() -> None:
    """Run deterministic triage before any downstream forecasting hand-off."""
    series = generate_ar1(n_samples=300, phi=0.8, random_state=42)
    result = run_triage(
        TriageRequest(
            series=series,
            max_lag=24,
            n_surrogates=99,
            random_state=42,
        )
    )

    if result.blocked:
        print(
            {
                "blocked": True,
                "readiness_status": result.readiness.status.value,
                "next_step": "Do data/readiness work before model search.",
            }
        )
        return

    interpretation = result.interpretation
    primary_lags = [] if interpretation is None else list(interpretation.primary_lags)
    forecastability_class = None if interpretation is None else interpretation.forecastability_class
    directness_class = None if interpretation is None else interpretation.directness_class
    modeling_regime = None if interpretation is None else interpretation.modeling_regime

    print(
        {
            "blocked": False,
            "readiness_status": result.readiness.status.value,
            "forecastability_class": forecastability_class,
            "primary_lags": primary_lags,
            "structure_signals": {
                "directness_class": directness_class,
                "modeling_regime": modeling_regime,
            },
            "next_step": (
                "Carry forecastability_class, primary_lags, and structure_signals "
                "into downstream framework setup."
            ),
        }
    )


if __name__ == "__main__":
    main()
