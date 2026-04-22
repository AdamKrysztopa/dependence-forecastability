"""Run a tiny triage-first hand-off demo on a synthetic series."""

from forecastability import TriageRequest, generate_ar1, run_triage


def main() -> None:
    """Print a compact summary that branches on blocked vs hand-off ready."""
    series = generate_ar1(n_samples=300, phi=0.8, random_state=42)
    result = run_triage(
        TriageRequest(
            series=series,
            max_lag=24,
            n_surrogates=99,
            random_state=42,
        )
    )

    print(f"blocked={result.blocked}")
    print(f"readiness_status={result.readiness.status.value}")

    if result.blocked:
        print("handoff=do data/readiness work first")
        return

    interpretation = result.interpretation
    primary_lags = [] if interpretation is None else list(interpretation.primary_lags)
    forecastability_class = None if interpretation is None else interpretation.forecastability_class
    directness_class = None if interpretation is None else interpretation.directness_class
    modeling_regime = None if interpretation is None else interpretation.modeling_regime

    print(f"forecastability_class={forecastability_class}")
    print(f"primary_lags={primary_lags}")
    print(
        f"structure_signals=directness_class:{directness_class},modeling_regime:{modeling_regime}"
    )
    print(
        "handoff=carry forecastability_class, primary_lags, and structure_signals "
        "into downstream framework setup"
    )


if __name__ == "__main__":
    main()
