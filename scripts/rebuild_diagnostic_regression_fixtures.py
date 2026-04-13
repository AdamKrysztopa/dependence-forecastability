"""Rebuild and verify diagnostic regression fixtures for F1–F6 diagnostics.

Generates deterministic fixture series, runs each diagnostic service, writes
outputs to JSON, and optionally verifies them against frozen expected files.

Reproduction command (rebuild + verify):
    uv run python scripts/rebuild_diagnostic_regression_fixtures.py --verify

Visualise diagnostic signatures:
    uv run python scripts/rebuild_diagnostic_regression_fixtures.py --verify --plot
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib
import numpy as np

from forecastability.diagnostic_regression import (
    build_diagnostic_regression_outputs,
    verify_diagnostic_regression_outputs,
    write_diagnostic_regression_outputs,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

_logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = Path("outputs/tables/diagnostic_regression")
_DEFAULT_EXPECTED_DIR = Path("docs/fixtures/diagnostic_regression/expected")
_DEFAULT_FIGURES_DIR = Path("outputs/figures/diagnostic_regression")


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild diagnostic regression fixture outputs and optionally verify "
            "against frozen expected JSON files."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help="Directory for rebuilt JSON outputs.",
    )
    parser.add_argument(
        "--expected-dir",
        type=Path,
        default=_DEFAULT_EXPECTED_DIR,
        help="Directory with frozen expected JSON files.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify rebuilt outputs against frozen expected.",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Generate diagnostic signature visualisations.",
    )
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=_DEFAULT_FIGURES_DIR,
        help="Directory for diagnostic plots.",
    )
    return parser


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------


def _plot_ami_profiles(
    outputs: dict[str, dict],
    *,
    figures_dir: Path,
) -> list[Path]:
    """Plot AMI forecastability profiles for series that have F1 results."""
    f1_series = {name: data for name, data in outputs.items() if "F1" in data}
    if not f1_series:
        return []

    fig, ax = plt.subplots(figsize=(10, 5))
    for name, data in sorted(f1_series.items()):
        horizons = data["F1"]["horizons"]
        values = data["F1"]["values"]
        ax.plot(horizons, values, marker="o", markersize=4, label=name)

    ax.set_xlabel("Horizon h")
    ax.set_ylabel("$I_h$ (AMI)")
    ax.set_title("F1 — Forecastability Profiles (AMI curves)")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.3)
    figures_dir.mkdir(parents=True, exist_ok=True)
    path = figures_dir / "f1_forecastability_profiles.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return [path]


def _plot_spectral_and_entropy(
    outputs: dict[str, dict],
    *,
    figures_dir: Path,
) -> list[Path]:
    """Plot F4 Ω vs F6 PE/SE plane for series that have both diagnostics."""
    paths: list[Path] = []
    figures_dir.mkdir(parents=True, exist_ok=True)

    # F4 bar chart — spectral predictability
    f4_series = {name: data["F4"]["omega"] for name, data in outputs.items() if "F4" in data}
    if f4_series:
        fig, ax = plt.subplots(figsize=(8, 4))
        names = sorted(f4_series.keys())
        omegas = [f4_series[n] for n in names]
        bars = ax.barh(names, omegas, color="steelblue", edgecolor="navy", alpha=0.8)
        ax.set_xlabel("Ω (Spectral Predictability)")
        ax.set_title("F4 — Spectral Predictability by Fixture Series")
        ax.set_xlim(0, 1)
        ax.grid(True, axis="x", alpha=0.3)
        for bar, val in zip(bars, omegas, strict=True):
            ax.text(
                val + 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}",
                va="center",
                fontsize=8,
            )
        path = figures_dir / "f4_spectral_predictability.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)

    # F6 entropy plane — PE vs SE scatter
    f6_series = {name: data["F6"] for name, data in outputs.items() if "F6" in data}
    if f6_series:
        fig, ax = plt.subplots(figsize=(7, 6))
        band_colors = {"low": "green", "medium": "orange", "high": "red"}
        for name in sorted(f6_series.keys()):
            d = f6_series[name]
            pe = d["permutation_entropy"]
            se = d["spectral_entropy"]
            band = d["complexity_band"]
            ax.scatter(
                pe,
                se,
                c=band_colors.get(band, "grey"),
                s=80,
                edgecolors="black",
                linewidths=0.5,
                zorder=3,
            )
            ax.annotate(name, (pe, se), textcoords="offset points", xytext=(6, 4), fontsize=7)

        # Band region shading
        ax.axvline(0.40, ls="--", color="grey", alpha=0.4, label="band thresholds")
        ax.axhline(0.40, ls="--", color="grey", alpha=0.4)
        ax.axvline(0.65, ls="--", color="grey", alpha=0.4)
        ax.axhline(0.65, ls="--", color="grey", alpha=0.4)

        ax.set_xlabel("Permutation Entropy (PE)")
        ax.set_ylabel("Spectral Entropy (SE)")
        ax.set_title("F6 — Entropy-Based Complexity Plane")
        ax.set_xlim(0, 1.05)
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)

        # Custom legend for bands
        from matplotlib.lines import Line2D

        legend_elements = [
            Line2D(
                [0], [0], marker="o", color="w", markerfacecolor="green", markersize=8, label="low"
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="orange",
                markersize=8,
                label="medium",
            ),
            Line2D(
                [0], [0], marker="o", color="w", markerfacecolor="red", markersize=8, label="high"
            ),
        ]
        ax.legend(handles=legend_elements, title="Complexity Band", loc="lower right")

        path = figures_dir / "f6_entropy_complexity_plane.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)

    return paths


def _plot_f3_learning_curve(
    outputs: dict[str, dict],
    *,
    figures_dir: Path,
) -> list[Path]:
    """Plot F3 predictive info learning curve."""
    f3_series = {name: data["F3"] for name, data in outputs.items() if "F3" in data}
    if not f3_series:
        return []

    figures_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    for name, data in sorted(f3_series.items()):
        ws = data["window_sizes"]
        iv = data["information_values"]
        ax.plot(ws, iv, marker="s", markersize=5, label=name)
        if data["plateau_detected"]:
            rec_k = data["recommended_lookback"]
            idx = ws.index(rec_k) if rec_k in ws else 0
            ax.axvline(rec_k, ls="--", alpha=0.5, color="grey")
            ax.annotate(
                f"plateau @ k={rec_k}",
                (rec_k, iv[idx]),
                textcoords="offset points",
                xytext=(10, 5),
                fontsize=8,
                arrowprops={"arrowstyle": "->", "color": "grey"},
            )

    ax.set_xlabel("Lookback window k")
    ax.set_ylabel("$I_{pred}(k)$ (nats)")
    ax.set_title("F3 — Predictive Information Learning Curves")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    path = figures_dir / "f3_learning_curves.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return [path]


def _plot_f5_lyapunov(
    outputs: dict[str, dict],
    *,
    figures_dir: Path,
) -> list[Path]:
    """Plot F5 Lyapunov exponent as a simple bar chart."""
    f5_series = {
        name: data["F5"]["lambda_estimate"]
        for name, data in outputs.items()
        if "F5" in data and data["F5"]["lambda_estimate"] is not None
    }
    if not f5_series:
        return []

    figures_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 4))
    names = sorted(f5_series.keys())
    values = [f5_series[n] for n in names]
    colors = ["red" if v > 0.1 else ("orange" if v > 0 else "green") for v in values]
    ax.barh(names, values, color=colors, edgecolor="black", alpha=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.axvline(0.1, color="red", linewidth=0.8, ls="--", alpha=0.5, label="chaotic threshold")
    ax.set_xlabel("λ̂ (Largest Lyapunov Exponent)")
    ax.set_title("F5 — Largest Lyapunov Exponent (EXPERIMENTAL)")
    ax.legend(fontsize=8)
    ax.grid(True, axis="x", alpha=0.3)

    path = figures_dir / "f5_lyapunov_exponent.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return [path]


def _plot_diagnostic_summary_heatmap(
    outputs: dict[str, dict],
    *,
    figures_dir: Path,
) -> list[Path]:
    """Plot a summary heatmap of which diagnostics ran for which series."""
    figures_dir.mkdir(parents=True, exist_ok=True)
    series_names = sorted(outputs.keys())
    all_diags = sorted({d for data in outputs.values() for d in data})

    matrix = np.zeros((len(series_names), len(all_diags)))
    for i, sname in enumerate(series_names):
        for j, dname in enumerate(all_diags):
            if dname in outputs[sname]:
                matrix[i, j] = 1.0

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(matrix, cmap="YlGn", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(len(all_diags)))
    ax.set_xticklabels(all_diags, fontsize=9)
    ax.set_yticks(range(len(series_names)))
    ax.set_yticklabels(series_names, fontsize=8)
    ax.set_title("Diagnostic Regression Coverage Matrix")
    ax.set_xlabel("Diagnostic")
    ax.set_ylabel("Fixture Series")

    for i in range(len(series_names)):
        for j in range(len(all_diags)):
            text = "✓" if matrix[i, j] > 0 else ""
            ax.text(j, i, text, ha="center", va="center", fontsize=10)

    fig.colorbar(im, ax=ax, shrink=0.6, label="Ran (1) / Not run (0)")
    path = figures_dir / "diagnostic_regression_coverage.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return [path]


def main(argv: list[str] | None = None) -> int:
    """Run diagnostic regression fixture rebuild and optional verification.

    Args:
        argv: CLI arguments; ``None`` uses ``sys.argv``.

    Returns:
        Exit code: 0 on success, 2 on verification failure.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _build_parser().parse_args(argv)

    _logger.info("Rebuilding diagnostic regression fixtures → %s", args.output_dir)
    written = write_diagnostic_regression_outputs(output_dir=args.output_dir)
    _logger.info("Wrote %d fixture files.", len(written))
    for path in written:
        _logger.info("  %s", path)

    if args.plot:
        _logger.info("Generating diagnostic visualisations → %s", args.figures_dir)
        outputs = build_diagnostic_regression_outputs()
        all_figures: list[Path] = []
        all_figures.extend(_plot_ami_profiles(outputs, figures_dir=args.figures_dir))
        all_figures.extend(_plot_spectral_and_entropy(outputs, figures_dir=args.figures_dir))
        all_figures.extend(_plot_f3_learning_curve(outputs, figures_dir=args.figures_dir))
        all_figures.extend(_plot_f5_lyapunov(outputs, figures_dir=args.figures_dir))
        all_figures.extend(_plot_diagnostic_summary_heatmap(outputs, figures_dir=args.figures_dir))
        _logger.info("Generated %d figures.", len(all_figures))
        for fig_path in all_figures:
            _logger.info("  %s", fig_path)

    if args.verify:
        _logger.info("Verifying against %s ...", args.expected_dir)
        try:
            verify_diagnostic_regression_outputs(
                actual_dir=args.output_dir,
                expected_dir=args.expected_dir,
            )
        except ValueError as exc:
            _logger.error("Verification FAILED:\n%s", exc)
            return 2
        _logger.info("Verification PASSED — all diagnostics match frozen expected.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
