"""PCMCI+ causal discovery example (V3-F03).

Demonstrates two distinct failure modes of classical correlation analysis,
using an 8-variable synthetic system with known ground-truth causal structure:

  Story A — Redundant-variable exclusion
    A variable that is linearly correlated with target (via a shared cause)
    but has NO direct structural link should be excluded.
    parcorr/PCMCI+ achieves this via conditional independence testing.

  Story B — Nonlinear blind-spot
    Two variables have genuine structural (causal) links to target via
    nonlinear coupling (quadratic and absolute-value).  Their Pearson and
    Spearman correlations with target are near zero by construction.
    A linear CI test (parcorr) therefore fails to detect them.
    Information-theoretic methods (MI, TE, GCMI) would detect these.

Ground-truth causal parents of `target`:
    driver_direct     at lag 2  (β=0.80, strong linear direct)
    driver_mediated   at lag 1  (β=0.50, via driver_direct → driver_mediated → target)
    driver_contemp    at lag 0  (β=0.35, contemporaneous — PCMCI+ specific)
    driver_nonlin_sq  at lag 1  (β=0.40, quadratic coupling — Pearson/Spearman ≈ 0)
    driver_nonlin_abs at lag 1  (β=0.35, abs-value coupling — Pearson/Spearman ≈ 0)

Deliberately NOT a parent (or not recoverable by linear CI):
    driver_redundant — correlated with driver_direct but not a structural cause
    driver_noise     — independent AR(1) noise

Reference:
    Runge, J. (2020). Discovering contemporaneous and lagged causal
    relations in autocorrelated nonlinear time series datasets.
    Proceedings of the 36th Conference on UAI, PMLR 124.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from forecastability.adapters.tigramite_adapter import TigramiteAdapter
from forecastability.utils.synthetic import generate_covariant_benchmark

sys.path.insert(0, str(Path(__file__).parent))
from _benchmark_ground_truth import (  # noqa: E402
    print_ground_truth_table,
    summarize_recovery,
)

_FIG_PATH = Path(
    "outputs/figures/examples/covariant_informative/causal_discovery/pcmci_plus_benchmark.png"
)
_EXPECTED_LAGGED_PARENTS = {("driver_direct", 2), ("driver_mediated", 1)}
_NONLINEAR_DRIVERS = ("driver_nonlin_sq", "driver_nonlin_abs")
_REDUNDANT_DRIVER = "driver_redundant"
_NOISE_DRIVER = "driver_noise"
_TARGET = "target"


def _format_parent(parent: tuple[str, int]) -> str:
    """Format a (source, lag) tuple as a readable string."""
    source, lag = parent
    return f"{source}(t-{lag})" if lag > 0 else f"{source}(t)"


def _print_narrative() -> None:
    """Print the scientific question and ground-truth summary."""
    width = 72
    print("\n" + "=" * width)
    print("  PCMCI+ causal discovery: linear CI test on 8-variable benchmark")
    print("=" * width)
    print()
    print("Story A — redundant-variable exclusion:")
    print("  driver_redundant is linearly correlated with target (via driver_direct)")
    print("  but has no direct structural link.  PCMCI+ (parcorr) should exclude it.")
    print()
    print("Story B — nonlinear blind-spot:")
    print("  driver_nonlin_sq  couples to target via x² (quadratic).")
    print("  driver_nonlin_abs couples to target via |x| (abs-value).")
    print("  Both have Pearson/Spearman ≈ 0 with target by construction.")
    print("  A linear CI test (parcorr) typically fails to detect these links on this benchmark.")
    print(
        "  Information-theoretic methods (MI/TE/GCMI) can detect some of these "
        "— see Script 2 / Script 3 "
        "(one of the two nonlinear parents recovered at the current settings)."
    )
    print()


def _print_pearson_blindspot(df: Any) -> None:  # noqa: F821
    """Print Pearson correlations for all drivers vs target to show blind-spot."""

    target = df[_TARGET]
    print("Pearson r (driver vs target)  — linear correlation view:")
    for col in df.columns:
        if col == _TARGET:
            continue
        r = float(df[col].corr(target, method="pearson"))
        label = "(nonlinear driver — Pearson blind!)" if col in _NONLINEAR_DRIVERS else ""
        print(f"  {col:>22s} : r = {r:+.4f}  {label}")
    print()


def _print_comparison(
    *,
    df: Any,  # noqa: F821
    target_parents: list[tuple[str, int]],
    var_names: list[str],
    val_matrix: list[list[float]] | None,
) -> None:
    """Print structured comparison of expected vs discovered parents."""
    recovered = set(target_parents)

    _print_pearson_blindspot(df)

    print("─" * 60)
    print("Story A — PCMCI+ (parcorr, α=0.01) results:")
    print()
    print("  Expected linear structural parents:")
    for parent in sorted(_EXPECTED_LAGGED_PARENTS):
        print(f"    - {_format_parent(parent)}")

    print("\n  Discovered parents of target:")
    if target_parents:
        for parent in sorted(target_parents):
            print(f"    - {_format_parent(parent)}")
    else:
        print("    (none)")

    print()

    direct_found = ("driver_direct", 2) in recovered
    mediated_found = ("driver_mediated", 1) in recovered
    redundant_excluded = all(src != _REDUNDANT_DRIVER for src, _ in recovered)
    noise_excluded = all(src != _NOISE_DRIVER for src, _ in recovered)

    def _check(label: str, passed: bool) -> None:
        marker = "PASS" if passed else "FAIL"
        print(f"  [{marker}] {label}")

    print("  Causal discovery checks (Story A):")
    _check("driver_direct (lag 2) recovered", direct_found)
    _check("driver_mediated (lag 1) recovered", mediated_found)
    _check(
        "driver_redundant correctly EXCLUDED (conditional testing advantage)",
        redundant_excluded,
    )
    _check("driver_noise correctly EXCLUDED", noise_excluded)

    print()
    print("─" * 60)
    print("Story B — parcorr blind-spot (expected behaviour for linear CI test):")
    sq_found = any(src == "driver_nonlin_sq" for src, _ in recovered)
    abs_found = any(src == "driver_nonlin_abs" for src, _ in recovered)
    _check("driver_nonlin_sq NOT found by parcorr  (blind to quadratic coupling)", not sq_found)
    _check("driver_nonlin_abs NOT found by parcorr (blind to abs-value coupling)", not abs_found)
    if not sq_found and not abs_found:
        print(
            "  → These two structural parents require information-theoretic CI tests"
            " (GCMI, CMI) to be discovered."
        )

    if val_matrix is not None and _TARGET in var_names:
        target_idx = var_names.index(_TARGET)
        print("\nMax directed test-statistic summary (source → target):")
        ranked = sorted(
            (
                (var_names[row], float(val_matrix[row][target_idx]))
                for row in range(len(var_names))
                if var_names[row] != _TARGET
            ),
            key=lambda item: abs(item[1]),
            reverse=True,
        )
        for source, score in ranked:
            tag = " ← nonlinear driver" if source in _NONLINEAR_DRIVERS else ""
            print(f"  {source:>22s} → target : {score: .4f}{tag}")


def _plot_timeseries(
    ax: Any,  # matplotlib Axes — optional import, no stubs at parse time
    data: np.ndarray,
    var_names: list[str],
    n_points: int = 300,
) -> None:
    """Plot standardized time-series trajectories for the first *n_points* steps."""
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
    ax: Any,  # matplotlib Axes — optional import, no stubs at parse time
    *,
    target_parents: list[tuple[str, int]],
    source_names: list[str],
    max_lag: int,
) -> None:
    """Visualize discovered source→target links as a source × lag heatmap."""
    grid = np.zeros((len(source_names), max_lag + 1), dtype=float)
    source_to_row = {name: idx for idx, name in enumerate(source_names)}

    for source, lag in target_parents:
        if source in source_to_row and 0 <= lag <= max_lag:
            grid[source_to_row[source], lag] = 1.0

    img = ax.imshow(grid, cmap="Blues", aspect="auto", vmin=0.0, vmax=1.0)
    ax.set_title("Discovered Parents of Target")
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
    """Run the PCMCI+ causal discovery demonstration."""
    df = generate_covariant_benchmark(n=1500, seed=42)
    data = df.to_numpy()
    var_names = df.columns.tolist()

    _print_narrative()
    print_ground_truth_table()

    try:
        adapter = TigramiteAdapter(ci_test="parcorr")
    except ImportError as exc:
        print(
            "tigramite is not installed. Install it with "
            "`uv sync --extra causal` (or `pip install tigramite`) and rerun."
        )
        raise SystemExit(0) from exc

    t0 = time.perf_counter()
    result = adapter.discover(data, var_names, max_lag=3, alpha=0.01, random_state=42)
    elapsed = time.perf_counter() - t0
    print(f"Discover wall-clock: {elapsed:.2f}s")
    target_parents = sorted(result.parents[_TARGET], key=lambda item: (item[1], item[0]))
    print()
    print(summarize_recovery(method_label="PCMCI+ (parcorr)", recovered_parents=target_parents))
    print()

    _print_comparison(
        df=df,
        target_parents=target_parents,
        var_names=var_names,
        val_matrix=result.val_matrix,
    )

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        _plot_timeseries(axes[0], data, var_names)
        _plot_parent_heatmap(
            axes[1],
            target_parents=target_parents,
            source_names=[name for name in var_names if name != _TARGET],
            max_lag=3,
        )
        fig.suptitle(
            "PCMCI+ (parcorr): 8-Variable Benchmark\n"
            "Story A: excludes driver_redundant  |  Story B: blind to nonlinear drivers",
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
