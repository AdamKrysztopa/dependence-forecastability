"""Reusable exogenous benchmark slice workflow helpers."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from forecastability.pipeline import run_exogenous_rolling_origin_evaluation
from forecastability.utils.config import ExogenousBenchmarkConfig
from forecastability.utils.plots import plot_exog_benchmark_curves

_logger = logging.getLogger(__name__)

_CANONICAL_DIR = Path("data/raw/canonical")
_EXOG_DIR = Path("data/raw/exog")


def _load_y(path: Path) -> np.ndarray:
    df = pd.read_csv(path)
    return df["y"].to_numpy(dtype=float)


def _align_tail(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(a), len(b))
    return a[-n:], b[-n:]


def _load_noise(n: int) -> np.ndarray:
    noise = _load_y(_EXOG_DIR / "noise_control.csv")
    return noise[-n:]


def load_benchmark_slice(case_ids: list[str]) -> list[tuple[str, str, str, np.ndarray, np.ndarray]]:
    """Load the fixed exogenous benchmark slice from local data."""
    bike = pd.read_csv(_EXOG_DIR / "bike_sharing_hour.csv")
    bike_cnt = bike["cnt"].to_numpy(dtype=float)
    bike_temp = bike["temp"].to_numpy(dtype=float)
    bike_hum = bike["hum"].to_numpy(dtype=float)

    aapl = _load_y(_CANONICAL_DIR / "aapl_returns.csv")
    spy = _load_y(_EXOG_DIR / "spy_returns.csv")
    aapl_aligned, spy_aligned = _align_tail(aapl, spy)

    btc = _load_y(_CANONICAL_DIR / "bitcoin_returns.csv")
    eth = _load_y(_EXOG_DIR / "eth_returns.csv")
    btc_aligned, eth_aligned = _align_tail(btc, eth)

    available = {
        "bike_cnt_temp": ("bike_cnt_temp", "bike_cnt", "temp", bike_cnt, bike_temp),
        "bike_cnt_hum": ("bike_cnt_hum", "bike_cnt", "hum", bike_cnt, bike_hum),
        "bike_cnt_noise": (
            "bike_cnt_noise",
            "bike_cnt",
            "noise",
            bike_cnt,
            _load_noise(len(bike_cnt)),
        ),
        "aapl_spy": ("aapl_spy", "aapl", "spy", aapl_aligned, spy_aligned),
        "aapl_noise": (
            "aapl_noise",
            "aapl",
            "noise",
            aapl_aligned,
            _load_noise(len(aapl_aligned)),
        ),
        "btc_eth": ("btc_eth", "btc", "eth", btc_aligned, eth_aligned),
        "btc_noise": (
            "btc_noise",
            "btc",
            "noise",
            btc_aligned,
            _load_noise(len(btc_aligned)),
        ),
    }
    return [available[case_id] for case_id in case_ids]


def build_case_summary(horizon_table: pd.DataFrame) -> pd.DataFrame:
    """Aggregate exogenous benchmark metrics to one row per case."""
    summary = (
        horizon_table.groupby(["case_id", "target_name", "exog_name"], as_index=False)
        .agg(
            mean_raw_cross_mi=("raw_cross_mi", "mean"),
            mean_conditioned_cross_mi=("conditioned_cross_mi", "mean"),
            mean_directness_ratio=("directness_ratio", "mean"),
            warning_horizon_count=("warning_directness_gt_one", "sum"),
        )
        .sort_values(["target_name", "case_id"])
    )
    summary["warning_note"] = np.where(
        summary["warning_horizon_count"] > 0,
        "Warning only: conditioned signal exceeded raw on at least one horizon.",
        "No directness warnings.",
    )
    return summary


def build_report_markdown(summary_table: pd.DataFrame, cfg: ExogenousBenchmarkConfig) -> str:
    """Render a concise markdown report for the exogenous benchmark slice."""
    lines = [
        "# Exogenous Benchmark Slice",
        "",
        (
            "> Disclosure: exogenous cross-dependence and conditioned "
            "pCrossAMI reporting are project extensions, not paper-native parity."
        ),
        "",
        (
            "This workflow is intended as both descriptive analysis and bounded "
            "model-selection guidance."
        ),
        (
            "Raw CrossMI describes total lagged target-exogenous dependence; "
            "conditioned pCrossAMI isolates direct dependence after conditioning "
            "on intermediate target lags."
        ),
        (
            "All exogenous diagnostics are computed on train windows only "
            "inside rolling-origin evaluation."
        ),
        "",
        f"- Analysis scope: `{cfg.analysis_scope}`",
        f"- Project extension: `{cfg.project_extension}`",
        f"- Cases: {', '.join(cfg.slice_case_ids)}",
        "",
        "## Case Summary",
        "",
        (
            "| Case | Mean Raw CrossMI | Mean Conditioned pCrossAMI | "
            "Mean Directness Ratio | Warning |"
        ),
        "|---|---:|---:|---:|---|",
    ]
    for row in summary_table.to_dict(orient="records"):
        lines.append(
            f"| {row['case_id']} | {float(row['mean_raw_cross_mi']):.4f} | "
            f"{float(row['mean_conditioned_cross_mi']):.4f} | "
            f"{float(row['mean_directness_ratio']):.4f} | {row['warning_note']} |"
        )
    lines += [
        "",
        (
            "Warning policy: any `directness_ratio > 1.0` is reported as a "
            "numerical/estimation warning, not a scientific conclusion."
        ),
    ]
    return "\n".join(lines)


def run_benchmark_exog_panel(
    *,
    cfg_path: Path = Path("configs/benchmark_exog_panel.yaml"),
    output_root: Path = Path("outputs"),
) -> None:
    """Run the exogenous benchmark slice from config and emit artifacts."""
    cfg = ExogenousBenchmarkConfig.model_validate(
        yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    )
    tables_dir = output_root / "tables" / "exog_benchmark"
    figures_dir = output_root / "figures" / "exog_benchmark"
    reports_dir = output_root / "reports"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for case_id, target_name, exog_name, target, exog in load_benchmark_slice(cfg.slice_case_ids):
        _logger.info("Running exogenous benchmark case %s", case_id)
        result = run_exogenous_rolling_origin_evaluation(
            target,
            exog,
            case_id=case_id,
            target_name=target_name,
            exog_name=exog_name,
            horizons=cfg.rolling_origin.horizons,
            n_origins=cfg.rolling_origin.n_origins,
            random_state=cfg.metric.random_state,
            n_surrogates=cfg.metric.n_surrogates,
            min_pairs_raw=cfg.metric.min_pairs_ami,
            min_pairs_partial=cfg.metric.min_pairs_pami,
            analysis_scope=cfg.analysis_scope,
            project_extension=cfg.project_extension,
        )
        results.append(result)

    horizon_rows: list[dict[str, str | int | float]] = []
    for result in results:
        for horizon in result.horizons:
            horizon_rows.append(
                {
                    "case_id": result.case_id,
                    "target_name": result.target_name,
                    "exog_name": result.exog_name,
                    "horizon": horizon,
                    "raw_cross_mi": result.raw_cross_mi_by_horizon[horizon],
                    "conditioned_cross_mi": result.conditioned_cross_mi_by_horizon[horizon],
                    "directness_ratio": result.directness_ratio_by_horizon[horizon],
                    "origins_used": result.origins_used_by_horizon[horizon],
                    "warning_directness_gt_one": int(horizon in result.warning_horizons),
                }
            )

    horizon_table = pd.DataFrame(horizon_rows).sort_values(["case_id", "horizon"])
    summary_table = build_case_summary(horizon_table)
    report_text = build_report_markdown(summary_table, cfg)

    horizon_table.to_csv(tables_dir / "horizon_table.csv", index=False)
    summary_table.to_csv(tables_dir / "case_summary.csv", index=False)
    plot_exog_benchmark_curves(horizon_table, save_path=figures_dir / "raw_vs_conditioned.png")
    (reports_dir / "benchmark_exog_panel.md").write_text(report_text, encoding="utf-8")
