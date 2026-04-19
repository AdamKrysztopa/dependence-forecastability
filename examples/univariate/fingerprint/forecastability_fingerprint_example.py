"""F01 example: linear Gaussian-information baseline across synthetic archetypes.

This example demonstrates the linear Gaussian-information baseline I_G(h) computed
via ``compute_linear_information_curve`` for four synthetic archetype series:

* **white_noise** — no autocorrelation; I_G ≈ 0 at all horizons.
* **ar1_monotonic** — strong linear decay; I_G highest at h=1, then monotone decrease.
* **seasonal_periodic** — periodic linear structure; I_G peaks recur near multiples of 12.
* **nonlinear_mixed** — nonlinear process; I_G is low despite detectable AMI signal.

The script prints per-archetype horizon tables, a cross-archetype summary, and saves
a 2×2 bar-chart figure to ``outputs/figures/f01_linear_information_baseline.png``.

Usage:
    uv run python examples/univariate/fingerprint/forecastability_fingerprint_example.py
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.services.linear_information_service import (
    LinearInformationCurve,
    compute_linear_information_curve,
)
from forecastability.utils.synthetic import (
    generate_ar1_monotonic,
    generate_nonlinear_mixed,
    generate_seasonal_periodic,
    generate_white_noise,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_HORIZONS: list[int] = list(range(1, 21))
_N: int = 500
_SEED: int = 42

_ARCHETYPE_NOTES: dict[str, str] = {
    "white_noise": "near-zero, no linear AC",
    "ar1_monotonic": "strong decay",
    "seasonal_periodic": "peaks at multiples of 12",
    "nonlinear_mixed": "low baseline — AMI > I_G",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_series_map(*, n: int, seed: int) -> dict[str, np.ndarray]:
    """Generate all four synthetic archetype series.

    Args:
        n: Number of time steps for each series.
        seed: Integer random seed; passed to every generator.

    Returns:
        Ordered mapping from archetype name to 1-D numpy array.
    """
    return {
        "white_noise": generate_white_noise(n=n, seed=seed),
        "ar1_monotonic": generate_ar1_monotonic(n=n, phi=0.85, seed=seed),
        "seasonal_periodic": generate_seasonal_periodic(
            n=n, period=12, ar_phi=0.5, seasonal_phi=0.8, seed=seed
        ),
        "nonlinear_mixed": generate_nonlinear_mixed(n=n, phi=0.6, nl_strength=0.8, seed=seed),
    }


def _compute_curves(
    series_map: dict[str, np.ndarray],
    *,
    horizons: list[int],
) -> dict[str, LinearInformationCurve]:
    """Compute the Gaussian-information curve for each archetype.

    Args:
        series_map: Mapping from archetype name to series.
        horizons: Positive horizon indices to evaluate.

    Returns:
        Mapping from archetype name to its LinearInformationCurve.
    """
    return {
        name: compute_linear_information_curve(series, horizons=horizons)
        for name, series in series_map.items()
    }


def _print_archetype_table(*, name: str, curve: LinearInformationCurve) -> None:
    """Print a per-horizon table for a single archetype to stdout.

    Args:
        name: Archetype identifier string.
        curve: Computed LinearInformationCurve for this archetype.
    """
    header_width = 48
    print(f"\n\u2550\u2550 {name} {'═' * (header_width - len(name) - 4)}")
    print(f"{'Horizon':>7} | {'rho':>7} | {'I_G (nats)':>10} | valid")
    print("-" * 8 + "|" + "-" * 9 + "|" + "-" * 12 + "|------")
    for point in curve.points:
        rho_str = f"{point.rho:>7.3f}" if point.rho is not None else f"{'N/A':>7}"
        ig_str = (
            f"{point.gaussian_information:>10.4f}"
            if point.gaussian_information is not None
            else f"{'N/A':>10}"
        )
        valid_str = "✓" if point.valid else "✗"
        print(f"{point.horizon:>7}  | {rho_str} | {ig_str}   |  {valid_str}")

    valid_pairs = curve.valid_gaussian_values()
    if valid_pairs:
        ig_values = [ig for _, ig in valid_pairs]
        print(
            f"Summary: max_IG={max(ig_values):.4f},"
            f" mean_IG={sum(ig_values) / len(ig_values):.4f}"
            " (over valid horizons)"
        )
    else:
        print("Summary: no valid horizons")


def _print_comparison_table(curves: dict[str, LinearInformationCurve]) -> None:
    """Print a cross-archetype comparison table to stdout.

    Args:
        curves: Mapping from archetype name to LinearInformationCurve.
    """
    print(f"\n{'═' * 3} Archetype Comparison {'═' * 38}")
    col_name = 20
    print(f"{'Archetype':<{col_name}} | {'max I_G':>7} | {'mean I_G':>8} | {'h=1 I_G':>7} | notes")
    print("-" * (col_name + 1) + "|" + "-" * 9 + "|" + "-" * 10 + "|" + "-" * 9 + "|-------")

    for name, curve in curves.items():
        valid_pairs = curve.valid_gaussian_values()
        if valid_pairs:
            ig_values = [ig for _, ig in valid_pairs]
            max_ig = max(ig_values)
            mean_ig = sum(ig_values) / len(ig_values)
            # I_G at h=1 — look up directly from points list
            h1_point = next((p for p in curve.points if p.horizon == 1), None)
            h1_ig = (
                h1_point.gaussian_information
                if h1_point and h1_point.gaussian_information is not None
                else float("nan")
            )
        else:
            max_ig = mean_ig = h1_ig = float("nan")

        notes = _ARCHETYPE_NOTES.get(name, "")
        print(f"{name:<{col_name}} | {max_ig:>7.3f} | {mean_ig:>8.3f} | {h1_ig:>7.3f} | {notes}")


def _plot_curves(
    curves: dict[str, LinearInformationCurve],
    *,
    save_path: Path,
) -> None:
    """Save a 2×2 bar-chart figure of I_G(h) per archetype.

    Valid-horizon bars are rendered solid; invalid-horizon bars are crosshatched
    to visually distinguish them. Each panel includes a max I_G annotation in
    the title.

    Args:
        curves: Mapping from archetype name to LinearInformationCurve.
        save_path: Destination PNG path; parent directories are created if needed.
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharey=False)
    axes_flat = axes.flatten()

    for ax, (name, curve) in zip(axes_flat, curves.items(), strict=True):
        horizons_all = [p.horizon for p in curve.points]
        ig_all = [
            p.gaussian_information if p.gaussian_information is not None else 0.0
            for p in curve.points
        ]
        valid_flags = [p.valid for p in curve.points]

        colors = ["steelblue" if v else "lightgray" for v in valid_flags]
        hatches = ["" if v else "///" for v in valid_flags]

        for h, ig, color, hatch in zip(horizons_all, ig_all, colors, hatches, strict=True):
            ax.bar(h, ig, color=color, hatch=hatch, edgecolor="dimgray", linewidth=0.6, width=0.7)

        valid_pairs = curve.valid_gaussian_values()
        max_ig = max((ig for _, ig in valid_pairs), default=0.0)

        ax.set_title(f"{name}\n(max I_G = {max_ig:.4f} nats)", fontsize=9)
        ax.set_xlabel("Horizon", fontsize=8)
        ax.set_ylabel("I_G (nats)", fontsize=8)
        ax.set_xticks(horizons_all[::2])
        ax.tick_params(labelsize=7)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle(
        "Linear Gaussian-Information Baseline  I_G(h)  across Synthetic Archetypes",
        fontsize=11,
        fontweight="bold",
    )
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the F01 linear Gaussian-information baseline example and persist artifacts."""
    series_map = _build_series_map(n=_N, seed=_SEED)
    curves = _compute_curves(series_map, horizons=_HORIZONS)

    for name, curve in curves.items():
        _print_archetype_table(name=name, curve=curve)

    _print_comparison_table(curves)

    figure_path = Path("outputs/figures/f01_linear_information_baseline.png")
    _plot_curves(curves, save_path=figure_path)

    print(f"\nFigure saved: {figure_path}")


if __name__ == "__main__":
    main()
