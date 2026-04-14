"""F8 example: exogenous screening with strong, weak, and redundant drivers.

This example runs the exogenous screening workbench using a deterministic
pair-evaluator stub to illustrate keep/review/reject decisions quickly.

Usage:
    uv run python examples/triage/f8_exogenous_screening.py
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.use_cases.run_exogenous_screening_workbench import (
    DRIVER_SUMMARY_TABLE_COLUMNS,
    HORIZON_USEFULNESS_TABLE_COLUMNS,
    driver_summary_table_rows,
    horizon_usefulness_table_rows,
    run_exogenous_screening_workbench,
)
from forecastability.utils.config import ExogenousScreeningWorkbenchConfig
from forecastability.utils.types import ExogenousBenchmarkResult, ExogenousScreeningWorkbenchResult

_HORIZONS = list(range(1, 11))


def _build_driver_profiles() -> dict[str, dict[int, tuple[float, float, float]]]:
    """Build deterministic per-horizon exogenous dependence profiles."""
    return {
        "strong_sales_index": {
            1: (0.28, 0.22, 0.79),
            2: (0.26, 0.20, 0.77),
            3: (0.24, 0.19, 0.79),
            4: (0.22, 0.17, 0.77),
            5: (0.19, 0.14, 0.74),
            6: (0.17, 0.12, 0.71),
            7: (0.14, 0.10, 0.71),
            8: (0.12, 0.08, 0.67),
            9: (0.10, 0.06, 0.60),
            10: (0.08, 0.05, 0.62),
        },
        "redundant_sales_proxy": {
            1: (0.18, 0.12, 0.67),
            2: (0.17, 0.11, 0.65),
            3: (0.16, 0.10, 0.63),
            4: (0.15, 0.10, 0.67),
            5: (0.14, 0.09, 0.64),
            6: (0.12, 0.08, 0.67),
            7: (0.11, 0.07, 0.64),
            8: (0.10, 0.06, 0.60),
            9: (0.08, 0.05, 0.62),
            10: (0.07, 0.04, 0.57),
        },
        "weak_weather_noise": {
            1: (0.04, 0.02, 0.50),
            2: (0.03, 0.02, 0.67),
            3: (0.03, 0.01, 1.40),
            4: (0.02, 0.01, 1.50),
            5: (0.02, 0.01, 1.50),
            6: (0.02, 0.01, 1.70),
            7: (0.01, 0.01, 1.20),
            8: (0.01, 0.01, 1.60),
            9: (0.01, 0.01, 1.40),
            10: (0.01, 0.01, 1.80),
        },
    }


def _build_stub_pair_evaluator(
    *,
    profiles: dict[str, dict[int, tuple[float, float, float]]],
):
    """Build deterministic evaluator injected into screening workbench."""

    def _pair_evaluator(
        target: np.ndarray,
        exog: np.ndarray,
        *,
        case_id: str,
        target_name: str,
        exog_name: str,
        horizons: list[int],
        n_origins: int,
        random_state: int,
        n_surrogates: int,
        min_pairs_raw: int,
        min_pairs_partial: int,
        analysis_scope: str,
        project_extension: bool,
    ) -> ExogenousBenchmarkResult:
        del target
        del exog
        del n_origins
        del random_state
        del n_surrogates
        del min_pairs_raw
        del min_pairs_partial
        del analysis_scope
        del project_extension

        profile = profiles[exog_name]
        warning_horizons = [horizon for horizon in horizons if profile[horizon][2] > 1.0]
        return ExogenousBenchmarkResult(
            case_id=case_id,
            target_name=target_name,
            exog_name=exog_name,
            horizons=horizons,
            raw_cross_mi_by_horizon={horizon: profile[horizon][0] for horizon in horizons},
            conditioned_cross_mi_by_horizon={horizon: profile[horizon][1] for horizon in horizons},
            directness_ratio_by_horizon={horizon: profile[horizon][2] for horizon in horizons},
            origins_used_by_horizon={horizon: 6 for horizon in horizons},
            warning_horizons=warning_horizons,
            metadata={"stubbed": 1},
        )

    return _pair_evaluator


def _build_config() -> ExogenousScreeningWorkbenchConfig:
    """Build a deterministic config that yields keep/review/reject outcomes."""
    return ExogenousScreeningWorkbenchConfig.model_validate(
        {
            "horizons": _HORIZONS,
            "n_origins": 6,
            "random_state": 42,
            "n_surrogates": 99,
            "min_pairs_raw": 10,
            "min_pairs_partial": 10,
            "redundancy_alpha": 0.55,
            "apply_bh_correction": True,
            "bh_fdr_alpha": 0.10,
            "lag_windows": [
                {"name": "near_term", "start_horizon": 1, "end_horizon": 3},
                {"name": "mid_term", "start_horizon": 4, "end_horizon": 7},
                {"name": "long_term", "start_horizon": 8, "end_horizon": 10},
            ],
            "pruning": {
                "enabled": True,
                "min_mean_usefulness": 0.012,
                "min_peak_usefulness": 0.020,
                "horizon_usefulness_floor": 0.012,
                "min_horizons_above_floor": 2,
            },
            "recommendation": {
                "keep_min_mean_usefulness": 0.095,
                "keep_min_peak_usefulness": 0.130,
                "review_min_mean_usefulness": 0.040,
                "review_min_peak_usefulness": 0.060,
            },
        }
    )


def _write_csv(
    *,
    csv_path: Path,
    rows: list[dict[str, object]],
    columns: tuple[str, ...],
) -> None:
    """Write deterministic CSV rows with stable column order."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


def _plot_usefulness_heatmap(
    *,
    result: ExogenousScreeningWorkbenchResult,
    output_path: Path,
) -> None:
    """Plot driver-by-horizon usefulness with recommendation labels."""
    ordered_summaries = sorted(result.driver_summaries, key=lambda row: row.overall_rank)
    drivers = [summary.driver_name for summary in ordered_summaries]
    horizons = result.horizons

    row_lookup: dict[str, dict[int, float]] = {driver: {} for driver in drivers}
    for row in result.horizon_usefulness_rows:
        if row.driver_name in row_lookup:
            row_lookup[row.driver_name][row.horizon] = row.usefulness_score

    matrix = np.array(
        [[row_lookup[driver].get(horizon, 0.0) for horizon in horizons] for driver in drivers],
        dtype=float,
    )

    fig, ax = plt.subplots(figsize=(11, 4.5))
    image = ax.imshow(matrix, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(np.arange(len(horizons)))
    ax.set_xticklabels([str(horizon) for horizon in horizons])
    ax.set_yticks(np.arange(len(drivers)))
    ax.set_yticklabels(
        [
            (
                f"#{summary.overall_rank} {summary.driver_name} "
                f"({summary.recommendation}, R={summary.redundancy_score:.2f})"
                if summary.redundancy_score is not None
                else f"#{summary.overall_rank} {summary.driver_name} ({summary.recommendation})"
            )
            for summary in ordered_summaries
        ],
        fontsize=9,
    )
    ax.set_xlabel("horizon")
    ax.set_title("F8 Exogenous screening: horizon usefulness by driver")

    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            ax.text(
                col_index,
                row_index,
                f"{matrix[row_index, col_index]:.2f}",
                ha="center",
                va="center",
                fontsize=8,
                color="black",
            )

    fig.colorbar(image, ax=ax, label="usefulness score")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    """Run the F8 exogenous screening example and save artifacts."""
    profiles = _build_driver_profiles()
    config = _build_config()
    pair_evaluator = _build_stub_pair_evaluator(profiles=profiles)

    n_samples = 220
    target = np.linspace(0.0, 1.0, n_samples, dtype=float)
    drivers = {
        driver_name: np.linspace(index, index + 1.0, n_samples, dtype=float)
        for index, driver_name in enumerate(sorted(profiles), start=1)
    }

    result = run_exogenous_screening_workbench(
        target,
        drivers,
        target_name="toy_retail_target",
        config=config,
        pair_evaluator=pair_evaluator,
    )

    print("\n=== F8 Exogenous Screening Workbench ===")
    print("Scenario drivers:")
    print("- strong_sales_index: intended strong signal")
    print("- redundant_sales_proxy: overlaps with strong driver profile")
    print("- weak_weather_noise: weak/noisy candidate")

    print("\nkeep/review/reject table:")
    print(
        f"{'Rank':<6} {'Driver':<24} {'Recommendation':<14} {'Mean':>7} "
        f"{'Peak':>7} {'Top h':>6} {'BH':>4} {'R-score':>8}"
    )
    print("-" * 88)
    for summary in sorted(result.driver_summaries, key=lambda row: row.overall_rank):
        redundancy_text = (
            f"{summary.redundancy_score:.3f}" if summary.redundancy_score is not None else "-"
        )
        print(
            f"{summary.overall_rank:<6} {summary.driver_name:<24} "
            f"{summary.recommendation:<14} {summary.mean_usefulness_score:>7.3f} "
            f"{summary.peak_usefulness_score:>7.3f} {str(summary.top_horizon or '-'):>6} "
            f"{('yes' if summary.bh_significant else 'no'):>4} {redundancy_text:>8}"
        )

    summary_rows = driver_summary_table_rows(result)
    horizon_rows = horizon_usefulness_table_rows(result)

    tables_dir = Path("outputs/tables/examples/triage")
    json_path = Path("outputs/json/examples/triage/f8_exogenous_screening_result.json")
    figure_path = Path("outputs/figures/examples/triage/f8_exogenous_screening_usefulness.png")

    summary_csv = tables_dir / "f8_exogenous_driver_summary.csv"
    horizon_csv = tables_dir / "f8_exogenous_horizon_usefulness.csv"

    _write_csv(csv_path=summary_csv, rows=summary_rows, columns=DRIVER_SUMMARY_TABLE_COLUMNS)
    _write_csv(csv_path=horizon_csv, rows=horizon_rows, columns=HORIZON_USEFULNESS_TABLE_COLUMNS)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    _plot_usefulness_heatmap(result=result, output_path=figure_path)

    print("\nSaved artifacts:")
    print(f"- {summary_csv}")
    print(f"- {horizon_csv}")
    print(f"- {json_path}")
    print(f"- {figure_path}")


if __name__ == "__main__":
    main()
