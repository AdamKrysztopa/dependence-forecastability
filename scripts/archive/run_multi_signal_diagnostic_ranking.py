"""Batch multi-signal diagnostic ranking example (F7).

Runs deterministic triage on seven synthetic signals spanning the full
forecastability and complexity spectrum, then ranks them and shows how the
new Phase-2 diagnostic columns (spectral predictability, permutation entropy,
complexity band) complement the core forecastability metrics.

Signals
-------
1. **White noise** — IID Gaussian; low forecastability, high complexity
2. **AR(1) φ=0.85** — moderate autocorrelation; medium-high forecastability
3. **Seasonal (period 12)** — dominant periodic component; high forecastability
4. **Random walk** — non-stationary, slowly varying; moderate readiness risk
5. **Sawtooth (period 24)** — non-sinusoidal periodic; high Ω, low PE
6. **Logistic map (r=3.8)** — deterministic chaos; high PE but low AMI
7. **AR(2) seasonal** — autoregressive with seasonal terms; medium complexity

Outputs
-------
* ``outputs/figures/batch_ranking/f7_diagnostic_ranking_heatmap.png``
  — ranked signals × diagnostics heatmap (rank, PE, spectral_predictability,
    complexity_band, forecastability_class).
* ``outputs/figures/batch_ranking/f7_complexity_vs_forecastability.png``
  — scatter: permutation entropy × spectral predictability, coloured by
    forecastability class.

Usage
-----
    uv run python scripts/archive/run_multi_signal_diagnostic_ranking.py
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.triage.batch_models import (
    BatchSeriesRequest,
    BatchTriageRequest,
    BatchTriageResponse,
)
from forecastability.use_cases.run_batch_triage import run_batch_triage

_logger = logging.getLogger(__name__)

_OUTPUT_DIR = Path("outputs/figures/batch_ranking")
_N = 400
_RNG = np.random.default_rng(42)


# ---------------------------------------------------------------------------
# Signal generators
# ---------------------------------------------------------------------------


def _make_white_noise() -> np.ndarray:
    """IID Gaussian white noise — unpredictable, maximally complex."""
    return _RNG.standard_normal(_N)


def _make_ar1() -> np.ndarray:
    """AR(1) with φ=0.85 — moderate-to-high autocorrelation structure."""
    rng = np.random.default_rng(0)
    series = np.zeros(_N)
    series[0] = rng.standard_normal()
    for t in range(1, _N):
        series[t] = 0.85 * series[t - 1] + rng.standard_normal()
    return series


def _make_seasonal() -> np.ndarray:
    """Sum of sinusoids with additive noise — dominant seasonal forecastability."""
    rng = np.random.default_rng(1)
    t = np.arange(_N, dtype=float)
    signal = np.sin(2 * np.pi * t / 12) + 0.5 * np.sin(2 * np.pi * t / 6)
    signal += 0.3 * rng.standard_normal(_N)
    return signal


def _make_random_walk() -> np.ndarray:
    """Cumulative sum of Gaussian increments — non-stationary drift."""
    return np.cumsum(_RNG.standard_normal(_N))


def _make_sawtooth() -> np.ndarray:
    """Pure sawtooth wave of period 24 — non-sinusoidal periodic structure."""
    t = np.arange(_N, dtype=float)
    return t % 24 / 24.0


def _make_logistic() -> np.ndarray:
    """Logistic map at r=3.8 — deterministic chaos, high PE, low AMI."""
    series = np.empty(_N)
    series[0] = 0.5
    r = 3.8
    for t in range(1, _N):
        series[t] = r * series[t - 1] * (1.0 - series[t - 1])
    return series


def _make_ar2_seasonal() -> np.ndarray:
    """AR(2) with seasonal additive component — medium structural complexity."""
    rng = np.random.default_rng(3)
    t = np.arange(_N, dtype=float)
    series = np.zeros(_N)
    series[0] = rng.standard_normal()
    series[1] = rng.standard_normal()
    noise = rng.standard_normal(_N)
    seasonal = 0.5 * np.sin(2 * np.pi * t / 12)
    for i in range(2, _N):
        series[i] = 0.6 * series[i - 1] - 0.3 * series[i - 2] + seasonal[i] + noise[i]
    return series


# ---------------------------------------------------------------------------
# Signal registry
# ---------------------------------------------------------------------------

_SIGNALS: list[tuple[str, np.ndarray]] = [
    ("white_noise", _make_white_noise()),
    ("ar1_phi085", _make_ar1()),
    ("seasonal_t12", _make_seasonal()),
    ("random_walk", _make_random_walk()),
    ("sawtooth_t24", _make_sawtooth()),
    ("logistic_r38", _make_logistic()),
    ("ar2_seasonal", _make_ar2_seasonal()),
]


# ---------------------------------------------------------------------------
# Batch triage
# ---------------------------------------------------------------------------


def _run_batch() -> BatchTriageResponse:
    """Build and execute the batch triage request for all seven signals."""
    items = [
        BatchSeriesRequest(series_id=name, series=series.tolist()) for name, series in _SIGNALS
    ]
    request = BatchTriageRequest(
        items=items,
        max_lag=20,
        n_surrogates=99,
        random_state=42,
    )
    return run_batch_triage(request)


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

_FC_COLOR: dict[str, str] = {
    "high": "#2ecc71",
    "medium": "#f39c12",
    "low": "#e74c3c",
}
_FC_NUMERIC: dict[str, float] = {"high": 1.0, "medium": 0.5, "low": 0.0}
_BAND_NUMERIC: dict[str, float] = {"low": 0.0, "medium": 0.5, "high": 1.0}
_BAND_MARKER: dict[str, str] = {"low": "s", "medium": "o", "high": "D"}


def _plot_diagnostic_heatmap(response: BatchTriageResponse, out_path: Path) -> None:
    """Render a ranked signals × diagnostics heatmap and save to *out_path*."""
    ranked = sorted(response.items, key=lambda x: (x.rank is None, x.rank))

    col_labels = [
        "Spectral predictability (Ω)",
        "Permutation entropy",
        "Forecastability class",
        "Complexity band",
    ]
    n_rows = len(ranked)
    n_cols = len(col_labels)

    matrix = np.zeros((n_rows, n_cols))
    for i, item in enumerate(ranked):
        sp_val = item.spectral_predictability if item.spectral_predictability is not None else 0.0
        pe_val = item.permutation_entropy if item.permutation_entropy is not None else 0.0
        matrix[i, 0] = sp_val
        matrix[i, 1] = pe_val
        matrix[i, 2] = _FC_NUMERIC.get(item.forecastability_class or "", 0.0)
        matrix[i, 3] = _BAND_NUMERIC.get(item.complexity_band_label or "", 0.0)

    y_labels = [f"#{item.rank or '?'}  {item.series_id}" for item in ranked]

    fig, ax = plt.subplots(figsize=(10, max(4, n_rows * 0.8 + 1.5)))
    im = ax.imshow(matrix, aspect="auto", cmap="coolwarm_r", vmin=0.0, vmax=1.0)

    ax.set_xticks(np.arange(n_cols))
    ax.set_xticklabels(col_labels, rotation=20, ha="right", fontsize=10)
    ax.set_yticks(np.arange(n_rows))
    ax.set_yticklabels(y_labels, fontsize=10)

    cell_texts = _build_heatmap_cell_texts(ranked)
    for (row_i, col_j), text in cell_texts.items():
        ax.text(
            col_j,
            row_i,
            text,
            ha="center",
            va="center",
            fontsize=9,
            color="black",
        )

    fig.colorbar(im, ax=ax, label="Normalised score / class encoding")
    ax.set_title(
        "F7: Ranked Diagnostic Profile — 7 Synthetic Signals",
        fontsize=13,
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    _logger.info("Heatmap saved to %s", out_path)


def _build_heatmap_cell_texts(
    ranked: list,
) -> dict[tuple[int, int], str]:
    """Return a mapping of (row, col) → annotation string for heatmap cells."""
    texts: dict[tuple[int, int], str] = {}
    for i, item in enumerate(ranked):
        sp_raw = item.spectral_predictability
        pe_raw = item.permutation_entropy
        sp = f"{sp_raw:.2f}" if sp_raw is not None else "—"
        pe = f"{pe_raw:.2f}" if pe_raw is not None else "—"
        fc = item.forecastability_class or "—"
        band = item.complexity_band_label or "—"
        texts[(i, 0)] = sp
        texts[(i, 1)] = pe
        texts[(i, 2)] = fc
        texts[(i, 3)] = band
    return texts


def _plot_complexity_vs_forecastability(response: BatchTriageResponse, out_path: Path) -> None:
    """Scatter PE × Ω coloured by forecastability class, saved to *out_path*."""
    fig, ax = plt.subplots(figsize=(8, 6))

    ax.axvline(0.5, color="grey", linestyle="--", lw=1.0, alpha=0.6, label="_nolegend_")
    ax.axhline(0.5, color="grey", linestyle="--", lw=1.0, alpha=0.6, label="_nolegend_")

    legend_handles: list = []
    seen_fc: set[str] = set()

    for item in response.items:
        pe = item.permutation_entropy if item.permutation_entropy is not None else 0.0
        sp = item.spectral_predictability if item.spectral_predictability is not None else 0.0
        fc = item.forecastability_class or "unknown"
        band = item.complexity_band_label or "medium"

        color = _FC_COLOR.get(fc, "#95a5a6")
        marker = _BAND_MARKER.get(band, "o")

        ax.scatter(
            pe,
            sp,
            c=color,
            marker=marker,
            s=120,
            edgecolors="black",
            linewidths=0.6,
            zorder=3,
        )

        ax.annotate(
            item.series_id,
            xy=(pe, sp),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=8,
        )

        if fc not in seen_fc:
            seen_fc.add(fc)
            legend_handles.append(
                plt.Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor=color,
                    markeredgecolor="black",
                    markersize=9,
                    label=f"Forecastability: {fc}",
                )
            )

    ax.set_xlabel("Permutation Entropy (PE)", fontsize=11)
    ax.set_ylabel("Spectral Predictability (Ω)", fontsize=11)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(
        "F7: Complexity vs Forecastability — 7 Synthetic Signals",
        fontsize=13,
        fontweight="bold",
    )
    ax.legend(handles=legend_handles, loc="upper right", fontsize=9, framealpha=0.8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    _logger.info("Scatter plot saved to %s", out_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run F7 batch diagnostic ranking and emit figures to *outputs/*."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    response = _run_batch()

    print("\nF7 Batch Diagnostic Ranking — 7 Synthetic Signals")
    print("=" * 80)
    print(f"{'Rank':<6} {'Series ID':<20} {'Forecast.':<12} {'Ω':<8} {'PE':<8} {'Band'}")
    print("-" * 80)
    for item in response.items:
        fc = item.forecastability_class or "—"
        sp_raw = item.spectral_predictability
        pe_raw = item.permutation_entropy
        sp = f"{sp_raw:.3f}" if sp_raw is not None else "—"
        pe = f"{pe_raw:.3f}" if pe_raw is not None else "—"
        band = item.complexity_band_label or "—"
        print(f"{item.rank or '?':<6} {item.series_id:<20} {fc:<12} {sp:<8} {pe:<8} {band}")

    _plot_diagnostic_heatmap(response, _OUTPUT_DIR / "f7_diagnostic_ranking_heatmap.png")
    _plot_complexity_vs_forecastability(
        response, _OUTPUT_DIR / "f7_complexity_vs_forecastability.png"
    )

    _logger.info("Heatmap saved to %s", _OUTPUT_DIR / "f7_diagnostic_ranking_heatmap.png")
    _logger.info(
        "Scatter plot saved to %s",
        _OUTPUT_DIR / "f7_complexity_vs_forecastability.png",
    )


if __name__ == "__main__":
    main()
