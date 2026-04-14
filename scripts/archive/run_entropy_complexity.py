"""Entropy-Based Complexity Triage example (F6).

Demonstrates permutation entropy (PE) and spectral entropy (SE) for three
synthetic signal types across different complexity regimes:

1. **Periodic** — pure sine wave (low complexity)
2. **AR(1) moderate** — autoregressive process with moderate autocorrelation
   (medium complexity)
3. **White noise** — independent Gaussian samples (high complexity)

Outputs
-------
* ``outputs/figures/entropy_complexity/f6_complexity_band_summary.png``
  — side-by-side time series, PE bar, SE bar, and the PE–SE scatter plot.
* ``outputs/figures/entropy_complexity/f6_pe_se_scatter.png``
  — dedicated PE–SE plane with complexity-band regions annotated.

Usage
-----
    uv run python scripts/archive/run_entropy_complexity.py
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from forecastability.services.complexity_band_service import (
    _HIGH_THRESHOLD,
    _LOW_THRESHOLD,
    build_complexity_band,
)
from forecastability.triage.complexity_band import ComplexityBandResult

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Signal generators
# ---------------------------------------------------------------------------

_N = 512
_RNG = np.random.default_rng(42)


def _make_periodic() -> np.ndarray:
    """Pure sine wave — single dominant frequency."""
    t = np.linspace(0, 16 * np.pi, _N)
    return np.sin(t)


def _make_ar1_moderate() -> np.ndarray:
    """AR(1) with phi=0.7 — moderate autocorrelation, structured dynamics."""
    series = np.zeros(_N)
    series[0] = _RNG.standard_normal()
    for t in range(1, _N):
        series[t] = 0.7 * series[t - 1] + _RNG.standard_normal()
    return series


def _make_white_noise() -> np.ndarray:
    """Independent Gaussian white noise — maximum disorder."""
    return _RNG.standard_normal(_N)


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

_SIGNAL_SPECS: list[tuple[str, np.ndarray]] = [
    ("Periodic (sine)", _make_periodic()),
    ("AR(1) φ=0.7", _make_ar1_moderate()),
    ("White noise", _make_white_noise()),
]

_BAND_COLORS: dict[str, str] = {
    "low": "#2ecc71",  # green
    "medium": "#f39c12",  # orange
    "high": "#e74c3c",  # red
}


def _build_results() -> list[tuple[str, np.ndarray, ComplexityBandResult]]:
    return [(label, series, build_complexity_band(series)) for label, series in _SIGNAL_SPECS]


def _plot_summary(
    results: list[tuple[str, np.ndarray, ComplexityBandResult]],
    out_path: Path,
) -> None:
    """Create a 3-column summary figure: time series | PE | SE."""
    n_signals = len(results)
    fig = plt.figure(figsize=(15, 4 * n_signals))
    gs = gridspec.GridSpec(n_signals, 3, figure=fig, hspace=0.45, wspace=0.35)

    for row, (label, series, result) in enumerate(results):
        color = _BAND_COLORS[result.complexity_band]

        # --- column 0: time series ---
        ax_ts = fig.add_subplot(gs[row, 0])
        ax_ts.plot(series[:200], lw=0.8, color="#555555")
        ax_ts.set_title(f"{label}", fontsize=11, fontweight="bold")
        ax_ts.set_xlabel("Time index")
        ax_ts.set_ylabel("Value")
        band_label = f"Band: {result.complexity_band.upper()}"
        ax_ts.annotate(
            band_label,
            xy=(0.97, 0.95),
            xycoords="axes fraction",
            ha="right",
            va="top",
            fontsize=9,
            color=color,
            fontweight="bold",
        )

        # --- column 1: permutation entropy bar ---
        ax_pe = fig.add_subplot(gs[row, 1])
        ax_pe.barh(
            ["PE"],
            [result.permutation_entropy],
            color=color,
            edgecolor="black",
            linewidth=0.6,
        )
        ax_pe.set_xlim(0, 1)
        ax_pe.set_xlabel("Normalised permutation entropy")
        ax_pe.axvline(_LOW_THRESHOLD, color="gray", linestyle="--", lw=1, label="Low threshold")
        ax_pe.axvline(_HIGH_THRESHOLD, color="gray", linestyle=":", lw=1, label="High threshold")
        ax_pe.text(
            result.permutation_entropy + 0.02,
            0,
            f"{result.permutation_entropy:.3f}",
            va="center",
            fontsize=9,
        )
        if row == 0:
            ax_pe.set_title("Permutation Entropy", fontsize=10)

        # --- column 2: spectral entropy bar ---
        ax_se = fig.add_subplot(gs[row, 2])
        ax_se.barh(
            ["SE"],
            [result.spectral_entropy],
            color=color,
            edgecolor="black",
            linewidth=0.6,
        )
        ax_se.set_xlim(0, 1)
        ax_se.set_xlabel("Normalised spectral entropy")
        ax_se.axvline(_LOW_THRESHOLD, color="gray", linestyle="--", lw=1)
        ax_se.axvline(_HIGH_THRESHOLD, color="gray", linestyle=":", lw=1)
        ax_se.text(
            result.spectral_entropy + 0.02,
            0,
            f"{result.spectral_entropy:.3f}",
            va="center",
            fontsize=9,
        )
        if row == 0:
            ax_se.set_title("Spectral Entropy", fontsize=10)

    fig.suptitle(
        "F6 Entropy-Based Complexity Triage — Summary",
        fontsize=14,
        fontweight="bold",
        y=1.0,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    _logger.info("Saved summary figure: %s", out_path)


def _plot_pe_se_scatter(
    results: list[tuple[str, np.ndarray, ComplexityBandResult]],
    out_path: Path,
) -> None:
    """Plot PE–SE scatter with complexity-band region annotations."""
    fig, ax = plt.subplots(figsize=(7, 6))

    # Background band regions (schematic diagonal split based on composite score)
    # composite = (pe + se) / 2  →  pe + se = threshold * 2 forms the boundary
    x = np.linspace(0, 1, 200)
    lo = _LOW_THRESHOLD * 2
    hi = _HIGH_THRESHOLD * 2

    ax.fill_between(
        x, np.zeros_like(x), np.clip(lo - x, 0, 1), alpha=0.12, color="#2ecc71", label="Low region"
    )
    ax.fill_between(
        x,
        np.clip(lo - x, 0, 1),
        np.clip(hi - x, 0, 1),
        alpha=0.12,
        color="#f39c12",
        label="Medium region",
    )
    ax.fill_between(
        x, np.clip(hi - x, 0, 1), np.ones_like(x), alpha=0.12, color="#e74c3c", label="High region"
    )

    # Diagonal boundary lines
    ax.plot(x, np.clip(lo - x, 0, 1), "--", color="#2ecc71", lw=1.2)
    ax.plot(x, np.clip(hi - x, 0, 1), "--", color="#e74c3c", lw=1.2)

    # Scatter points
    for label, _series, result in results:
        color = _BAND_COLORS[result.complexity_band]
        ax.scatter(
            result.permutation_entropy,
            result.spectral_entropy,
            s=140,
            color=color,
            edgecolors="black",
            linewidths=0.8,
            zorder=5,
        )
        ax.annotate(
            label,
            (result.permutation_entropy, result.spectral_entropy),
            textcoords="offset points",
            xytext=(8, 4),
            fontsize=9,
        )

    # Legend patches for bands
    legend_patches = [
        mpatches.Patch(facecolor="#2ecc71", alpha=0.5, label="Low complexity"),
        mpatches.Patch(facecolor="#f39c12", alpha=0.5, label="Medium complexity"),
        mpatches.Patch(facecolor="#e74c3c", alpha=0.5, label="High complexity"),
    ]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=9)

    ax.set_xlim(-0.02, 1.05)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlabel("Normalised Permutation Entropy (PE)", fontsize=11)
    ax.set_ylabel("Normalised Spectral Entropy (SE)", fontsize=11)
    ax.set_title("F6 Complexity Triage — PE–SE Plane", fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    _logger.info("Saved PE–SE scatter: %s", out_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run F6 entropy-based complexity triage example and save figures."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    figures_dir = Path("outputs/figures/entropy_complexity")
    results = _build_results()

    # ---- console summary ----
    print("\n" + "=" * 62)
    print("  F6 Entropy-Based Complexity Triage — Results")
    print("=" * 62)
    for label, series, result in results:
        print(f"\n  Signal : {label}")
        print(f"  Length : {len(series)}")
        print(f"  Embedding order m = {result.embedding_order}")
        print(f"  Permutation Entropy (norm) : {result.permutation_entropy:.4f}")
        print(f"  Spectral Entropy   (norm) : {result.spectral_entropy:.4f}")
        print(f"  Complexity Band           : {result.complexity_band.upper()}")
        print(f"  {result.interpretation}")
        if result.pe_reliability_warning:
            print(f"  ⚠  {result.pe_reliability_warning}")
    print("\n" + "=" * 62 + "\n")

    # ---- figures ----
    _plot_summary(results, figures_dir / "f6_complexity_band_summary.png")
    _plot_pe_se_scatter(results, figures_dir / "f6_pe_se_scatter.png")

    _logger.info("F6 example complete.")


if __name__ == "__main__":
    main()
