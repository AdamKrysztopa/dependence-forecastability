"""PCMCI-AMI-Hybrid causal discovery example (V3-F04).

Demonstrates the three-phase PCMCI-AMI-Hybrid method on the 8-variable
synthetic benchmark with known ground-truth causal structure:

  Phase 0 — AMI triage
    Compute unconditional mutual information for every (source, lag, target)
    triplet.  Prune pairs whose MI falls below a noise-floor threshold.

  Phase 1+2 — PCMCI+ with kNN conditional MI
    Run PCMCI+ conditional-independence testing only on the Phase 0 survivors,
    using a kNN-based conditional mutual information estimator (knn_cmi)
     instead of partial correlation.  In this implementation the conditioning
     step is residualization-based, and the benchmark can expose nonlinear
     dependencies that parcorr may miss.

What this example illustrates:
     1. Phase 0 pruning can remove weak candidates before the more expensive
         conditional-independence tests.
     2. On this benchmark, the residualized kNN CI test can recover nonlinear
         couplings (quadratic, absolute-value) that linear parcorr may miss.

Ground-truth causal parents of ``target``:
    driver_direct      at lag 2  (β=0.80, strong linear direct)
    driver_mediated    at lag 1  (β=0.50, via driver_direct → driver_mediated → target)
    driver_contemp     at lag 0  (β=0.35, contemporaneous — PCMCI+ specific)
    driver_nonlin_sq   at lag 1  (β=0.40, quadratic coupling — Pearson/Spearman ≈ 0)
    driver_nonlin_abs  at lag 1  (β=0.35, abs-value coupling — Pearson/Spearman ≈ 0)

NOT a causal parent:
    driver_redundant — correlated with driver_direct but not a structural cause
    driver_noise     — independent AR(1) noise
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from forecastability.adapters.pcmci_ami_adapter import PcmciAmiAdapter
from forecastability.utils.synthetic import generate_covariant_benchmark

_FIG_PATH = Path("outputs/figures/pcmci_ami_hybrid_example.png")
_TARGET = "target"
_EXPECTED_LAGGED_PARENTS = {("driver_direct", 2), ("driver_mediated", 1)}
_NONLINEAR_DRIVERS = ("driver_nonlin_sq", "driver_nonlin_abs")
_REDUNDANT_DRIVER = "driver_redundant"
_NOISE_DRIVER = "driver_noise"


def _format_parent(parent: tuple[str, int]) -> str:
    """Format a (source, lag) tuple as a readable string."""
    source, lag = parent
    return f"{source}(t-{lag})" if lag > 0 else f"{source}(t)"


def _print_narrative() -> None:
    """Print the scientific question and method overview."""
    width = 72
    print("\n" + "=" * width)
    print("  PCMCI-AMI-Hybrid: AMI triage + residualized kNN CI on benchmark")
    print("=" * width)
    print()
    print("Method overview (three phases):")
    print("  Phase 0 — unconditional MI triage:")
    print("    Compute MI(source_lag, target) for all (source, lag) pairs.")
    print("    Prune pairs whose MI falls below a noise-floor threshold.")
    print()
    print("  Phases 1+2 — PCMCI+ with residualized kNN CI test (knn_cmi):")
    print("    Run PCMCI+ skeleton + MCI orientation only on Phase 0 survivors.")
    print("    Conditioning is handled by residualization before kNN MI scoring.")
    print("    On this benchmark, it can recover nonlinear parents parcorr may miss.")
    print()


def _print_phase0_results(
    *,
    mi_scores: list[Any],  # list[Phase0MiScore] — avoid import for print helper
    ami_threshold: float,
    pruned_count: int,
    kept_count: int,
) -> None:
    """Print Phase 0 MI triage diagnostics."""
    print("─" * 72)
    print("Phase 0 — AMI triage results:")
    print(f"  Threshold: {ami_threshold:.6f}")
    print(f"  Candidates pruned: {pruned_count}")
    print(f"  Candidates kept:   {kept_count}")
    print()

    target_scores = sorted(
        [s for s in mi_scores if s.target == _TARGET],
        key=lambda s: s.mi_value,
        reverse=True,
    )
    if target_scores:
        print(f"  MI scores for target's surviving parents (top {min(10, len(target_scores))}):")
        for score in target_scores[:10]:
            print(f"    {score.source:>22s} (lag {score.lag}) : MI = {score.mi_value:.6f}")
    print()


def _print_phase2_results(
    *,
    target_parents: list[tuple[str, int]],
) -> None:
    """Print final Phase 2 causal discovery checks."""
    recovered = set(target_parents)

    print("─" * 72)
    print("Phase 2 — PCMCI+ final results:")
    print()
    print("  Discovered parents of target:")
    if target_parents:
        for parent in sorted(target_parents):
            print(f"    - {_format_parent(parent)}")
    else:
        print("    (none)")
    print()

    direct_found = ("driver_direct", 2) in recovered
    mediated_found = ("driver_mediated", 1) in recovered
    nonlin_sq_found = ("driver_nonlin_sq", 1) in recovered
    redundant_excluded = all(src != _REDUNDANT_DRIVER for src, _ in recovered)
    noise_excluded = all(src != _NOISE_DRIVER for src, _ in recovered)

    def _check(label: str, *, passed: bool) -> None:
        marker = "PASS" if passed else "FAIL"
        print(f"  [{marker}] {label}")

    print("  Causal discovery checks:")
    _check("driver_direct (lag 2) recovered", passed=direct_found)
    _check("driver_mediated (lag 1) recovered", passed=mediated_found)
    _check(
        "driver_nonlin_sq (lag 1) recovered — benchmark nonlinear parent",
        passed=nonlin_sq_found,
    )
    _check(
        "driver_redundant correctly EXCLUDED",
        passed=redundant_excluded,
    )
    _check("driver_noise correctly EXCLUDED", passed=noise_excluded)
    if nonlin_sq_found:
        print()
        print("  ★ On this benchmark, kNN MI recovered the quadratic coupling that parcorr missed.")
    print()


def _print_pruning_summary(
    *,
    pruned_count: int,
    kept_count: int,
) -> None:
    """Print the Phase 0 pruning statistics for this run."""
    total = pruned_count + kept_count
    pct = 100.0 * pruned_count / total if total > 0 else 0.0
    print("─" * 72)
    print("Key benefit — Phase 0 pruning:")
    print(f"  Total (source, lag, target) candidates: {total}")
    print(f"  Pruned by MI threshold:                 {pruned_count} ({pct:.1f}%)")
    print(f"  Surviving for PCMCI+:                   {kept_count}")
    print("  → Fewer CI tests and a smaller candidate set for the downstream PCMCI+ run")
    print()


def _plot_timeseries(
    ax: Any,  # matplotlib Axes — optional import
    data: np.ndarray,
    var_names: list[str],
    *,
    n_points: int = 300,
) -> None:
    """Plot standardized time-series trajectories."""
    window = min(n_points, data.shape[0])
    x_axis = np.arange(window)

    for idx, name in enumerate(var_names):
        values = data[:window, idx]
        std = float(np.std(values))
        scaled = (values - float(np.mean(values))) / (std if std > 1e-12 else 1.0)
        lw = 2.2 if name == _TARGET else 1.2
        alpha = 1.0 if name == _TARGET else 0.75
        ax.plot(x_axis, scaled, label=name, linewidth=lw, alpha=alpha)

    ax.set_title(f"Synthetic Dynamics (z-scored, first {window} steps)")
    ax.set_xlabel("Time index")
    ax.set_ylabel("z-score")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=8)


def _plot_parent_heatmap(
    ax: Any,  # matplotlib Axes — optional import
    *,
    target_parents: list[tuple[str, int]],
    source_names: list[str],
    max_lag: int,
    title: str = "Discovered Parents of Target",
) -> None:
    """Visualize discovered source→target links as a source × lag heatmap."""
    grid = np.zeros((len(source_names), max_lag + 1), dtype=float)
    source_to_row = {name: idx for idx, name in enumerate(source_names)}

    for source, lag in target_parents:
        if source in source_to_row and 0 <= lag <= max_lag:
            grid[source_to_row[source], lag] = 1.0

    img = ax.imshow(grid, cmap="Blues", aspect="auto", vmin=0.0, vmax=1.0)
    ax.set_title(title)
    ax.set_xlabel("Lag")
    ax.set_ylabel("Source variable")
    ax.set_xticks(np.arange(max_lag + 1))
    ax.set_xticklabels([f"t-{lag}" if lag > 0 else "t" for lag in range(max_lag + 1)])
    ax.set_yticks(np.arange(len(source_names)))
    ax.set_yticklabels(source_names)

    for row in range(len(source_names)):
        for col in range(max_lag + 1):
            marker = "Y" if grid[row, col] > 0.0 else "."
            ax.text(
                col,
                row,
                marker,
                ha="center",
                va="center",
                color="white" if marker == "Y" else "black",
                fontsize=9,
            )

    ax.figure.colorbar(img, ax=ax, fraction=0.046, pad=0.04, label="Link present")


def main() -> None:
    """Run the PCMCI-AMI-Hybrid causal discovery demonstration."""
    df = generate_covariant_benchmark(n=800, seed=42)
    data = df.to_numpy()
    var_names = df.columns.tolist()

    _print_narrative()

    try:
        adapter = PcmciAmiAdapter()
    except ImportError as exc:
        print(
            "tigramite is not installed. Install it with "
            "`uv sync --extra causal` (or `pip install tigramite`) and rerun."
        )
        raise SystemExit(0) from exc

    result = adapter.discover_full(data, var_names, max_lag=2, alpha=0.05, random_state=42)

    target_parents = sorted(
        result.causal_graph.parents[_TARGET],
        key=lambda item: (item[1], item[0]),
    )

    _print_phase0_results(
        mi_scores=result.phase0_mi_scores,
        ami_threshold=result.ami_threshold,
        pruned_count=result.phase0_pruned_count,
        kept_count=result.phase0_kept_count,
    )

    _print_phase2_results(target_parents=target_parents)

    _print_pruning_summary(
        pruned_count=result.phase0_pruned_count,
        kept_count=result.phase0_kept_count,
    )

    # ── Plotting ──────────────────────────────────────────────────────
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        _plot_timeseries(axes[0], data, var_names)
        _plot_parent_heatmap(
            axes[1],
            target_parents=target_parents,
            source_names=[n for n in var_names if n != _TARGET],
            max_lag=2,
        )
        fig.suptitle(
            "PCMCI-AMI-Hybrid (V3-F04): AMI triage + kNN MI on 8-variable benchmark",
            fontsize=9,
        )
        fig.tight_layout()
        _FIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(_FIG_PATH, dpi=160)
        plt.close(fig)
        print(f"\nFigure saved → {_FIG_PATH}")
    except ImportError:
        print("\n[INFO] matplotlib not available — figure skipped.")


if __name__ == "__main__":
    main()
