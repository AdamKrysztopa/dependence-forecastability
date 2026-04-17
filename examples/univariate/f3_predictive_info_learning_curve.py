"""F3 example: predictive information learning curves.

This example compares short-memory and longer-memory processes, and includes
an explicit small-sample run to demonstrate reliability warnings.

Usage:
    uv run python examples/univariate/f3_predictive_info_learning_curve.py
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.services.predictive_info_learning_curve_service import (
    build_predictive_info_learning_curve,
)
from forecastability.triage.predictive_info_learning_curve import PredictiveInfoLearningCurve


def _generate_ar1(*, n_samples: int, phi: float, random_state: int) -> np.ndarray:
    """Generate a deterministic AR(1) process.

    Args:
        n_samples: Number of observations.
        phi: Autoregressive coefficient.
        random_state: Integer seed for deterministic noise generation.

    Returns:
        A 1-D numpy array of length ``n_samples``.
    """
    rng = np.random.default_rng(random_state)
    series = np.zeros(n_samples, dtype=float)
    series[0] = rng.standard_normal()
    for index in range(1, n_samples):
        series[index] = phi * series[index - 1] + rng.standard_normal()
    return series


def _interpret_case(*, curve: PredictiveInfoLearningCurve) -> str:
    """Build a practical interpretation sentence for one learning-curve result.

    Args:
        curve: Learning-curve result for one signal.

    Returns:
        Practical recommendation text.
    """
    if curve.plateau_detected:
        return (
            f"Plateau detected near k={curve.recommended_lookback}; use a compact "
            "lookback around that value and validate with rolling-origin backtesting."
        )
    return (
        f"No clear plateau by max evaluated k={curve.recommended_lookback}; keep "
        "the current cap and check whether larger k improves out-of-sample errors."
    )


def build_example_results() -> list[tuple[str, PredictiveInfoLearningCurve]]:
    """Run all F3 example cases and return their learning-curve outputs.

    Returns:
        A list of ``(label, curve_result)`` tuples.
    """
    series_specs: list[tuple[str, np.ndarray, int, int]] = [
        (
            "Short-memory AR(1), phi=0.60, n=600",
            _generate_ar1(n_samples=600, phi=0.60, random_state=21),
            8,
            121,
        ),
        (
            "Longer-memory AR(1), phi=0.95, n=1200",
            _generate_ar1(n_samples=1200, phi=0.95, random_state=22),
            8,
            122,
        ),
        (
            "Small-sample warning demo, phi=0.95, n=180",
            _generate_ar1(n_samples=180, phi=0.95, random_state=23),
            8,
            123,
        ),
    ]

    results: list[tuple[str, PredictiveInfoLearningCurve]] = []
    for label, series, max_k, random_state in series_specs:
        curve = build_predictive_info_learning_curve(
            series,
            max_k=max_k,
            random_state=random_state,
        )
        results.append((label, curve))
    return results


def _print_results(*, results: list[tuple[str, PredictiveInfoLearningCurve]]) -> None:
    """Print numeric and practical outputs for all cases.

    Args:
        results: Learning-curve outputs from :func:`build_example_results`.
    """
    print("\n=== F3 Predictive Information Learning Curves ===")
    for label, curve in results:
        rounded_values = [round(value, 4) for value in curve.information_values]
        print(f"\nCase: {label}")
        print(f"window_sizes: {curve.window_sizes}")
        print(f"information_values: {rounded_values}")
        print(f"plateau_detected: {curve.plateau_detected}")
        print(f"recommended_lookback: {curve.recommended_lookback}")
        print(f"lookback_summary: {_interpret_case(curve=curve)}")
        if curve.reliability_warnings:
            print("reliability_warnings:")
            for warning in curve.reliability_warnings:
                print(f"- {warning}")
        else:
            print("reliability_warnings: none")


def _plot_results(
    *,
    results: list[tuple[str, PredictiveInfoLearningCurve]],
    save_path: Path,
) -> None:
    """Plot learning curves for all cases.

    Args:
        results: Learning-curve outputs from :func:`build_example_results`.
        save_path: PNG output path.
    """
    fig, axes = plt.subplots(1, len(results), figsize=(5 * len(results), 4), sharey=True)
    if len(results) == 1:
        axes = np.array([axes])

    for axis, (label, curve) in zip(axes, results, strict=True):
        axis.plot(
            curve.window_sizes,
            curve.information_values,
            marker="o",
            lw=1.6,
            color="tab:blue",
        )
        if curve.plateau_detected:
            axis.axvline(
                curve.recommended_lookback,
                color="tab:red",
                ls="--",
                lw=1.2,
                label=f"recommended k={curve.recommended_lookback}",
            )
        if curve.reliability_warnings:
            axis.text(
                0.03,
                0.03,
                "warning: sample size caution",
                transform=axis.transAxes,
                fontsize=8,
                va="bottom",
                color="tab:orange",
            )
        axis.set_title(label, fontsize=9)
        axis.set_xlabel("lookback k")
        axis.grid(alpha=0.3)
        axis.legend(fontsize=8, loc="best")

    axes[0].set_ylabel("predictive information (nats)")
    fig.suptitle("F3 Predictive Information Learning Curves", fontsize=12, fontweight="bold")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=160)
    plt.close(fig)


def main() -> None:
    """Run the F3 example and save artifacts."""
    results = build_example_results()
    _print_results(results=results)

    figure_path = Path("outputs/figures/examples/univariate/f3_predictive_info_learning_curve.png")
    _plot_results(results=results, save_path=figure_path)

    print("\nSaved figure:")
    print(f"- {figure_path}")


if __name__ == "__main__":
    main()
