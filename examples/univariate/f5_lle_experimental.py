"""F5 example: experimental Largest Lyapunov Exponent with sensitivity checks.

This example contrasts a chaotic toy system with a smooth non-chaotic series,
then demonstrates how the estimated LLE changes with embedding parameters.

Usage:
    uv run python examples/univariate/f5_lle_experimental.py
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.services.lyapunov_service import build_largest_lyapunov_exponent
from forecastability.triage.lyapunov import LargestLyapunovExponentResult


def _make_logistic_map(*, n_samples: int, r: float, x0: float = 0.23) -> np.ndarray:
    """Generate a deterministic logistic map.

    Args:
        n_samples: Number of observations.
        r: Logistic-map parameter.
        x0: Initial state.

    Returns:
        Logistic-map trajectory.
    """
    series = np.empty(n_samples, dtype=float)
    series[0] = x0
    for index in range(1, n_samples):
        series[index] = r * series[index - 1] * (1.0 - series[index - 1])
    return series


def _make_smooth_nonchaotic(*, n_samples: int) -> np.ndarray:
    """Generate a smooth non-chaotic benchmark signal.

    Args:
        n_samples: Number of observations.

    Returns:
        Smooth periodic mixture with no chaotic map dynamics.
    """
    time_index = np.arange(n_samples, dtype=float)
    return np.sin(2.0 * np.pi * time_index / 48.0) + 0.25 * np.sin(
        2.0 * np.pi * time_index / 96.0 + 0.4
    )


def _run_sensitivity_grid(
    *,
    series: np.ndarray,
    embedding_dims: list[int],
    delays: list[int],
) -> dict[tuple[int, int], LargestLyapunovExponentResult]:
    """Evaluate LLE across an embedding/delay grid.

    Args:
        series: Input signal.
        embedding_dims: Embedding dimensions to evaluate.
        delays: Delay values to evaluate.

    Returns:
        Mapping from ``(embedding_dim, delay)`` to LLE result.
    """
    grid_results: dict[tuple[int, int], LargestLyapunovExponentResult] = {}
    for embedding_dim in embedding_dims:
        for delay in delays:
            grid_results[(embedding_dim, delay)] = build_largest_lyapunov_exponent(
                series,
                embedding_dim=embedding_dim,
                delay=delay,
            )
    return grid_results


def _to_lambda_matrix(
    *,
    grid_results: dict[tuple[int, int], LargestLyapunovExponentResult],
    embedding_dims: list[int],
    delays: list[int],
) -> np.ndarray:
    """Convert grid results to a matrix indexed by embedding and delay."""
    matrix = np.full((len(embedding_dims), len(delays)), np.nan, dtype=float)
    for row_index, embedding_dim in enumerate(embedding_dims):
        for col_index, delay in enumerate(delays):
            matrix[row_index, col_index] = grid_results[(embedding_dim, delay)].lambda_estimate
    return matrix


def _print_case_summary(
    *,
    case_name: str,
    baseline: LargestLyapunovExponentResult,
    lambda_matrix: np.ndarray,
    embedding_dims: list[int],
    delays: list[int],
) -> None:
    """Print one case summary with parameter-sensitivity table."""
    finite_values = lambda_matrix[np.isfinite(lambda_matrix)]
    if finite_values.size > 0:
        sensitivity_span = float(finite_values.max() - finite_values.min())
        min_text = f"{finite_values.min():.4f}"
        max_text = f"{finite_values.max():.4f}"
    else:
        sensitivity_span = float("nan")
        min_text = "nan"
        max_text = "nan"

    print(f"\nCase: {case_name}")
    print(f"baseline_lambda (m=3, delay=1): {baseline.lambda_estimate:.4f}")
    print(f"interpretation: {baseline.interpretation}")
    print(f"reliability_warning: {baseline.reliability_warning}")
    print(f"sensitivity_range: min={min_text}, max={max_text}, span={sensitivity_span:.4f}")
    print("parameter_sensitivity_table:")

    header = "m\\delay | " + " | ".join(str(delay) for delay in delays)
    print(header)
    print("-" * len(header))
    for row_index, embedding_dim in enumerate(embedding_dims):
        row_cells: list[str] = []
        for col_index, _delay in enumerate(delays):
            value = lambda_matrix[row_index, col_index]
            row_cells.append(f"{value:.4f}" if np.isfinite(value) else "nan")
        print(f"{embedding_dim:>7} | " + " | ".join(row_cells))


def _plot_results(
    *,
    cases: list[tuple[str, np.ndarray, np.ndarray]],
    embedding_dims: list[int],
    delays: list[int],
    output_path: Path,
) -> None:
    """Save signal snapshots and LLE sensitivity heatmaps.

    Args:
        cases: Tuples of ``(label, series, lambda_matrix)``.
        embedding_dims: Grid embedding dimensions.
        delays: Grid delays.
        output_path: Figure save path.
    """
    finite_all = np.concatenate(
        [matrix[np.isfinite(matrix)] for _label, _series, matrix in cases],
        axis=0,
    )
    vmin = float(finite_all.min()) if finite_all.size > 0 else -0.5
    vmax = float(finite_all.max()) if finite_all.size > 0 else 0.5

    fig = plt.figure(figsize=(12, 7))
    grid = fig.add_gridspec(2, len(cases), height_ratios=[1.0, 1.3])
    heatmap_image = None

    for column_index, (label, series, lambda_matrix) in enumerate(cases):
        axis_series = fig.add_subplot(grid[0, column_index])
        axis_series.plot(series[:220], lw=1.1, color="tab:gray")
        axis_series.set_title(label, fontsize=10)
        axis_series.set_xlabel("time index")
        axis_series.set_ylabel("value")
        axis_series.grid(alpha=0.3)

        axis_heatmap = fig.add_subplot(grid[1, column_index])
        heatmap_image = axis_heatmap.imshow(
            lambda_matrix,
            aspect="auto",
            cmap="coolwarm",
            vmin=vmin,
            vmax=vmax,
        )
        axis_heatmap.set_xticks(np.arange(len(delays)))
        axis_heatmap.set_xticklabels([str(delay) for delay in delays])
        axis_heatmap.set_yticks(np.arange(len(embedding_dims)))
        axis_heatmap.set_yticklabels([str(embedding_dim) for embedding_dim in embedding_dims])
        axis_heatmap.set_xlabel("delay")
        axis_heatmap.set_ylabel("embedding_dim")
        axis_heatmap.set_title("lambda sensitivity")

        for row_index, _embedding_dim in enumerate(embedding_dims):
            for col_index, _delay in enumerate(delays):
                value = lambda_matrix[row_index, col_index]
                text = f"{value:.2f}" if np.isfinite(value) else "nan"
                axis_heatmap.text(
                    col_index,
                    row_index,
                    text,
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="black",
                )

    if heatmap_image is not None:
        fig.colorbar(heatmap_image, ax=fig.axes, shrink=0.85, label="estimated lambda")

    fig.suptitle(
        "F5 Experimental LLE: baseline and parameter sensitivity\n"
        "Warning: experimental diagnostic, never a sole decision criterion",
        fontsize=12,
        fontweight="bold",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(top=0.84)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main() -> None:
    """Run the E5 example and save artifacts."""
    embedding_dims = [2, 3, 4]
    delays = [1, 2, 3]

    case_specs: list[tuple[str, np.ndarray]] = [
        ("Chaotic logistic map (r=3.9)", _make_logistic_map(n_samples=700, r=3.9)),
        ("Smooth non-chaotic oscillation", _make_smooth_nonchaotic(n_samples=700)),
    ]

    print("\n=== F5 Largest Lyapunov Exponent (EXPERIMENTAL) ===")
    print(
        "WARNING: This diagnostic is experimental and sensitive to embedding choices; "
        "do not use it as a sole triage decision-maker."
    )

    plotted_cases: list[tuple[str, np.ndarray, np.ndarray]] = []
    for case_name, series in case_specs:
        baseline = build_largest_lyapunov_exponent(series)
        grid_results = _run_sensitivity_grid(
            series=series,
            embedding_dims=embedding_dims,
            delays=delays,
        )
        lambda_matrix = _to_lambda_matrix(
            grid_results=grid_results,
            embedding_dims=embedding_dims,
            delays=delays,
        )
        _print_case_summary(
            case_name=case_name,
            baseline=baseline,
            lambda_matrix=lambda_matrix,
            embedding_dims=embedding_dims,
            delays=delays,
        )
        plotted_cases.append((case_name, series, lambda_matrix))

    figure_path = Path("outputs/figures/examples/univariate/f5_lle_experimental_sensitivity.png")
    _plot_results(
        cases=plotted_cases,
        embedding_dims=embedding_dims,
        delays=delays,
        output_path=figure_path,
    )

    print("\nSaved figure:")
    print(f"- {figure_path}")


if __name__ == "__main__":
    main()
