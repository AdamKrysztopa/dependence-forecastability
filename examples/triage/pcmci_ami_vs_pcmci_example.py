"""Minimal benchmark-specific comparison for PCMCI+ vs PCMCI-AMI."""

from __future__ import annotations

from forecastability.adapters.pcmci_ami_adapter import PcmciAmiAdapter
from forecastability.adapters.tigramite_adapter import TigramiteAdapter
from forecastability.utils.synthetic import generate_covariant_benchmark

Parent = tuple[str, int]

TARGET = "target"
EXPECTED_NONLINEAR_PARENTS = {
    ("driver_nonlin_abs", 1),
    ("driver_nonlin_sq", 1),
}
N_TIMESTEPS = 1200
MAX_LAG = 2
ALPHA = 0.05
SEED = 43


def _format_parents(parents: set[Parent] | list[Parent]) -> str:
    """Return a stable human-readable parent list."""
    ordered = sorted(parents, key=lambda item: (item[1], item[0]))
    if not ordered:
        return "(none)"
    return ", ".join(f"{source}(t-{lag})" if lag > 0 else f"{source}(t)" for source, lag in ordered)


def main() -> None:
    """Run the linear baseline and hybrid side by side on one benchmark setting."""
    try:
        baseline_adapter = TigramiteAdapter(ci_test="parcorr")
        hybrid_adapter = PcmciAmiAdapter(ci_test="knn_cmi")
    except ImportError as exc:
        print("Install tigramite with `uv sync --extra causal` and rerun.")
        raise SystemExit(0) from exc

    df = generate_covariant_benchmark(n=N_TIMESTEPS, seed=SEED)
    data = df.to_numpy()
    var_names = df.columns.tolist()

    baseline_result = baseline_adapter.discover(
        data,
        var_names,
        max_lag=MAX_LAG,
        alpha=ALPHA,
        random_state=SEED,
    )
    hybrid_result = hybrid_adapter.discover_full(
        data,
        var_names,
        max_lag=MAX_LAG,
        alpha=ALPHA,
        random_state=SEED,
    )

    baseline_parents = set(baseline_result.parents[TARGET])
    hybrid_parents = set(hybrid_result.phase2_final.parents[TARGET])

    baseline_nonlinear = baseline_parents & EXPECTED_NONLINEAR_PARENTS
    hybrid_nonlinear = hybrid_parents & EXPECTED_NONLINEAR_PARENTS
    hybrid_only_nonlinear = hybrid_nonlinear - baseline_nonlinear
    missing_hybrid_nonlinear = EXPECTED_NONLINEAR_PARENTS - hybrid_nonlinear

    total_candidates = hybrid_result.phase0_pruned_count + hybrid_result.phase0_kept_count

    print("Method 1: PCMCI+ with parcorr (linear baseline)")
    print("Method 2: PCMCI-AMI with knn_cmi (Phase 0 pruning + residualized kNN CI test)")
    print()
    print(f"PCMCI+ target parents: {_format_parents(baseline_parents)}")
    print(f"PCMCI-AMI target parents: {_format_parents(hybrid_parents)}")
    print()
    print(f"Expected nonlinear parents: {_format_parents(EXPECTED_NONLINEAR_PARENTS)}")
    print(f"PCMCI+ nonlinear parents found: {_format_parents(baseline_nonlinear)}")
    print(f"PCMCI-AMI nonlinear parents found: {_format_parents(hybrid_nonlinear)}")
    print(f"Recovered only by PCMCI-AMI: {_format_parents(hybrid_only_nonlinear)}")
    print()
    print(
        "PCMCI-AMI Phase 0 pruning: "
        f"pruned {hybrid_result.phase0_pruned_count}, "
        f"kept {hybrid_result.phase0_kept_count}, "
        f"threshold={hybrid_result.ami_threshold:.6f}, "
        f"total={total_candidates}"
    )
    print()

    if baseline_nonlinear:
        verdict = (
            "FAIL: the linear baseline recovered nonlinear parents, so this no longer "
            "isolates the intended benchmark-specific contrast."
        )
    elif not hybrid_only_nonlinear:
        verdict = "FAIL: the hybrid did not recover any expected nonlinear parent in this run."
    else:
        verdict = (
            "PASS: on this benchmark setting, the linear baseline missed the expected "
            "nonlinear parents while PCMCI-AMI recovered at least one of them."
        )
        if missing_hybrid_nonlinear:
            verdict += f" Missing in this run: {_format_parents(missing_hybrid_nonlinear)}."

    verdict += " This is an illustration on one synthetic benchmark, not a general proof."

    print(f"Verdict: {verdict}")


if __name__ == "__main__":
    main()
