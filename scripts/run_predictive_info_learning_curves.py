"""Run F3 — Predictive Information Learning Curves example.

Demonstrates how lookback sufficiency varies between a finite-memory AR(1)
series (plateau at small k) and a long-memory-like near-unit-root AR(1)
series (plateau at larger k).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from forecastability.services.predictive_info_learning_curve_service import (
    build_predictive_info_learning_curve,
)
from forecastability.triage.predictive_info_learning_curve import PredictiveInfoLearningCurve


def _generate_ar1(n: int, phi: float, seed: int = 0) -> np.ndarray:
    """Generate an AR(1) series: x_t = phi * x_{t-1} + eps_t.

    Args:
        n: Series length.
        phi: Autoregressive coefficient.
        seed: RNG seed for reproducibility.

    Returns:
        1-D array of length ``n``.
    """
    rng = np.random.default_rng(seed)
    out = np.zeros(n)
    out[0] = rng.standard_normal()
    for i in range(1, n):
        out[i] = phi * out[i - 1] + rng.standard_normal()
    return out


def _generate_long_memory(n: int, phi: float = 0.97, seed: int = 1) -> np.ndarray:
    """Simulate a near-unit-root AR(1) to mimic long memory.

    Args:
        n: Series length.
        phi: Near-unit-root autoregressive coefficient.
        seed: RNG seed for reproducibility.

    Returns:
        1-D array of length ``n``.
    """
    return _generate_ar1(n, phi=phi, seed=seed)


def _plot_curve(
    ax: plt.Axes,
    curve: PredictiveInfoLearningCurve,
    title: str,
) -> None:
    """Plot a single learning curve on the given axes.

    Args:
        ax: Matplotlib axes to draw on.
        curve: Learning curve result to visualise.
        title: Plot title.
    """
    ax.plot(curve.window_sizes, curve.information_values, marker="o", linewidth=2)
    if curve.plateau_detected:
        ax.axvline(
            x=curve.recommended_lookback,
            color="red",
            linestyle="--",
            label=f"Recommended lookback = {curve.recommended_lookback}",
        )
    ax.set_xlabel("Lookback k")
    ax.set_ylabel("EvoRate (nats)")
    ax.set_title(title)
    ax.legend(fontsize=8)
    if curve.reliability_warnings:
        warn_text = "\n".join(f"\u26a0 {w}" for w in curve.reliability_warnings)
        ax.text(
            0.02,
            0.02,
            warn_text,
            transform=ax.transAxes,
            fontsize=7,
            verticalalignment="bottom",
            color="darkorange",
            wrap=True,
        )


def main() -> None:
    """Run the F3 learning-curve demonstration and save figure."""
    figures_dir = Path("outputs/figures")
    figures_dir.mkdir(parents=True, exist_ok=True)

    # --- Finite-memory AR(1): phi=0.8, n=500 ---
    finite_mem = _generate_ar1(n=500, phi=0.8, seed=42)
    curve_finite = build_predictive_info_learning_curve(
        finite_mem,
        max_k=8,
        random_state=42,
    )

    # --- Long-memory-like near-unit-root AR(1): phi=0.97, n=1000 ---
    long_mem = _generate_long_memory(n=1000, phi=0.97, seed=99)
    curve_long = build_predictive_info_learning_curve(
        long_mem,
        max_k=8,
        random_state=99,
    )

    # --- Print results ---
    print("=== Finite-memory AR(1) (phi=0.8, n=500) ===")
    print(f"  Window sizes:         {curve_finite.window_sizes}")
    print(f"  I_pred values:        {[round(v, 4) for v in curve_finite.information_values]}")
    print(f"  Plateau detected:     {curve_finite.plateau_detected}")
    print(f"  Recommended lookback: {curve_finite.recommended_lookback}")
    for w in curve_finite.reliability_warnings:
        print(f"  WARNING: {w}")

    print()
    print("=== Long-memory near-unit-root AR(1) (phi=0.97, n=1000) ===")
    print(f"  Window sizes:         {curve_long.window_sizes}")
    print(f"  I_pred values:        {[round(v, 4) for v in curve_long.information_values]}")
    print(f"  Plateau detected:     {curve_long.plateau_detected}")
    print(f"  Recommended lookback: {curve_long.recommended_lookback}")
    for w in curve_long.reliability_warnings:
        print(f"  WARNING: {w}")

    # --- Plot ---
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    _plot_curve(axes[0], curve_finite, "Finite-memory AR(1) (\u03c6=0.8, n=500)")
    _plot_curve(axes[1], curve_long, "Near-unit-root AR(1) (\u03c6=0.97, n=1000)")
    fig.suptitle(
        "Predictive Information Learning Curves \u2014 Lookback Sufficiency",
        fontsize=13,
    )
    plt.tight_layout()
    out_path = figures_dir / "predictive_info_learning_curves.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"\nFigure saved to {out_path}")


if __name__ == "__main__":
    main()
