"""Spectral Predictability example (F4).

Demonstrates the spectral predictability score Ω for four synthetic signal
types spanning the full predictability spectrum:

1. **White noise** — flat PSD, Ω ≈ 0 (unpredictable)
2. **AR(1) moderate** — moderate autocorrelation, Ω in the middle range
3. **Seasonal / sum of sines** — dominant seasonal frequencies, Ω high
4. **Pure sine** — single dominant frequency, Ω near 1 (maximally predictable)

Outputs
-------
* ``outputs/figures/spectral_predictability/f4_spectral_predictability_summary.png``
  — 4×3 grid: time series | PSD | Ω score per signal.
* ``outputs/figures/spectral_predictability/f4_omega_comparison.png``
  — horizontal bar comparison of Ω across all four signals.

Usage
-----
    uv run python scripts/run_spectral_predictability.py
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt

from forecastability.diagnostics.spectral_utils import compute_normalised_psd
from forecastability.services.spectral_predictability_service import (
    build_spectral_predictability,
)
from forecastability.triage.spectral_predictability import SpectralPredictabilityResult

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Signal generators
# ---------------------------------------------------------------------------

_N = 512
_RNG = np.random.default_rng(42)


def _make_white_noise() -> np.ndarray:
    """Independent Gaussian white noise — flat spectrum, lowest predictability."""
    return _RNG.standard_normal(_N)


def _make_ar1_moderate() -> np.ndarray:
    """AR(1) with φ=0.7 — moderate autocorrelation, mixed spectrum."""
    rng = np.random.default_rng(0)
    series = np.zeros(_N)
    series[0] = rng.standard_normal()
    for t in range(1, _N):
        series[t] = 0.7 * series[t - 1] + rng.standard_normal()
    return series


def _make_seasonal() -> np.ndarray:
    """Sum of two sinusoidal components with additive noise.

    Dominant period of 12 + a secondary period of 4 — mimics seasonal data
    with a quarterly sub-cycle.  Noise component reduces Ω below the pure
    sine baseline.
    """
    rng = np.random.default_rng(1)
    t = np.arange(_N, dtype=float)
    signal = np.sin(2 * np.pi * t / 12) + 0.5 * np.sin(2 * np.pi * t / 4)
    signal += 0.4 * rng.standard_normal(_N)
    return signal


def _make_pure_sine() -> np.ndarray:
    """Pure sine wave — single frequency, highest spectral predictability."""
    t = np.linspace(0, 16 * np.pi, _N)
    return np.sin(t)


# ---------------------------------------------------------------------------
# Signal registry
# ---------------------------------------------------------------------------

_SIGNAL_SPECS: list[tuple[str, np.ndarray]] = [
    ("White noise", _make_white_noise()),
    ("AR(1) φ=0.7", _make_ar1_moderate()),
    ("Seasonal (T=12 + T=4 + noise)", _make_seasonal()),
    ("Pure sine", _make_pure_sine()),
]

# Colour palette matched to predictability level (low → high)
_OMEGA_COLORS: list[str] = ["#e74c3c", "#f39c12", "#3498db", "#2ecc71"]


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def _build_results() -> list[tuple[str, np.ndarray, SpectralPredictabilityResult]]:
    return [
        (label, series, build_spectral_predictability(series)) for label, series in _SIGNAL_SPECS
    ]


def _plot_summary(
    results: list[tuple[str, np.ndarray, SpectralPredictabilityResult]],
    out_path: Path,
) -> None:
    """Create a 4-row × 3-column summary figure.

    Columns: time series | normalised PSD | Ω score bar.
    """
    n_signals = len(results)
    fig = plt.figure(figsize=(15, 4 * n_signals))
    gs = gridspec.GridSpec(n_signals, 3, figure=fig, hspace=0.50, wspace=0.38)

    for row, (label, series, result) in enumerate(results):
        color = _OMEGA_COLORS[row]

        # ---- column 0: time series (first 200 points) ----
        ax_ts = fig.add_subplot(gs[row, 0])
        ax_ts.plot(series[:200], lw=0.8, color="#333333")
        ax_ts.set_title(label, fontsize=11, fontweight="bold")
        ax_ts.set_xlabel("Time index")
        ax_ts.set_ylabel("Value")
        ax_ts.annotate(
            f"Ω = {result.score:.3f}",
            xy=(0.97, 0.95),
            xycoords="axes fraction",
            ha="right",
            va="top",
            fontsize=10,
            color=color,
            fontweight="bold",
        )

        # ---- column 1: normalised PSD ----
        ax_psd = fig.add_subplot(gs[row, 1])
        freqs, p = compute_normalised_psd(series)
        ax_psd.fill_between(freqs, p, alpha=0.60, color=color)
        ax_psd.plot(freqs, p, lw=0.8, color=color)
        ax_psd.set_xlabel("Normalised frequency")
        ax_psd.set_ylabel("Normalised power")
        if row == 0:
            ax_psd.set_title("Power Spectral Density (normalised)", fontsize=10)
        ax_psd.set_xlim(left=0.0)
        ax_psd.set_ylim(bottom=0.0)

        # ---- column 2: Ω score bar ----
        ax_omega = fig.add_subplot(gs[row, 2])
        ax_omega.barh(
            ["Ω"],
            [result.score],
            color=color,
            edgecolor="black",
            linewidth=0.6,
        )
        ax_omega.set_xlim(0, 1)
        ax_omega.set_xlabel("Spectral predictability Ω")
        ax_omega.axvline(0.40, color="gray", linestyle="--", lw=1.0, label="Low/Mid boundary")
        ax_omega.axvline(0.70, color="gray", linestyle=":", lw=1.0, label="Mid/High boundary")
        ax_omega.text(
            min(result.score + 0.03, 0.97),
            0,
            f"{result.score:.3f}",
            va="center",
            fontsize=10,
        )
        if row == 0:
            ax_omega.set_title("Spectral Predictability Ω", fontsize=10)

    fig.suptitle(
        "F4 Spectral Predictability — Summary",
        fontsize=14,
        fontweight="bold",
        y=1.00,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    _logger.info("Saved summary figure: %s", out_path)


def _plot_omega_comparison(
    results: list[tuple[str, np.ndarray, SpectralPredictabilityResult]],
    out_path: Path,
) -> None:
    """Bar chart comparing Ω across all signals."""
    labels = [label for label, _, _ in results]
    scores = [result.score for _, _, result in results]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(
        labels,
        scores,
        color=_OMEGA_COLORS,
        edgecolor="black",
        linewidth=0.7,
    )
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Spectral predictability Ω", fontsize=12)
    ax.set_title("F4 Spectral Predictability — Signal Comparison", fontsize=13, fontweight="bold")
    ax.axvline(0.40, color="gray", linestyle="--", lw=1.2, label="Low/Moderate boundary (0.40)")
    ax.axvline(0.70, color="gray", linestyle=":", lw=1.2, label="Moderate/High boundary (0.70)")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(axis="x", alpha=0.35)

    # Value labels on bars
    for bar, score in zip(bars, scores, strict=True):
        ax.text(
            score + 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"{score:.3f}",
            va="center",
            fontsize=10,
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    _logger.info("Saved comparison figure: %s", out_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run F4 spectral predictability example and save figures."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    figures_dir = Path("outputs/figures/spectral_predictability")
    results = _build_results()

    # ---- console summary ----
    print("\n" + "=" * 66)
    print("  F4 Spectral Predictability — Results")
    print("=" * 66)
    for label, series, result in results:
        print(f"\n  Signal   : {label}")
        print(f"  Length   : {len(series)}")
        print(f"  N bins   : {result.n_bins}")
        print(f"  Norm. entropy (SE)       : {result.normalised_entropy:.4f}")
        print(f"  Spectral predictability Ω: {result.score:.4f}")
        print(f"  {result.interpretation}")
    print("\n" + "=" * 66 + "\n")

    # ---- figures ----
    _plot_summary(results, figures_dir / "f4_spectral_predictability_summary.png")
    _plot_omega_comparison(results, figures_dir / "f4_omega_comparison.png")

    _logger.info("F4 example complete.")


if __name__ == "__main__":
    main()
