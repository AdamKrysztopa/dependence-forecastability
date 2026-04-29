"""Run deterministic causal-rivers rolling-origin analysis.

Artifacts written by this script:
    outputs/figures/causal_rivers/driver_ranking.png
    outputs/figures/causal_rivers/target_baseline_by_horizon.png
    outputs/figures/causal_rivers/station_<id>_cross_mi.png
    outputs/json/causal_rivers/analysis_summary.json
    outputs/json/causal_rivers/target_baseline.json
    outputs/json/causal_rivers/station_<id>.json
    outputs/tables/causal_rivers/driver_summary.csv
    outputs/tables/causal_rivers/driver_horizon_table.csv
    outputs/tables/causal_rivers/target_baseline_by_horizon.csv
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from forecastability.adapters.causal_rivers import (
    CausalRiversAnalysisBundle,
    CausalRiversPairSummary,
    build_pair_horizon_table,
    build_pair_summary_table,
    evaluate_causal_rivers_pair,
    extract_aligned_station_pair,
    extract_station_series,
    load_causal_rivers_config,
    load_resampled_causal_rivers_frame,
)
from forecastability.extensions import (
    TargetBaselineCurves,
    compute_target_baseline_by_horizon,
)

_LOGGER = logging.getLogger(__name__)
_DEFAULT_CONFIG_PATH = Path("configs/causal_rivers_analysis.yaml")
_FIGURES_DIR = Path("outputs/figures/causal_rivers")
_JSON_DIR = Path("outputs/json/causal_rivers")
_TABLES_DIR = Path("outputs/tables/causal_rivers")


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Configured CLI parser.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=_DEFAULT_CONFIG_PATH,
        help="Path to the causal-rivers YAML config.",
    )
    return parser


def _ensure_output_dirs() -> None:
    """Create the deterministic output directories if missing."""
    for path in (_FIGURES_DIR, _JSON_DIR, _TABLES_DIR):
        path.mkdir(parents=True, exist_ok=True)


def _plot_pair_curves(
    pair: CausalRiversPairSummary,
    *,
    horizons: list[int],
) -> None:
    """Save a two-panel per-driver horizon plot.

    Args:
        pair: Evaluated driver summary.
        horizons: Configured horizons to display.
    """
    figure, axes = plt.subplots(1, 2, figsize=(11, 4), sharex=True)
    color = "#2563eb" if pair.role == "positive" else "#dc2626"
    raw_values = [pair.raw_cross_mi_by_horizon.get(horizon, np.nan) for horizon in horizons]
    conditioned_values = [
        pair.conditioned_cross_mi_by_horizon.get(horizon, np.nan) for horizon in horizons
    ]
    axes[0].plot(horizons, raw_values, marker="o", color=color, linewidth=2)
    axes[1].plot(horizons, conditioned_values, marker="o", color=color, linewidth=2)
    axes[0].set_title("CrossAMI")
    axes[1].set_title("pCrossAMI")
    for axis in axes:
        axis.axhline(0.0, color="#9ca3af", linewidth=0.8, linestyle="--")
        axis.set_xlabel("Horizon")
        axis.set_ylabel("MI (nats)")
        axis.set_xticks(horizons)
    figure.suptitle(f"{pair.station_label} ({pair.role})")
    figure.tight_layout()
    figure.savefig(
        _FIGURES_DIR / f"{pair.station_label}_cross_mi.png",
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(figure)


def _plot_driver_ranking(pairs: list[CausalRiversPairSummary]) -> None:
    """Save a ranking chart ordered by conditioned cross-MI.

    Args:
        pairs: Evaluated driver summaries.
    """
    ordered = sorted(pairs, key=lambda pair: pair.mean_conditioned_cross_mi)
    labels = [pair.station_label for pair in ordered]
    raw_values = [pair.mean_raw_cross_mi for pair in ordered]
    conditioned_values = [pair.mean_conditioned_cross_mi for pair in ordered]
    colors = ["#2563eb" if pair.role == "positive" else "#dc2626" for pair in ordered]
    y_positions = np.arange(len(ordered), dtype=float)

    figure, axis = plt.subplots(figsize=(10, max(4, len(ordered) * 0.8)))
    axis.barh(
        y_positions + 0.18,
        raw_values,
        height=0.34,
        color=colors,
        alpha=0.35,
        label="CrossAMI",
    )
    axis.barh(
        y_positions - 0.18,
        conditioned_values,
        height=0.34,
        color=colors,
        alpha=0.85,
        label="pCrossAMI",
    )
    axis.set_yticks(y_positions)
    axis.set_yticklabels(labels)
    axis.set_xlabel("Mean MI across horizons (nats)")
    axis.set_title("Causal-rivers driver ranking for the target station")
    axis.axvline(0.0, color="#9ca3af", linewidth=0.8, linestyle="--")
    axis.legend(loc="lower right")
    figure.tight_layout()
    figure.savefig(_FIGURES_DIR / "driver_ranking.png", dpi=150, bbox_inches="tight")
    plt.close(figure)


def _plot_target_baseline(*, baseline_horizon_table: pd.DataFrame, target_label: str) -> None:
    """Save the target-only baseline curves.

    Args:
        baseline_horizon_table: Long-form target baseline table.
        target_label: Human-readable target label.
    """
    figure, axis = plt.subplots(figsize=(8, 4))
    axis.plot(
        baseline_horizon_table["horizon"],
        baseline_horizon_table["target_ami"],
        marker="o",
        color="#111827",
        linewidth=2,
        label="Target AMI",
    )
    axis.plot(
        baseline_horizon_table["horizon"],
        baseline_horizon_table["target_pami"],
        marker="o",
        color="#059669",
        linewidth=2,
        label="Target pAMI",
    )
    axis.set_xlabel("Horizon")
    axis.set_ylabel("MI (nats)")
    axis.set_title(f"Target baseline by horizon for {target_label}")
    axis.legend(loc="upper right")
    figure.tight_layout()
    figure.savefig(_FIGURES_DIR / "target_baseline_by_horizon.png", dpi=150, bbox_inches="tight")
    plt.close(figure)


def _build_target_baseline_table(
    *,
    target_baseline: TargetBaselineCurves,
    horizons: list[int],
) -> pd.DataFrame:
    """Build the target baseline table.

    Args:
        target_baseline: Target-only baseline result.
        horizons: Configured horizons to emit.

    Returns:
        Long-form target baseline table.
    """
    return pd.DataFrame(
        [
            {
                "horizon": horizon,
                "target_ami": target_baseline.ami_by_horizon.get(horizon, np.nan),
                "target_pami": target_baseline.pami_by_horizon.get(horizon, np.nan),
            }
            for horizon in horizons
        ]
    )


def main(argv: list[str] | None = None) -> int:
    """Run the deterministic causal-rivers analysis.

    Args:
        argv: Optional CLI arguments for programmatic invocation.

    Returns:
        Process exit code.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    config = load_causal_rivers_config(args.config)
    _ensure_output_dirs()

    frame = load_resampled_causal_rivers_frame(config)
    target = extract_station_series(frame, config.station_selection.target_id)
    target_label = f"station_{config.station_selection.target_id}"
    target_baseline = compute_target_baseline_by_horizon(
        series_name=target_label,
        target=target,
        horizons=config.rolling_origin.horizons,
        n_origins=config.rolling_origin.n_origins,
        random_state=config.metric.random_state,
        min_pairs_raw=config.metric.min_pairs_raw,
        min_pairs_partial=config.metric.min_pairs_partial,
        n_surrogates=config.metric.n_surrogates,
    )

    pairs: list[CausalRiversPairSummary] = []
    for station_id in config.station_selection.positive_upstream:
        target_aligned, driver_aligned = extract_aligned_station_pair(
            frame,
            config.station_selection.target_id,
            station_id,
        )
        pairs.append(
            evaluate_causal_rivers_pair(
                config=config,
                target=target_aligned,
                driver=driver_aligned,
                station_id=station_id,
                role="positive",
            )
        )
    for station_id in config.station_selection.negative_control:
        target_aligned, driver_aligned = extract_aligned_station_pair(
            frame,
            config.station_selection.target_id,
            station_id,
        )
        pairs.append(
            evaluate_causal_rivers_pair(
                config=config,
                target=target_aligned,
                driver=driver_aligned,
                station_id=station_id,
                role="negative",
            )
        )

    bundle = CausalRiversAnalysisBundle(
        target_id=config.station_selection.target_id,
        target_label=target_label,
        resample_freq=config.data.resample_freq,
        horizons=config.rolling_origin.horizons,
        target_baseline=target_baseline,
        pairs=pairs,
    )

    (_JSON_DIR / "analysis_summary.json").write_text(
        bundle.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (_JSON_DIR / "target_baseline.json").write_text(
        target_baseline.model_dump_json(indent=2),
        encoding="utf-8",
    )
    for pair in pairs:
        (_JSON_DIR / f"{pair.station_label}.json").write_text(
            pair.model_dump_json(indent=2),
            encoding="utf-8",
        )

    pair_summary_table = build_pair_summary_table(pairs).sort_values(
        ["role", "mean_conditioned_cross_mi"],
        ascending=[True, False],
    )
    pair_summary_table.to_csv(_TABLES_DIR / "driver_summary.csv", index=False)

    pair_horizon_table = build_pair_horizon_table(pairs).sort_values(
        ["role", "station_id", "horizon"],
        ascending=[True, True, True],
    )
    pair_horizon_table.to_csv(_TABLES_DIR / "driver_horizon_table.csv", index=False)

    target_baseline_table = _build_target_baseline_table(
        target_baseline=target_baseline,
        horizons=config.rolling_origin.horizons,
    )
    target_baseline_table.to_csv(_TABLES_DIR / "target_baseline_by_horizon.csv", index=False)

    for pair in pairs:
        _plot_pair_curves(pair, horizons=config.rolling_origin.horizons)
    _plot_driver_ranking(pairs)
    _plot_target_baseline(
        baseline_horizon_table=target_baseline_table,
        target_label=target_label,
    )

    _LOGGER.info("Wrote %d pair JSON files under %s", len(pairs), _JSON_DIR)
    _LOGGER.info("Driver summary table: %s", _TABLES_DIR / "driver_summary.csv")
    _LOGGER.info("Target baseline table: %s", _TABLES_DIR / "target_baseline_by_horizon.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
