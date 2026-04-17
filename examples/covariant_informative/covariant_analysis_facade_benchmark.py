"""Benchmark example for the covariant orchestration facade.

Runs ``run_covariant_analysis()`` on the synthetic covariant benchmark and
prints a compact summary showing which drivers stand out across the bundled
methods. Optional tigramite-backed methods are included automatically when
available and skipped gracefully otherwise.
"""

from __future__ import annotations

from forecastability import run_covariant_analysis
from forecastability.utils.synthetic import generate_covariant_benchmark
from forecastability.utils.types import CovariantAnalysisBundle

_PAIRWISE_METHOD_FIELDS: tuple[tuple[str, str], ...] = (
    ("cross_ami", "CrossAMI"),
    ("cross_pami", "pCrossAMI"),
    ("transfer_entropy", "TE"),
    ("gcmi", "GCMI"),
)


def _max_score_for_driver(
    bundle: CovariantAnalysisBundle,
    *,
    driver_name: str,
    field_name: str,
) -> float | None:
    values = [
        getattr(row, field_name)
        for row in bundle.summary_table
        if row.driver == driver_name and getattr(row, field_name) is not None
    ]
    if not values:
        return None
    return max(float(value) for value in values)


def _print_pairwise_summary(bundle: CovariantAnalysisBundle) -> None:
    print("\nPairwise triage summary (max score by driver across lags 1..3)")
    print("=" * 72)
    print(f"{'Method':<14}{'Direct':>12}{'Mediated':>12}{'Noise':>12}")
    print("-" * 50)
    for field_name, label in _PAIRWISE_METHOD_FIELDS:
        direct = _max_score_for_driver(bundle, driver_name="driver_direct", field_name=field_name)
        mediated = _max_score_for_driver(
            bundle,
            driver_name="driver_mediated",
            field_name=field_name,
        )
        noise = _max_score_for_driver(bundle, driver_name="driver_noise", field_name=field_name)
        if direct is None and mediated is None and noise is None:
            continue
        print(f"{label:<14}{direct or 0.0:>12.4f}{mediated or 0.0:>12.4f}{noise or 0.0:>12.4f}")


def _print_causal_summary(bundle: CovariantAnalysisBundle) -> None:
    if bundle.pcmci_graph is not None:
        parents = sorted(bundle.pcmci_graph.parents.get(bundle.target_name, []))
        print("\nPCMCI+ target parents")
        print("=" * 72)
        print(parents if parents else "(none)")

    if bundle.pcmci_ami_result is not None:
        parents = sorted(bundle.pcmci_ami_result.causal_graph.parents.get(bundle.target_name, []))
        print("\nPCMCI-AMI target parents")
        print("=" * 72)
        print(parents if parents else "(none)")
        print(
            "Phase 0 kept/pruned:",
            bundle.pcmci_ami_result.phase0_kept_count,
            "/",
            bundle.pcmci_ami_result.phase0_pruned_count,
        )


def main() -> None:
    df = generate_covariant_benchmark(n=900, seed=42)
    target = df["target"].to_numpy()
    drivers = {name: df[name].to_numpy() for name in df.columns if name != "target"}

    bundle = run_covariant_analysis(
        target,
        drivers,
        target_name="target",
        max_lag=3,
        random_state=42,
    )

    print("Covariant facade benchmark")
    print("=" * 72)
    print(f"Requested methods: {bundle.metadata.get('requested_methods', '')}")
    print(f"Active methods:    {bundle.metadata.get('active_methods', '')}")
    skipped = bundle.metadata.get("skipped_optional_methods")
    if skipped:
        print(f"Skipped optional methods: {skipped}")
    disclaimer = bundle.metadata.get("conditioning_scope_disclaimer")
    if disclaimer:
        print("\nConditioning disclaimer:")
        print(disclaimer)
        print(f"Forward link: {bundle.metadata.get('conditioning_scope_forward_link', '')}")

    _print_pairwise_summary(bundle)
    _print_causal_summary(bundle)


if __name__ == "__main__":
    main()
