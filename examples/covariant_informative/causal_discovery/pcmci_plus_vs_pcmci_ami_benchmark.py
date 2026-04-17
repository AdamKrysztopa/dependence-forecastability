"""Minimal benchmark-specific comparison for PCMCI+ vs PCMCI-AMI.

Includes a causality-contrast scatter plot that separates linear from
nonlinear drivers visually, with Pearson r and per-method detection status.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from forecastability.adapters.pcmci_ami_adapter import PcmciAmiAdapter
from forecastability.adapters.tigramite_adapter import TigramiteAdapter
from forecastability.utils.synthetic import generate_covariant_benchmark

if TYPE_CHECKING:
    from matplotlib.figure import Figure

_FIG_PATH = Path(
    "outputs/figures/examples/covariant_informative/causal_discovery/"
    "pcmci_plus_vs_pcmci_ami_benchmark_causality_contrast.png"
)

Parent = tuple[str, int]

TARGET = "target"

# ── Causality-contrast plot config ────────────────────────────────────────────
# (driver_column, lag, category, title)
_SCATTER_PANELS: list[tuple[str, int, str, str]] = [
    ("driver_direct", 2, "linear", "driver_direct(t-2)"),
    ("driver_mediated", 1, "linear", "driver_mediated(t-1)"),
    ("driver_nonlin_sq", 1, "nonlinear", "driver_nonlin_sq(t-1)\n[quadratic coupling]"),
    ("driver_nonlin_abs", 1, "nonlinear", "driver_nonlin_abs(t-1)\n[abs-value coupling]"),
]
_ALPHA_DOT = 0.25
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


def _plot_causality_contrast(
    df: pd.DataFrame,
    baseline_parents: set[Parent],
    hybrid_parents: set[Parent],
) -> Figure:
    """Create a 2×2 scatter grid contrasting linear vs nonlinear causal links.

    Each panel shows driver(t-lag) vs target(t) with:
    - Pearson r annotation (near-zero for nonlinear drivers)
    - OLS trend line for linear panels; a binned-mean curve for nonlinear panels
    - Detection badges for PCMCI+ (parcorr) and PCMCI-AMI
    """
    import matplotlib.gridspec as gridspec
    import matplotlib.pyplot as _plt

    target = df[TARGET].to_numpy()

    fig = _plt.figure(figsize=(13, 10))
    gs = gridspec.GridSpec(
        3,
        2,
        height_ratios=[0.06, 1, 1],
        hspace=0.55,
        wspace=0.38,
    )

    # ── Row headers ───────────────────────────────────────────────────
    ax_hdr_lin = fig.add_subplot(gs[0, 0])
    ax_hdr_lin.axis("off")
    ax_hdr_lin.text(
        0.5,
        0.7,
        "Linear causality",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#1a5276",
        transform=ax_hdr_lin.transAxes,
    )
    ax_hdr_lin.text(
        0.5,
        0.1,
        "V3-F03: PCMCI+ / parcorr",
        ha="center",
        va="center",
        fontsize=8,
        color="#1a5276",
        style="italic",
        transform=ax_hdr_lin.transAxes,
    )
    ax_hdr_nl = fig.add_subplot(gs[0, 1])
    ax_hdr_nl.axis("off")
    ax_hdr_nl.text(
        0.5,
        0.7,
        "Nonlinear drivers (V3-F04 advantage)",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#922b21",
        transform=ax_hdr_nl.transAxes,
    )
    ax_hdr_nl.text(
        0.5,
        0.1,
        "V3-F04: PCMCI-AMI / kNN CMI  (also recovers linear parents)",
        ha="center",
        va="center",
        fontsize=8,
        color="#922b21",
        style="italic",
        transform=ax_hdr_nl.transAxes,
    )

    panel_axes = [
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[2, 0]),
        fig.add_subplot(gs[1, 1]),
        fig.add_subplot(gs[2, 1]),
    ]

    for ax, (col, lag, category, title) in zip(
        panel_axes,
        _SCATTER_PANELS,
        strict=True,
    ):
        driver = df[col].to_numpy()
        x = driver[: len(driver) - lag]
        y = target[lag:]

        pearson_r = float(np.corrcoef(x, y)[0, 1])

        color = "#1a5276" if category == "linear" else "#922b21"
        ax.scatter(x, y, alpha=_ALPHA_DOT, s=4, color=color, linewidths=0, rasterized=True)

        x_sorted = np.linspace(x.min(), x.max(), 200)

        if category == "linear":
            # OLS trend line
            slope, intercept = np.polyfit(x, y, 1)
            ax.plot(x_sorted, slope * x_sorted + intercept, color=color, lw=1.8, label="OLS fit")
        else:
            # Binned-mean curve to reveal the nonlinear shape
            n_bins = 30
            bins = np.percentile(x, np.linspace(0, 100, n_bins + 1))
            bin_centers, bin_means = [], []
            for i in range(n_bins):
                # Use <= for the last bin so the maximum value is included.
                upper_op = (x <= bins[i + 1]) if i == n_bins - 1 else (x < bins[i + 1])
                mask = (x >= bins[i]) & upper_op
                if mask.sum() > 5:
                    bin_centers.append(0.5 * (bins[i] + bins[i + 1]))
                    bin_means.append(float(y[mask].mean()))
            ax.plot(bin_centers, bin_means, color=color, lw=2.0, label="binned mean")

        # ── Pearson r annotation ──────────────────────────────────────
        n_obs = len(x)
        r_se = float(np.sqrt((1.0 - pearson_r**2) / max(n_obs - 2, 1)))
        if category == "nonlinear":
            # Near-zero r is by construction (odd/even moment argument);
            # show ±SE to clarify the finite-sample scatter around 0.
            r_label = f"Pearson r = {pearson_r:+.3f} \u00b1{r_se:.3f}  (n={n_obs})"
        else:
            r_label = f"Pearson r = {pearson_r:+.3f}"
        ax.annotate(
            r_label,
            xy=(0.04, 0.93),
            xycoords="axes fraction",
            fontsize=8,
            color="black",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", alpha=0.8, ec="grey", lw=0.5),
        )

        # ── Detection badges ──────────────────────────────────────────
        pcmci_hit = (col, lag) in baseline_parents
        ami_hit = (col, lag) in hybrid_parents
        # Two separate annotations so each line can carry its own outcome colour.
        ax.annotate(
            f"V3-F03 PCMCI+:    {'✓ found' if pcmci_hit else '✗ missed'}",
            xy=(0.96, 0.11),
            xycoords="axes fraction",
            fontsize=7.5,
            ha="right",
            va="bottom",
            family="monospace",
            color="#1e8449" if pcmci_hit else "#922b21",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", alpha=0.85, ec="grey", lw=0.5),
        )
        ax.annotate(
            f"V3-F04 PCMCI-AMI: {'✓ found' if ami_hit else '✗ missed'}",
            xy=(0.96, 0.02),
            xycoords="axes fraction",
            fontsize=7.5,
            ha="right",
            va="bottom",
            family="monospace",
            color="#1e8449" if ami_hit else "#922b21",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", alpha=0.85, ec="grey", lw=0.5),
        )

        ax.set_xlabel(f"{col}  (t-{lag})", fontsize=8)
        ax.set_ylabel("target  (t)", fontsize=8)
        ax.set_title(title, fontsize=9, pad=4)
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=7, loc="upper right", handlelength=1.4)

    fig.suptitle(
        "Causality detection contrast — V3-F03 (PCMCI+/parcorr) vs V3-F04 (PCMCI-AMI/kNN CMI)\n"
        "Linear drivers are visible to both methods · Nonlinear drivers require "
        "kNN CMI (Pearson r ≈ 0)",
        fontsize=10,
        y=0.99,
    )
    return fig


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
    # Identify self-lag parents (target appearing as its own parent);
    # AR(1) target has only lag-1 structural self-coupling — higher lags are FPs.
    structural_self_lags: set[Parent] = {(TARGET, 1)}
    baseline_self_fp = {
        parent
        for parent in baseline_parents
        if parent[0] == TARGET and parent not in structural_self_lags
    }
    hybrid_self_fp = {
        parent
        for parent in hybrid_parents
        if parent[0] == TARGET and parent not in structural_self_lags
    }

    print(f"PCMCI+ target parents: {_format_parents(baseline_parents)}")
    if baseline_self_fp:
        print(
            f"  [NOTE] Likely false positive(s) — non-structural self-lag(s): "
            f"{_format_parents(baseline_self_fp)}  (AR(1) target has no lag>1 structural self-link)"
        )
    print(f"PCMCI-AMI target parents: {_format_parents(hybrid_parents)}")
    if hybrid_self_fp:
        print(
            f"  [NOTE] Likely false positive(s) — non-structural self-lag(s): "
            f"{_format_parents(hybrid_self_fp)}"
        )
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

    # ── Causality-contrast figure ──────────────────────────────────────────────
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig = _plot_causality_contrast(df, baseline_parents, hybrid_parents)
        _FIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(_FIG_PATH, dpi=160)
        plt.close(fig)
        print(f"\nFigure saved → {_FIG_PATH}")
    except ImportError:
        print("\n[INFO] matplotlib not available — figure skipped.")


if __name__ == "__main__":
    main()
