"""Demonstrate Largest Lyapunov Exponent estimation (F5) on four benchmark signals.

Produces two figures in outputs/figures/lyapunov/:
    f5_lle_divergence_curves.png  — 4-panel log-divergence curves with linear fits
    f5_lle_lambda_comparison.png  — horizontal bar chart comparing λ estimates

Usage::

    uv run python scripts/archive/run_largest_lyapunov_exponent.py
"""

from __future__ import annotations

import pathlib

import matplotlib.pyplot as plt
import numpy as np

from forecastability.metrics.scorers import _embed_series
from forecastability.services.lyapunov_service import build_largest_lyapunov_exponent
from forecastability.triage.lyapunov import LargestLyapunovExponentResult

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------

_OUTPUT_DIR = pathlib.Path("outputs/figures/lyapunov")
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Signal generators
# ---------------------------------------------------------------------------


def _make_logistic(n: int = 500) -> np.ndarray:
    """Logistic map r=3.9 — chaotic (λ > 0)."""
    x = np.empty(n)
    x[0] = 0.5
    for i in range(1, n):
        x[i] = 3.9 * x[i - 1] * (1.0 - x[i - 1])
    return x


def _make_sine(n: int = 500) -> np.ndarray:
    """Pure sine wave — periodic."""
    t = np.linspace(0, 8 * np.pi, n)
    return np.sin(t)


def _make_ar1(n: int = 500, phi: float = 0.7) -> np.ndarray:
    """AR(1) process — stochastic linear memory."""
    rng = np.random.default_rng(123)
    eps = rng.standard_normal(n)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + eps[i]
    return x


def _make_white_noise(n: int = 500) -> np.ndarray:
    """IID standard normal — no temporal structure."""
    return np.random.default_rng(42).standard_normal(n)


# ---------------------------------------------------------------------------
# Divergence curve extraction (for visualisation)
# ---------------------------------------------------------------------------


def _divergence_curve(
    series: np.ndarray,
    *,
    m: int = 3,
    tau: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (steps, avg_log_divergence) arrays for plotting.

    Args:
        series: 1-D time series.
        m: Embedding dimension.
        tau: Time delay.

    Returns:
        Tuple of (step_indices, log_divergence_values).
    """
    n = len(series)
    embedded = _embed_series(series, m=m, tau=tau)
    theiler = max(1, int(0.1 * n))
    steps = max(1, n // 20)

    from forecastability.metrics.scorers import (
        _compute_log_divergence,
        _find_nearest_with_theiler,
    )

    nn = _find_nearest_with_theiler(embedded, theiler_window=theiler)
    y = _compute_log_divergence(embedded, nn, evolution_steps=steps)
    xs = np.arange(steps, dtype=float)
    return xs, y


# ---------------------------------------------------------------------------
# Build results
# ---------------------------------------------------------------------------

SIGNALS: list[tuple[str, np.ndarray]] = [
    ("Logistic map (r=3.9, chaotic)", _make_logistic()),
    ("Sine wave (periodic)", _make_sine()),
    ("AR(1) φ=0.7 (stochastic)", _make_ar1()),
    ("White noise (IID)", _make_white_noise()),
]

results: list[LargestLyapunovExponentResult] = []
curves: list[tuple[np.ndarray, np.ndarray]] = []

print("\n=== Largest Lyapunov Exponent — F5 (EXPERIMENTAL) ===\n")
print("WARNING: LLE estimates are experimental. Do not use as a sole triage decision-maker.\n")

for label, series in SIGNALS:
    result = build_largest_lyapunov_exponent(series)
    results.append(result)
    xs, y = _divergence_curve(series)
    curves.append((xs, y))
    print(f"Signal : {label}")
    print(f"  λ̂     : {result.lambda_estimate:.4f}")
    print(f"  m/tau : {result.embedding_dim}/{result.delay}")
    print(f"  Interp: {result.interpretation}")
    print(f"  Warn  : {result.reliability_warning}")
    print()


# ---------------------------------------------------------------------------
# Figure 1 — log-divergence curves (4-panel)
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(2, 2, figsize=(10, 8))
fig.suptitle(
    "F5 — Largest Lyapunov Exponent: log-divergence curves (Rosenstein 1993)\n"
    "[EXPERIMENTAL — interpret with caution]",
    fontsize=11,
)

colors = ["#c0392b", "#2980b9", "#27ae60", "#8e44ad"]

for ax, (label, _), result, (xs, y), color in zip(
    axes.flat, SIGNALS, results, curves, colors, strict=True
):
    valid = np.isfinite(y)
    if valid.any():
        ax.plot(xs[valid], y[valid], "o-", color=color, markersize=3, linewidth=1.5, label="y(j)")
        # Linear fit overlay
        if valid.sum() >= 2:
            xf = xs[valid]
            coeffs = np.polyfit(xf, y[valid], 1)
            fit_y = np.polyval(coeffs, xf)
            ax.plot(xf, fit_y, "--", color="k", linewidth=1.0, label=f"slope=λ̂={coeffs[0]:.3f}")
    else:
        ax.text(0.5, 0.5, "no valid divergence", ha="center", va="center", transform=ax.transAxes)

    lam = result.lambda_estimate
    title_suffix = f"λ̂={lam:.3f}" if np.isfinite(lam) else "λ̂=nan"
    ax.set_title(f"{label}\n({title_suffix})", fontsize=9)
    ax.set_xlabel("Evolution step j", fontsize=8)
    ax.set_ylabel("⟨log d_j⟩", fontsize=8)
    ax.legend(fontsize=7)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.3)

fig.tight_layout()
fig_path_1 = _OUTPUT_DIR / "f5_lle_divergence_curves.png"
fig.savefig(fig_path_1, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Figure saved: {fig_path_1}")


# ---------------------------------------------------------------------------
# Figure 2 — λ comparison bar chart
# ---------------------------------------------------------------------------

labels = [label for label, _ in SIGNALS]
lambdas = [r.lambda_estimate for r in results]
finite_lambdas = [lam if np.isfinite(lam) else 0.0 for lam in lambdas]
bar_colors = [
    "#c0392b" if lam > 0.1 else ("#27ae60" if lam < -0.1 else "#f39c12") for lam in finite_lambdas
]

fig2, ax2 = plt.subplots(figsize=(8, 4))
bars = ax2.barh(labels, finite_lambdas, color=bar_colors, edgecolor="k", linewidth=0.5)
ax2.axvline(0, color="k", linewidth=0.8, linestyle="--")
ax2.axvline(
    0.1,
    color="#c0392b",
    linewidth=0.6,
    linestyle=":",
    alpha=0.7,
    label="chaotic threshold (0.1)",
)
ax2.axvline(
    -0.1,
    color="#27ae60",
    linewidth=0.6,
    linestyle=":",
    alpha=0.7,
    label="stable threshold (−0.1)",
)

for bar, lam in zip(bars, lambdas, strict=True):
    text = f"{lam:.3f}" if np.isfinite(lam) else "nan"
    ax2.text(
        bar.get_width() + 0.01,
        bar.get_y() + bar.get_height() / 2,
        text,
        va="center",
        fontsize=8,
    )

ax2.set_xlabel("Estimated λ̂ (LLE)", fontsize=9)
ax2.set_title(
    "F5 — Largest Lyapunov Exponent comparison across signals\n[EXPERIMENTAL]",
    fontsize=10,
)
ax2.legend(fontsize=7, loc="lower right")
ax2.tick_params(labelsize=8)
ax2.grid(axis="x", alpha=0.3)
fig2.tight_layout()

fig_path_2 = _OUTPUT_DIR / "f5_lle_lambda_comparison.png"
fig2.savefig(fig_path_2, dpi=150, bbox_inches="tight")
plt.close(fig2)
print(f"Figure saved: {fig_path_2}")

print("\nDone. This is an experimental feature — λ̂ estimates are indicative only.")
