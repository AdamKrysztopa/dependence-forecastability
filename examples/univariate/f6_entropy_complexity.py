"""F6 example: entropy-based complexity triage.

This example evaluates periodic, noisy, and structured-irregular signals,
then reports permutation entropy, spectral entropy, complexity band, and
practical modeling guidance.

Usage:
    uv run python examples/univariate/f6_entropy_complexity.py
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.services.complexity_band_service import build_complexity_band
from forecastability.triage.complexity_band import ComplexityBandResult


def _make_periodic(*, n_samples: int) -> np.ndarray:
    """Generate a periodic sine process.

    Args:
        n_samples: Number of observations.

    Returns:
        Periodic series.
    """
    time_index = np.linspace(0.0, 18.0 * np.pi, n_samples)
    return np.sin(time_index)


def _make_noisy(*, n_samples: int, random_state: int) -> np.ndarray:
    """Generate deterministic white noise.

    Args:
        n_samples: Number of observations.
        random_state: Integer seed.

    Returns:
        Noisy series.
    """
    rng = np.random.default_rng(random_state)
    return rng.standard_normal(n_samples)


def _make_structured_irregular(*, n_samples: int, random_state: int) -> np.ndarray:
    """Generate structured but irregular dynamics.

    Args:
        n_samples: Number of observations.
        random_state: Integer seed.

    Returns:
        A deterministic mixed-structure signal.
    """
    rng = np.random.default_rng(random_state)
    time_index = np.arange(n_samples, dtype=float)
    seasonal = 0.8 * np.sin(2.0 * np.pi * time_index / 20.0)
    modulated = (1.0 + 0.3 * np.sin(2.0 * np.pi * time_index / 90.0)) * np.sin(
        2.0 * np.pi * time_index / 7.0
    )
    irregular = np.zeros(n_samples, dtype=float)
    irregular[0] = rng.standard_normal()
    for index in range(1, n_samples):
        irregular[index] = 0.45 * irregular[index - 1] + 0.6 * rng.standard_normal()
    return seasonal + 0.7 * modulated + 0.5 * irregular


def _band_guidance(*, band: str) -> str:
    """Map complexity band to practical guidance.

    Args:
        band: Complexity band label.

    Returns:
        Practical recommendation sentence.
    """
    if band == "low":
        return "Prefer simple seasonal or linear models before escalating complexity."
    if band == "high":
        return "Expect higher uncertainty; compare robust baselines with nonlinear alternatives."
    return (
        "Use moderate-capacity models and regularization; validate gains with rolling-origin tests."
    )


def build_example_results() -> list[tuple[str, np.ndarray, ComplexityBandResult]]:
    """Run F6 example scenarios.

    Returns:
        List of tuples with label, series, and complexity-band result.
    """
    signal_specs: list[tuple[str, np.ndarray]] = [
        ("Periodic signal", _make_periodic(n_samples=512)),
        ("Noisy signal", _make_noisy(n_samples=512, random_state=41)),
        (
            "Structured irregular signal",
            _make_structured_irregular(n_samples=512, random_state=42),
        ),
    ]

    return [(label, series, build_complexity_band(series)) for label, series in signal_specs]


def _print_results(*, results: list[tuple[str, np.ndarray, ComplexityBandResult]]) -> None:
    """Print complexity diagnostics with practical guidance.

    Args:
        results: Outputs from :func:`build_example_results`.
    """
    print("\n=== F6 Entropy-Based Complexity Triage ===")
    for label, _series, result in results:
        print(f"\nSignal: {label}")
        print(f"permutation_entropy: {result.permutation_entropy:.4f}")
        print(f"spectral_entropy: {result.spectral_entropy:.4f}")
        print(f"complexity_band: {result.complexity_band}")
        print(f"complexity_summary: {result.interpretation}")
        print(f"model_guidance: {_band_guidance(band=result.complexity_band)}")
        if result.pe_reliability_warning:
            print(f"pe_reliability_warning: {result.pe_reliability_warning}")


def _plot_results(
    *,
    results: list[tuple[str, np.ndarray, ComplexityBandResult]],
    save_path: Path,
) -> None:
    """Plot signal snapshots and PE-SE complexity plane.

    Args:
        results: Outputs from :func:`build_example_results`.
        save_path: PNG output path.
    """
    fig = plt.figure(figsize=(13, 7))
    grid = fig.add_gridspec(2, 3, height_ratios=[1.2, 1.0])

    for index, (label, series, _result) in enumerate(results):
        axis = fig.add_subplot(grid[0, index])
        axis.plot(series[:220], lw=1.0, color="tab:gray")
        axis.set_title(label, fontsize=10)
        axis.set_xlabel("time index")
        axis.set_ylabel("value")
        axis.grid(alpha=0.3)

    scatter_axis = fig.add_subplot(grid[1, :])
    color_map = {"low": "tab:green", "medium": "tab:orange", "high": "tab:red"}

    for label, _series, result in results:
        color = color_map[result.complexity_band]
        scatter_axis.scatter(
            result.permutation_entropy,
            result.spectral_entropy,
            s=120,
            color=color,
            edgecolors="black",
            linewidths=0.7,
            label=f"{label} ({result.complexity_band})",
        )

    scatter_axis.set_xlim(-0.02, 1.02)
    scatter_axis.set_ylim(-0.02, 1.02)
    scatter_axis.set_xlabel("permutation entropy (normalized)")
    scatter_axis.set_ylabel("spectral entropy (normalized)")
    scatter_axis.set_title("PE-SE plane with complexity bands")
    scatter_axis.grid(alpha=0.3)
    scatter_axis.legend(fontsize=8, loc="best")

    fig.suptitle("F6 Entropy Complexity Example", fontsize=12, fontweight="bold")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=160)
    plt.close(fig)


def main() -> None:
    """Run the F6 example and save artifacts."""
    results = build_example_results()
    _print_results(results=results)

    figure_path = Path("outputs/figures/examples/univariate/f6_entropy_complexity.png")
    _plot_results(results=results, save_path=figure_path)

    print("\nSaved figure:")
    print(f"- {figure_path}")


if __name__ == "__main__":
    main()
