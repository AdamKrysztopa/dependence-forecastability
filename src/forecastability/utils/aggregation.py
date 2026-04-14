"""Result aggregation and summary descriptors."""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from forecastability.utils.types import (
    CanonicalExampleResult,
    CanonicalSummary,
    SeriesEvaluationResult,
)


def _significance_status(
    significant_lags: np.ndarray | None,
) -> Literal["computed", "not computed"]:
    return "not computed" if significant_lags is None else "computed"


def summarize_canonical_result(
    result: CanonicalExampleResult,
) -> CanonicalSummary:
    """Compute canonical summary descriptors for AMI and pAMI."""
    eps = 1e-12

    ami = result.ami.values
    pami = result.pami.values
    ami_sig_lags = result.ami.significant_lags
    pami_sig_lags = result.pami.significant_lags
    sig_ami = ami_sig_lags if ami_sig_lags is not None else np.array([], dtype=int)
    sig_pami = pami_sig_lags if pami_sig_lags is not None else np.array([], dtype=int)

    auc_ami = float(np.trapezoid(ami))
    auc_pami = float(np.trapezoid(pami))

    return CanonicalSummary(
        series_name=result.series_name,
        n_sig_ami=int(sig_ami.size),
        n_sig_pami=int(sig_pami.size),
        ami_significance_status=_significance_status(ami_sig_lags),
        pami_significance_status=_significance_status(pami_sig_lags),
        peak_lag_ami=int(np.argmax(ami) + 1),
        peak_lag_pami=int(np.argmax(pami) + 1),
        peak_ami=float(np.max(ami)),
        peak_pami=float(np.max(pami)),
        auc_ami=auc_ami,
        auc_pami=auc_pami,
        directness_ratio=float(auc_pami / max(auc_ami, eps)),
        pami_to_ami_sig_ratio=float(sig_pami.size / max(sig_ami.size, 1)),
        first_sig_ami=int(sig_ami[0]) if sig_ami.size else 0,
        first_sig_pami=int(sig_pami[0]) if sig_pami.size else 0,
        last_sig_ami=int(sig_ami[-1]) if sig_ami.size else 0,
        last_sig_pami=int(sig_pami[-1]) if sig_pami.size else 0,
    )


def build_horizon_table(
    results: list[SeriesEvaluationResult],
) -> pd.DataFrame:
    """Build one row per series-horizon-model."""
    rows: list[dict[str, str | int | float]] = []

    for result in results:
        for forecast_result in result.forecast_results:
            for horizon, smape_value in sorted(forecast_result.smape_by_horizon.items()):
                rows.append(
                    {
                        "series_id": result.series_id,
                        "frequency": result.frequency,
                        "model_name": forecast_result.model_name,
                        "horizon": horizon,
                        "ami": result.ami_by_horizon[horizon],
                        "pami": result.pami_by_horizon[horizon],
                        "smape": smape_value,
                    }
                )

    return pd.DataFrame(rows)


def compute_rank_associations(
    table: pd.DataFrame,
) -> pd.DataFrame:
    """Compute Spearman rank correlations by model/horizon."""
    rows: list[dict[str, str | int | float]] = []

    pairs = table[["model_name", "horizon"]].drop_duplicates()
    pairs = pairs.sort_values(["model_name", "horizon"])
    for model_name, horizon in pairs.itertuples(index=False):
        group = table[(table["model_name"] == model_name) & (table["horizon"] == horizon)]
        ami_corr, _ = spearmanr(group["ami"], group["smape"])
        pami_corr, _ = spearmanr(group["pami"], group["smape"])

        rows.append(
            {
                "model_name": model_name,
                "horizon": int(horizon),
                "spearman_ami_smape": float(np.nan_to_num(ami_corr, nan=0.0)),
                "spearman_pami_smape": float(np.nan_to_num(pami_corr, nan=0.0)),
                "delta_pami_minus_ami": float(
                    np.nan_to_num(pami_corr, nan=0.0) - np.nan_to_num(ami_corr, nan=0.0)
                ),
            }
        )

    return pd.DataFrame(rows)


def add_terciles(
    table: pd.DataFrame,
    *,
    metric_col: str,
    output_col: str,
) -> pd.DataFrame:
    """Add within-frequency/horizon terciles for a metric."""
    result = table.copy()

    def _assign(series: pd.Series) -> pd.Series:
        if series.nunique(dropna=True) < 3:
            return pd.Series([pd.NA] * len(series), index=series.index, dtype="object")
        try:
            return pd.qcut(series, 3, labels=["low", "mid", "high"], duplicates="drop")
        except ValueError:
            return pd.Series([pd.NA] * len(series), index=series.index, dtype="object")

    result[output_col] = result.groupby(["frequency", "horizon"])[metric_col].transform(_assign)
    return result


def summarize_terciles(
    table: pd.DataFrame,
    *,
    tercile_col: str,
) -> pd.DataFrame:
    """Summarize median sMAPE by tercile."""
    return (
        table.groupby(["frequency", "model_name", "horizon", tercile_col], dropna=False)["smape"]
        .median()
        .reset_index()
        .rename(columns={"smape": "median_smape"})
    )


def summarize_frequency_panels(table: pd.DataFrame) -> pd.DataFrame:
    """Summarize performance and diagnostics by frequency/model."""
    grouped = (
        table.groupby(["frequency", "model_name"], as_index=False)
        .agg(
            mean_smape=("smape", "mean"),
            mean_ami=("ami", "mean"),
            mean_pami=("pami", "mean"),
        )
        .sort_values(["frequency", "mean_smape"])
    )
    grouped["directness_ratio"] = grouped["mean_pami"] / grouped["mean_ami"].clip(lower=1e-12)
    return grouped
