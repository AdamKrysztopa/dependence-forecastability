"""CausalRivers CrossAMI / pCrossAMI use-case analysis pipeline.

Loads the East Germany subset of the CausalRivers benchmark, resamples to
6-hour resolution, and runs rolling-origin CrossAMI / pCrossAMI evaluation
for a target station (Unstrut @ 978) against:

  - positive candidates: direct upstream tributaries (graph-verified causal)
  - negative controls:   stations from unrelated river basins

Artifacts saved to:
  outputs/figures/causal_rivers/   — per-pair PNG figures, ranking bar chart
  outputs/json/causal_rivers/      — per-pair JSON result records
  outputs/tables/causal_rivers/    — ranking CSV, horizon pivot table

Usage:
    MPLBACKEND=Agg uv run python scripts/run_causal_rivers_analysis.py
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from forecastability.pipeline import run_exogenous_rolling_origin_evaluation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_CFG_PATH = Path("configs/causal_rivers_analysis.yaml")
_FIG_DIR = Path("outputs/figures/causal_rivers")
_JSON_DIR = Path("outputs/json/causal_rivers")
_TABLE_DIR = Path("outputs/tables/causal_rivers")


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------
def _load_config() -> dict:
    """Load YAML analysis config."""
    with _CFG_PATH.open() as fh:
        return yaml.safe_load(fh)


def _load_and_resample(cfg: dict) -> pd.DataFrame:
    """Load the East Germany time-series CSV and resample to configured frequency.

    Args:
        cfg: Parsed YAML config dict.

    Returns:
        DataFrame indexed by timestamp with station IDs as integer column names.
    """
    raw_dir = Path(cfg["data"]["raw_dir"])
    ts_path = raw_dir / cfg["data"]["ts_file"]
    _logger.info("Loading time series from %s …", ts_path)

    ts = pd.read_csv(ts_path, index_col=0, parse_dates=True)
    _logger.info("  Raw shape: %s  (index freq: 15 min)", ts.shape)

    freq = cfg["data"]["resample_freq"]
    ts_rs = ts.resample(freq).mean()
    _logger.info("  Resampled → %s at %s", ts_rs.shape, freq)

    # Rename columns to int for consistent lookup
    ts_rs.columns = [int(c) for c in ts_rs.columns]
    return ts_rs


def _extract_series(ts: pd.DataFrame, station_id: int) -> np.ndarray:
    """Extract a cleaned numpy array for one station, forward-filling short NaN gaps.

    Gaps longer than 4 consecutive steps (1 day at 6H) are left as NaN to avoid
    artefacts — the MI estimator handles shorter arrays gracefully.

    Args:
        ts: Resampled DataFrame with integer station IDs as columns.
        station_id: Station ID to extract.

    Returns:
        1-D float64 array with short NaN gaps filled.
    """
    col = ts[station_id].copy()
    # Forward-fill short gaps only (limit=4 steps = 1 day at 6H resolution)
    col = col.ffill(limit=4)
    # Drop any remaining NaN at the boundaries
    col = col.dropna()
    return col.to_numpy(dtype=float)


# ---------------------------------------------------------------------------
# Rolling-origin per-pair evaluation
# ---------------------------------------------------------------------------
def _run_pair(
    pair_name: str,
    description: str,
    target: np.ndarray,
    driver: np.ndarray,
    cfg: dict,
    *,
    role: str,
) -> dict:
    """Run rolling-origin CrossAMI + pCrossAMI for one target–driver pair.

    Args:
        pair_name: Short slug used for filenames.
        description: Human-readable description.
        target: 1-D target time series (shorter common tail is auto-aligned).
        driver: 1-D driver time series.
        cfg: Parsed YAML config dict.
        role: ``"positive"`` or ``"negative"`` — used for annotations.

    Returns:
        Dict with summary metrics, curves, and metadata ready for JSON export.
    """
    roc = cfg["rolling_origin"]
    mc = cfg["metric"]

    # Align tails (same length, most recent observations)
    n = min(len(target), len(driver))
    target_al = target[-n:]
    driver_al = driver[-n:]

    _logger.info(
        "  Running '%s' (%s, n=%d, %d origins, horizons=%s)",
        pair_name,
        role,
        n,
        roc["n_origins"],
        roc["horizons"],
    )

    result = run_exogenous_rolling_origin_evaluation(
        target=target_al,
        exog=driver_al,
        case_id=pair_name,
        target_name=f"station_{cfg['station_selection']['target_id']}",
        exog_name=f"station_{pair_name}",
        horizons=roc["horizons"],
        n_origins=roc["n_origins"],
        random_state=mc["random_state"],
        n_surrogates=mc["n_surrogates"],
        min_pairs_raw=mc["min_pairs_raw"],
        min_pairs_partial=mc["min_pairs_partial"],
        analysis_scope=cfg.get("analysis_scope", "both"),
        project_extension=cfg.get("project_extension", True),
    )

    # Summary scalars
    raw_vals = list(result.raw_cross_mi_by_horizon.values())
    partial_vals = list(result.conditioned_cross_mi_by_horizon.values())
    dr_vals = list(result.directness_ratio_by_horizon.values())

    mean_raw = float(np.mean(raw_vals)) if raw_vals else float("nan")
    mean_partial = float(np.mean(partial_vals)) if partial_vals else float("nan")
    mean_dr = float(np.mean(dr_vals)) if dr_vals else float("nan")

    return {
        "pair_name": pair_name,
        "description": description,
        "role": role,
        "n_obs": int(n),
        "mean_raw_cross_ami": mean_raw,
        "mean_pCrossAMI": mean_partial,
        "mean_directness_ratio": mean_dr,
        "warning_horizon_count": len(result.warning_horizons),
        "per_horizon_raw": {str(h): float(v) for h, v in result.raw_cross_mi_by_horizon.items()},
        "per_horizon_partial": {
            str(h): float(v) for h, v in result.conditioned_cross_mi_by_horizon.items()
        },
        "per_horizon_dr": {str(h): float(v) for h, v in result.directness_ratio_by_horizon.items()},
    }


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def _plot_horizon_curves(summary_records: list[dict], cfg: dict) -> None:
    """Save per-pair CrossAMI-vs-horizon line plots.

    Args:
        summary_records: Output of :func:`_run_pair` calls.
        cfg: Parsed YAML config dict.
    """
    horizons = cfg["rolling_origin"]["horizons"]
    freq = cfg["data"]["resample_freq"]

    for rec in summary_records:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=False)
        for ax, key, title in [
            (axes[0], "per_horizon_raw", "CrossAMI (raw)"),
            (axes[1], "per_horizon_partial", "pCrossAMI (direct)"),
        ]:
            vals = [rec[key].get(str(h), np.nan) for h in horizons]
            color = "#2a7ae2" if rec["role"] == "positive" else "#dc322f"
            ax.plot(horizons, vals, marker="o", color=color, linewidth=2)
            ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
            ax.set_xlabel(f"Horizon ({freq} steps)")
            ax.set_ylabel("MI (nats)")
            ax.set_title(title)
            ax.set_xticks(horizons)

        role_label = "POSITIVE (upstream)" if rec["role"] == "positive" else "NEGATIVE control"
        fig.suptitle(
            f"{rec['pair_name']}  [{role_label}]\n{rec['description']}",
            fontsize=10,
        )
        fig.tight_layout()
        out_path = _FIG_DIR / f"{rec['pair_name']}_horizon_curves.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        _logger.info("    Figure saved → %s", out_path)


def _plot_ranking(summary_records: list[dict]) -> None:
    """Save a horizontal bar chart ranking all pairs by mean CrossAMI.

    Args:
        summary_records: Output of :func:`_run_pair` calls.
    """
    df = pd.DataFrame(summary_records).sort_values("mean_raw_cross_ami", ascending=True)
    colors = ["#2a7ae2" if r == "positive" else "#dc322f" for r in df["role"]]

    fig, ax = plt.subplots(figsize=(9, max(4, len(df) * 0.55)))
    ax.barh(df["pair_name"], df["mean_raw_cross_ami"], color=colors, edgecolor="white")
    ax.barh(
        df["pair_name"],
        df["mean_pCrossAMI"],
        color="none",
        edgecolor=[c for c in colors],
        linestyle="--",
        label="pCrossAMI (direct)",
        height=0.4,
    )

    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="#2a7ae2", label="Upstream (positive)"),
        Patch(facecolor="#dc322f", label="Unrelated (negative control)"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9)
    ax.set_xlabel("Mean CrossAMI across horizons (nats)")
    ax.set_title("CrossAMI Driver Ranking — Unstrut @ 978 (target)")
    ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
    fig.tight_layout()
    out_path = _FIG_DIR / "ranking_bar.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    _logger.info("Ranking figure saved → %s", out_path)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------
def _save_tables(summary_records: list[dict], cfg: dict) -> None:
    """Save ranking CSV and per-horizon pivot table.

    Args:
        summary_records: Output of :func:`_run_pair` calls.
        cfg: Parsed YAML config dict.
    """
    ranking_df = (
        pd.DataFrame(summary_records)[
            [
                "pair_name",
                "description",
                "role",
                "n_obs",
                "mean_raw_cross_ami",
                "mean_pCrossAMI",
                "mean_directness_ratio",
                "warning_horizon_count",
            ]
        ]
        .sort_values("mean_raw_cross_ami", ascending=False)
        .reset_index(drop=True)
    )

    ranking_path = _TABLE_DIR / "causal_rivers_ranking.csv"
    ranking_df.to_csv(ranking_path, index=False)
    _logger.info("Ranking table → %s", ranking_path)

    # Pivot: rows = pair, cols = horizon, values = raw CrossAMI
    horizons = cfg["rolling_origin"]["horizons"]
    pivot_rows = []
    for rec in summary_records:
        row = {"pair_name": rec["pair_name"], "role": rec["role"]}
        for h in horizons:
            row[f"h{h}_raw"] = rec["per_horizon_raw"].get(str(h), np.nan)
            row[f"h{h}_partial"] = rec["per_horizon_partial"].get(str(h), np.nan)
        pivot_rows.append(row)

    pivot_df = pd.DataFrame(pivot_rows).sort_values("pair_name")
    pivot_path = _TABLE_DIR / "causal_rivers_horizon_pivot.csv"
    pivot_df.to_csv(pivot_path, index=False)
    _logger.info("Horizon pivot → %s", pivot_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Run the full CausalRivers CrossAMI / pCrossAMI analysis pipeline."""
    t_start = time.time()

    for d in [_FIG_DIR, _JSON_DIR, _TABLE_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    cfg = _load_config()
    ts = _load_and_resample(cfg)
    sel = cfg["station_selection"]

    target_id = sel["target_id"]
    target = _extract_series(ts, target_id)
    _logger.info("Target station %d: %d obs after cleaning", target_id, len(target))

    # Build candidate list: positive upstream + negative controls
    candidates: list[tuple[str, str, int, str]] = []

    meta_path = Path(cfg["data"]["raw_dir"]) / cfg["data"]["meta_file"]
    meta = pd.read_csv(meta_path)

    def _river_name(sid: int) -> str:
        row = meta[meta["ID"] == sid]
        return row["R"].values[0] if len(row) else "?"

    target_river = _river_name(target_id)
    _logger.info("Target river: %s", target_river)

    for sid in sel["positive_upstream"]:
        candidates.append(
            (
                f"pos_{sid}",
                f"Upstream {sid} ({_river_name(sid)} → {target_river} @ {target_id})",
                sid,
                "positive",
            )
        )

    for sid in sel["negative_control"]:
        candidates.append(
            (
                f"neg_{sid}",
                f"Control {sid} ({_river_name(sid)}, unrelated basin)",
                sid,
                "negative",
            )
        )

    summary_records: list[dict] = []

    for pair_name, description, driver_id, role in candidates:
        _logger.info("[%s] %s", pair_name, description)
        try:
            driver = _extract_series(ts, driver_id)
        except KeyError:
            _logger.warning("  Station %d not in time series — skipping", driver_id)
            continue

        rec = _run_pair(pair_name, description, target, driver, cfg, role=role)
        summary_records.append(rec)

        json_path = _JSON_DIR / f"{pair_name}.json"
        with json_path.open("w") as fh:
            import json

            json.dump(rec, fh, indent=2)
        _logger.info("  JSON → %s", json_path)

    # Figures + tables
    _logger.info("Generating figures …")
    _plot_horizon_curves(summary_records, cfg)
    _plot_ranking(summary_records)
    _save_tables(summary_records, cfg)

    # Console summary
    print("\n" + "=" * 72)
    print(f"{'Pair':<22} {'Role':<10} {'CrossAMI':>10} {'pCrossAMI':>10} {'DR':>6}")
    print("-" * 72)
    for rec in sorted(summary_records, key=lambda r: r["mean_raw_cross_ami"], reverse=True):
        print(
            f"{rec['pair_name']:<22} {rec['role']:<10} "
            f"{rec['mean_raw_cross_ami']:>10.4f} {rec['mean_pCrossAMI']:>10.4f} "
            f"{rec['mean_directness_ratio']:>6.2f}"
        )
    print("=" * 72)
    _logger.info("Done in %.1f s", time.time() - t_start)


if __name__ == "__main__":
    main()
