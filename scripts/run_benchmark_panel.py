"""Run rolling-origin benchmark panel and save summary tables."""

from __future__ import annotations

import logging
import os
import signal
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, TypeAlias, cast

import numpy as np
import yaml

# Default to non-interactive plotting backend for script execution.
os.environ.setdefault("MPLBACKEND", "Agg")

from forecastability.aggregation import (
    add_terciles,
    build_horizon_table,
    compute_rank_associations,
    summarize_frequency_panels,
    summarize_terciles,
)
from forecastability.config import (
    BenchmarkDataConfig,
    ModelConfig,
    PaperBaselineConfig,
    RollingOriginConfig,
)
from forecastability.datasets import load_m4_subset
from forecastability.pipeline import run_rolling_origin_evaluation
from forecastability.plots import plot_frequency_panel, plot_smape_vs_ami

_logger = logging.getLogger(__name__)

PanelSpec: TypeAlias = tuple[str, str, int, np.ndarray]
DataSource: TypeAlias = Literal["synthetic", "m4_subset", "m4_mock"]


def _make_panel_series() -> list[PanelSpec]:
    rng = np.random.default_rng(42)
    n = 360
    t = np.arange(n)

    seasonal_trend = 0.02 * t + 1.5 * np.sin(2.0 * np.pi * t / 12) + rng.normal(0.0, 0.3, size=n)

    ar1 = np.zeros(n, dtype=float)
    noise = rng.normal(0.0, 1.0, size=n)
    for idx in range(1, n):
        ar1[idx] = 0.65 * ar1[idx - 1] + noise[idx]

    damped = np.zeros(n, dtype=float)
    shocks = rng.normal(0.0, 0.8, size=n)
    for idx in range(2, n):
        damped[idx] = 0.5 * damped[idx - 1] - 0.2 * damped[idx - 2] + shocks[idx]

    return [
        ("panel_monthly_seasonal", "monthly", 12, seasonal_trend),
        ("panel_monthly_ar1", "monthly", 12, ar1),
        ("panel_monthly_damped", "monthly", 12, damped),
    ]


def _log(msg: str, t0: float | None = None) -> None:
    """Emit a timestamped log line via logging."""
    elapsed = f"  (+{time.time() - t0:.1f}s)" if t0 is not None else ""
    _logger.info("    [%s]%s %s", time.strftime("%H:%M:%S"), elapsed, msg)


@contextmanager
def _series_timeout(seconds: int, series_id: str) -> Generator[None, None, None]:
    """Raise TimeoutError if the block takes longer than *seconds* (Unix only)."""

    def _handler(signum: int, frame: object) -> None:  # noqa: ARG001
        raise TimeoutError(f"series '{series_id}' timed out after {seconds}s")

    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def main() -> None:
    """Run rolling-origin benchmark on a synthetic non-canonical panel."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    t_total = time.time()
    output_root = Path("outputs")
    tables_dir = output_root / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    cfg_path = Path("configs/benchmark_panel.yaml")
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    baseline_cfg = PaperBaselineConfig.model_validate(cfg.get("paper_baseline", {}))
    rolling_cfg = RollingOriginConfig(
        n_origins=int(cfg["rolling_origin"]["n_origins"]),
        horizons=[int(h) for h in cfg["rolling_origin"]["horizons"]],
        seasonal_period=12,
    )
    data_cfg = BenchmarkDataConfig(
        source=cast(DataSource, cfg.get("data", {}).get("source", "synthetic")),
        frequencies=list(cfg.get("data", {}).get("frequencies", ["Monthly"])),
        n_series_per_frequency=int(cfg.get("data", {}).get("n_series_per_frequency", 20)),
        random_state=int(cfg["metric"]["random_state"]),
    )
    model_cfg = ModelConfig(
        include_lightgbm_autoreg=bool(cfg.get("models", {}).get("include_lightgbm_autoreg", False)),
        include_nbeats=bool(cfg.get("models", {}).get("include_nbeats", False)),
    )
    data_cfg = data_cfg.model_copy(
        update={
            "frequencies": [baseline_cfg.normalize_frequency(freq) for freq in data_cfg.frequencies]
        }
    )

    freq_str = ", ".join(data_cfg.frequencies)
    _logger.info(
        "=== Loading panel ===\n  source=%r, frequencies=[%s], n_series_per_frequency=%d",
        data_cfg.source,
        freq_str,
        data_cfg.n_series_per_frequency,
    )
    if data_cfg.source == "synthetic":
        panel = _make_panel_series()
    else:
        panel = []
        for frequency in data_cfg.frequencies:
            panel.extend(
                load_m4_subset(
                    frequency=frequency,
                    n_series=data_cfg.n_series_per_frequency,
                    random_state=data_cfg.random_state,
                    allow_mock=data_cfg.source == "m4_mock",
                )
            )

    n_panel = len(panel)
    _logger.info("  %d series to evaluate.\n", n_panel)
    _logger.info("=== Running rolling-origin evaluations ===")

    results = []
    skipped = 0
    for idx, (series_id, frequency, seasonal_period, ts) in enumerate(panel, start=1):
        series_horizons = baseline_cfg.clamp_horizons(frequency, rolling_cfg.horizons)
        t_series = time.time()
        _logger.info("\n--- Series %d/%d ---", idx, n_panel)
        _logger.info(
            "  [%s] START '%s' (freq=%s, n=%d, horizons=1..%d)",
            time.strftime("%H:%M:%S"),
            series_id,
            frequency,
            len(ts),
            max(series_horizons),
        )
        try:
            with _series_timeout(120, series_id):
                result = run_rolling_origin_evaluation(
                    ts,
                    series_id=series_id,
                    frequency=frequency,
                    horizons=series_horizons,
                    n_origins=rolling_cfg.n_origins,
                    seasonal_period=seasonal_period,
                    random_state=int(cfg["metric"]["random_state"]),
                    include_lightgbm_autoreg=model_cfg.include_lightgbm_autoreg,
                    include_nbeats=model_cfg.include_nbeats,
                )
        except (ValueError, TimeoutError) as exc:
            _log(f"SKIPPED — {exc}", t_series)
            skipped += 1
            continue
        _log(
            f"DONE '{series_id}' — ami_h1={result.ami_by_horizon.get(1, float('nan')):.4f}, "
            f"pami_h1={result.pami_by_horizon.get(1, float('nan')):.4f}",
            t_series,
        )
        results.append(result)

    if skipped:
        _logger.info("\n  Skipped %d series (too short).", skipped)
    _logger.info("\n  Completed %d/%d series.", len(results), n_panel)

    horizon_table = build_horizon_table(results)
    horizon_table.to_csv(tables_dir / "horizon_table.csv", index=False)

    corr_table = compute_rank_associations(horizon_table)
    corr_table.to_csv(tables_dir / "rank_associations.csv", index=False)

    ami_terciles = add_terciles(horizon_table, metric_col="ami", output_col="ami_tercile")
    summarize_terciles(ami_terciles, tercile_col="ami_tercile").to_csv(
        tables_dir / "ami_terciles.csv",
        index=False,
    )

    pami_terciles = add_terciles(horizon_table, metric_col="pami", output_col="pami_tercile")
    summarize_terciles(pami_terciles, tercile_col="pami_tercile").to_csv(
        tables_dir / "pami_terciles.csv",
        index=False,
    )
    freq_summary = summarize_frequency_panels(horizon_table)
    freq_summary.to_csv(tables_dir / "frequency_panel_summary.csv", index=False)
    plot_frequency_panel(freq_summary, save_path=output_root / "figures" / "frequency_panel.png")

    # Per-forecaster sMAPE vs AMI/pAMI scatter plots (paper figure)
    plot_smape_vs_ami(
        horizon_table,
        metric="ami",
        horizons=[1],
        save_path=output_root / "figures" / "smape_vs_ami_h1.png",
    )
    plot_smape_vs_ami(
        horizon_table,
        metric="pami",
        horizons=[1],
        save_path=output_root / "figures" / "smape_vs_pami_h1.png",
    )
    # All horizons pooled
    plot_smape_vs_ami(
        horizon_table,
        metric="ami",
        save_path=output_root / "figures" / "smape_vs_ami_all_horizons.png",
    )

    # Summary table
    _logger.info("\n=== Results summary (rank associations, mean over horizons) ===")
    _h1, _h2, _h3 = "ρ(AMI,sMAPE)", "ρ(pAMI,sMAPE)", "Δ(pAMI−AMI)"
    header = f"  {'Model':<22} {_h1:>13} {_h2:>14} {_h3:>12}"
    _logger.info(header)
    _logger.info("  " + "-" * (len(header) - 2))
    for model, grp in corr_table.groupby("model_name"):
        rho_ami = grp["spearman_ami_smape"].mean()
        rho_pami = grp["spearman_pami_smape"].mean()
        delta = grp["delta_pami_minus_ami"].mean()
        _logger.info("  %-22s %13.4f %14.4f %+12.4f", model, rho_ami, rho_pami, delta)
    _logger.info("")

    _logger.info("Tables saved to %s/", tables_dir)
    _logger.info("Total elapsed: %.1fs", time.time() - t_total)
    _logger.info("Benchmark panel run complete.")


if __name__ == "__main__":
    main()
