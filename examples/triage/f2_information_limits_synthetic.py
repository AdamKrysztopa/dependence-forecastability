"""F2 synthetic example: information-theoretic limits vs achieved performance.

This script compares an original synthetic signal with a destructive transform
(block aggregation) and distinguishes:
- Theoretical ceiling (what is possible under log-loss, via AMI)
- Achieved model performance (what a simple baseline realizes on holdout splits)

Usage:
    uv run python examples/triage/f2_information_limits_synthetic.py
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.datasets import generate_ar1
from forecastability.models import forecast_linear_autoreg, forecast_naive, smape
from forecastability.rolling_origin import build_expanding_window_splits
from forecastability.services.theoretical_limit_diagnostics_service import (
    build_theoretical_limit_diagnostics,
)
from forecastability.triage.models import TriageRequest
from forecastability.triage.run_triage import run_triage
from forecastability.triage.theoretical_limit_diagnostics import TheoreticalLimitDiagnostics


def _generate_source_signal(*, random_state: int, n_samples: int = 1200) -> np.ndarray:
    """Generate a deterministic source signal with seasonal and autoregressive structure.

    Args:
        random_state: Integer seed for deterministic generation.
        n_samples: Number of observations.

    Returns:
        A 1-D synthetic source signal.
    """
    ar_component = generate_ar1(n_samples=n_samples, phi=0.90, random_state=random_state)
    time_index = np.arange(n_samples, dtype=float)
    seasonal = np.sin(2.0 * np.pi * time_index / 24.0) + 0.4 * np.sin(
        2.0 * np.pi * time_index / 6.0
    )
    return ar_component + seasonal


def _aggregate_blocks(series: np.ndarray, *, block_size: int) -> np.ndarray:
    """Apply a destructive aggregation transform by averaging fixed-size blocks.

    Args:
        series: Input time series.
        block_size: Number of consecutive points in each aggregated block.

    Returns:
        A shorter aggregated series.

    Raises:
        ValueError: If block_size is not positive or too large for the series.
    """
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    trimmed = (series.size // block_size) * block_size
    if trimmed == 0:
        raise ValueError("block_size is too large for the input series")
    reshaped = series[:trimmed].reshape(-1, block_size)
    return reshaped.mean(axis=1)


def _compute_theoretical_ceiling(
    *,
    series: np.ndarray,
    max_lag: int,
    random_state: int,
    compression_suspected: bool,
    dpi_suspected: bool,
) -> TheoreticalLimitDiagnostics:
    """Compute F2 theoretical ceiling diagnostics via reusable triage services.

    Args:
        series: Input series.
        max_lag: Maximum lag used for AMI ceiling computation.
        random_state: Deterministic random state passed to triage.
        compression_suspected: Whether to emit a compression warning.
        dpi_suspected: Whether to emit a data-processing warning.

    Returns:
        Theoretical limit diagnostics.

    Raises:
        RuntimeError: If triage fails to produce an AMI curve.
    """
    request = TriageRequest(
        series=series,
        max_lag=max_lag,
        n_surrogates=99,
        random_state=random_state,
    )
    result = run_triage(request)
    if result.blocked or result.analyze_result is None:
        raise RuntimeError("Triage did not return an AMI curve for F2 diagnostics.")

    return build_theoretical_limit_diagnostics(
        result.analyze_result.raw,
        compression_suspected=compression_suspected,
        dpi_suspected=dpi_suspected,
    )


def _evaluate_achieved_performance(
    *,
    series: np.ndarray,
    max_horizon: int,
    n_origins: int,
) -> pd.DataFrame:
    """Evaluate achieved baseline performance using rolling-origin holdout splits.

    Args:
        series: Input series.
        max_horizon: Largest forecast horizon to evaluate.
        n_origins: Number of rolling origins per horizon.

    Returns:
        DataFrame with naive and linear baseline sMAPE, plus realized gain.
    """
    rows: list[dict[str, float | int]] = []

    for horizon in range(1, max_horizon + 1):
        splits = build_expanding_window_splits(series, n_origins=n_origins, horizon=horizon)

        naive_scores: list[float] = []
        linear_scores: list[float] = []
        for split in splits:
            naive_pred = forecast_naive(split.train, horizon)
            linear_pred = forecast_linear_autoreg(
                split.train,
                horizon,
                n_lags=min(24, max(4, horizon * 2)),
            )
            naive_scores.append(smape(split.test, naive_pred))
            linear_scores.append(smape(split.test, linear_pred))

        naive_mean = float(np.mean(naive_scores))
        linear_mean = float(np.mean(linear_scores))
        gain_pct = 0.0
        if naive_mean > 0.0:
            gain_pct = 100.0 * (naive_mean - linear_mean) / naive_mean

        rows.append(
            {
                "horizon": horizon,
                "naive_smape": naive_mean,
                "linear_smape": linear_mean,
                "realized_gain_pct": gain_pct,
            }
        )

    return pd.DataFrame(rows)


def _print_context(
    *,
    label: str,
    diagnostics: TheoreticalLimitDiagnostics,
    achieved: pd.DataFrame,
) -> None:
    """Print possible-vs-achieved diagnostics for one context.

    Args:
        label: Context label (e.g., original or transformed).
        diagnostics: F2 theoretical diagnostics.
        achieved: Holdout achieved-performance table.
    """
    ceiling = diagnostics.forecastability_ceiling_by_horizon
    rounded_ceiling = np.array2string(np.round(ceiling, 4), separator=", ", max_line_width=120)

    print(f"\n=== {label} ===")
    print("Possible (theoretical ceiling from AMI, log-loss interpretation):")
    print(f"ceiling by horizon: {rounded_ceiling}")
    print(f"ceiling summary: {diagnostics.ceiling_summary}")
    print(f"compression warning: {diagnostics.compression_warning}")
    print(f"dpi warning: {diagnostics.dpi_warning}")
    print("Achieved (holdout realization from simple baselines):")
    print(achieved.to_string(index=False, float_format=lambda value: f"{value:0.4f}"))


def _plot_possible_vs_realized(
    *,
    source: np.ndarray,
    transformed: np.ndarray,
    source_diag: TheoreticalLimitDiagnostics,
    transformed_diag: TheoreticalLimitDiagnostics,
    source_achieved: pd.DataFrame,
    transformed_achieved: pd.DataFrame,
    save_path: Path,
) -> None:
    """Save a 2x2 figure separating possible from achieved contexts.

    Args:
        source: Original signal.
        transformed: Destructively transformed signal.
        source_diag: Ceiling diagnostics for original signal.
        transformed_diag: Ceiling diagnostics for transformed signal.
        source_achieved: Holdout achieved table for original signal.
        transformed_achieved: Holdout achieved table for transformed signal.
        save_path: Output figure path.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=False)

    axes[0, 0].plot(source[:300], lw=1.2, color="tab:blue", label="Original signal")
    axes[0, 0].plot(
        np.linspace(0, 299, transformed[:300].size),
        transformed[:300],
        lw=1.2,
        color="tab:orange",
        label="Transformed signal",
    )
    axes[0, 0].set_title("Signals (destructive aggregation shown)")
    axes[0, 0].set_xlabel("Index")
    axes[0, 0].set_ylabel("Value")
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].grid(alpha=0.3)

    horizons = np.arange(1, source_diag.forecastability_ceiling_by_horizon.size + 1)
    axes[0, 1].plot(
        horizons,
        source_diag.forecastability_ceiling_by_horizon,
        marker="o",
        lw=1.6,
        color="tab:blue",
        label="Original possible ceiling",
    )
    axes[0, 1].plot(
        horizons,
        transformed_diag.forecastability_ceiling_by_horizon,
        marker="o",
        lw=1.6,
        color="tab:orange",
        label="Transformed possible ceiling",
    )
    axes[0, 1].set_title("Possible: theoretical ceiling by horizon")
    axes[0, 1].set_xlabel("Horizon")
    axes[0, 1].set_ylabel("MI (nats)")
    axes[0, 1].legend(fontsize=8)
    axes[0, 1].grid(alpha=0.3)

    axes[1, 0].plot(
        source_achieved["horizon"],
        source_achieved["naive_smape"],
        marker="o",
        lw=1.5,
        color="tab:gray",
        label="Naive sMAPE",
    )
    axes[1, 0].plot(
        source_achieved["horizon"],
        source_achieved["linear_smape"],
        marker="o",
        lw=1.5,
        color="tab:green",
        label="Linear autoreg sMAPE",
    )
    axes[1, 0].set_title("Achieved (original): holdout model performance")
    axes[1, 0].set_xlabel("Horizon")
    axes[1, 0].set_ylabel("sMAPE")
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].grid(alpha=0.3)

    axes[1, 1].plot(
        transformed_achieved["horizon"],
        transformed_achieved["naive_smape"],
        marker="o",
        lw=1.5,
        color="tab:gray",
        label="Naive sMAPE",
    )
    axes[1, 1].plot(
        transformed_achieved["horizon"],
        transformed_achieved["linear_smape"],
        marker="o",
        lw=1.5,
        color="tab:green",
        label="Linear autoreg sMAPE",
    )
    axes[1, 1].set_title("Achieved (transformed): holdout model performance")
    axes[1, 1].set_xlabel("Horizon")
    axes[1, 1].set_ylabel("sMAPE")
    axes[1, 1].legend(fontsize=8)
    axes[1, 1].grid(alpha=0.3)

    fig.suptitle(
        "F2 Information Limits: Possible (ceiling) vs Achieved (realization)",
        fontsize=12,
        fontweight="bold",
    )
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=160)
    plt.close(fig)


def _plot_realized_gain(
    *,
    source_achieved: pd.DataFrame,
    transformed_achieved: pd.DataFrame,
    save_path: Path,
) -> None:
    """Save a figure comparing realized gain for original vs transformed signal.

    Args:
        source_achieved: Achieved table for original signal.
        transformed_achieved: Achieved table for transformed signal.
        save_path: Output figure path.
    """
    fig, axis = plt.subplots(1, 1, figsize=(9, 4.5))
    axis.plot(
        source_achieved["horizon"],
        source_achieved["realized_gain_pct"],
        marker="o",
        lw=1.7,
        color="tab:blue",
        label="Original realized gain",
    )
    axis.plot(
        transformed_achieved["horizon"],
        transformed_achieved["realized_gain_pct"],
        marker="o",
        lw=1.7,
        color="tab:orange",
        label="Transformed realized gain",
    )
    axis.axhline(0.0, color="black", lw=1.0)
    axis.set_title("Realized holdout gain vs naive baseline")
    axis.set_xlabel("Horizon")
    axis.set_ylabel("Gain (%)")
    axis.legend(fontsize=9)
    axis.grid(alpha=0.3)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=160)
    plt.close(fig)


def main() -> None:
    """Run the F2 synthetic possible-vs-achieved comparison and save artifacts."""
    random_state = 42
    max_horizon = 12

    source = _generate_source_signal(random_state=random_state, n_samples=1200)
    transformed = _aggregate_blocks(source, block_size=4)

    source_diag = _compute_theoretical_ceiling(
        series=source,
        max_lag=max_horizon,
        random_state=random_state,
        compression_suspected=False,
        dpi_suspected=False,
    )
    transformed_diag = _compute_theoretical_ceiling(
        series=transformed,
        max_lag=max_horizon,
        random_state=random_state,
        compression_suspected=True,
        dpi_suspected=True,
    )

    source_achieved = _evaluate_achieved_performance(
        series=source,
        max_horizon=max_horizon,
        n_origins=10,
    )
    transformed_achieved = _evaluate_achieved_performance(
        series=transformed,
        max_horizon=max_horizon,
        n_origins=10,
    )

    _print_context(label="Original signal", diagnostics=source_diag, achieved=source_achieved)
    _print_context(
        label="Destructive transform (block-aggregated)",
        diagnostics=transformed_diag,
        achieved=transformed_achieved,
    )

    output_dir = Path("outputs/figures/examples/triage")
    possible_vs_realized_path = output_dir / "f2_information_limits_possible_vs_realized.png"
    gain_path = output_dir / "f2_information_limits_realized_gain_comparison.png"

    _plot_possible_vs_realized(
        source=source,
        transformed=transformed,
        source_diag=source_diag,
        transformed_diag=transformed_diag,
        source_achieved=source_achieved,
        transformed_achieved=transformed_achieved,
        save_path=possible_vs_realized_path,
    )
    _plot_realized_gain(
        source_achieved=source_achieved,
        transformed_achieved=transformed_achieved,
        save_path=gain_path,
    )

    print("\nSaved figures:")
    print(f"- {possible_vs_realized_path}")
    print(f"- {gain_path}")


if __name__ == "__main__":
    main()
