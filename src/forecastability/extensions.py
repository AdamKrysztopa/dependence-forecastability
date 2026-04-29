"""Extension analyses for sensitivity, uncertainty, and target baselines."""

from __future__ import annotations

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from forecastability.pipeline import ForecastabilityAnalyzerExog, run_canonical_example
from forecastability.pipeline.rolling_origin import build_expanding_window_splits
from forecastability.utils.aggregation import summarize_canonical_result
from forecastability.utils.types import CanonicalExampleResult

__all__ = [
    "TargetBaselineCurves",
    "bootstrap_descriptor_uncertainty",
    "compute_k_sensitivity",
    "compute_target_baseline_by_horizon",
]


class TargetBaselineCurves(BaseModel):
    """Target-only train-window baseline curves aggregated by horizon.

    Attributes:
        series_name: Human-readable target series identifier.
        ami_by_horizon: Mean target-only AMI value for each evaluated horizon.
        pami_by_horizon: Mean target-only pAMI value for each evaluated horizon.
    """

    model_config = ConfigDict(frozen=True)

    series_name: str
    ami_by_horizon: dict[int, float]
    pami_by_horizon: dict[int, float]


def compute_k_sensitivity(
    *,
    series_name: str,
    ts: np.ndarray,
    k_values: list[int],
    max_lag_ami: int,
    max_lag_pami: int,
    n_surrogates: int,
    alpha: float,
    random_state: int,
) -> pd.DataFrame:
    """Run canonical AMI/pAMI analysis over a k-neighbor grid.

    Args:
        series_name: Series label carried into the output table.
        ts: Univariate target series.
        k_values: Neighborhood sizes to evaluate.
        max_lag_ami: Maximum AMI horizon.
        max_lag_pami: Maximum pAMI horizon.
        n_surrogates: Number of phase surrogates for significance bands.
        alpha: Two-sided significance level.
        random_state: Deterministic seed.

    Returns:
        Data frame with one row per ``k`` value and summary diagnostics.
    """
    rows: list[dict[str, str | int | float]] = []
    for k in k_values:
        result = run_canonical_example(
            series_name=series_name,
            ts=ts,
            max_lag_ami=max_lag_ami,
            max_lag_pami=max_lag_pami,
            n_neighbors=k,
            n_surrogates=n_surrogates,
            alpha=alpha,
            random_state=random_state,
        )
        summary = summarize_canonical_result(result)
        rows.append(
            {
                "series_name": series_name,
                "k": int(k),
                "n_sig_ami": summary.n_sig_ami,
                "n_sig_pami": summary.n_sig_pami,
                "directness_ratio": summary.directness_ratio,
                "auc_ami": summary.auc_ami,
                "auc_pami": summary.auc_pami,
            }
        )
    return pd.DataFrame(rows)


def compute_target_baseline_by_horizon(
    *,
    series_name: str,
    target: np.ndarray,
    horizons: list[int],
    n_origins: int,
    random_state: int,
    min_pairs_raw: int,
    min_pairs_partial: int,
    n_surrogates: int,
) -> TargetBaselineCurves:
    """Compute target-only rolling-origin baselines by horizon.

    The helper mirrors the train-only discipline of the exogenous rolling-origin
    evaluation, but it evaluates the target series without any exogenous driver.

    Args:
        series_name: Human-readable target series identifier.
        target: Target time series.
        horizons: Forecast horizons to evaluate.
        n_origins: Number of expanding-window origins.
        random_state: Base deterministic seed.
        min_pairs_raw: Minimum sample pairs for AMI estimation.
        min_pairs_partial: Minimum sample pairs for pAMI estimation.
        n_surrogates: Number of surrogate draws carried into the analyzer.

    Returns:
        Frozen target-only AMI and pAMI means keyed by horizon.
    """
    ami_by_horizon: dict[int, float] = {}
    pami_by_horizon: dict[int, float] = {}

    for horizon in horizons:
        try:
            splits = build_expanding_window_splits(target, n_origins=n_origins, horizon=horizon)
        except ValueError:
            continue

        ami_values: list[float] = []
        pami_values: list[float] = []
        for index, split in enumerate(splits):
            analyzer = ForecastabilityAnalyzerExog(
                n_surrogates=n_surrogates,
                random_state=random_state + (1000 * horizon) + index,
            )
            ami_curve = analyzer.compute_raw(
                split.train,
                max_lag=horizon,
                method="mi",
                min_pairs=min_pairs_raw,
                exog=None,
            )
            pami_curve = analyzer.compute_partial(
                split.train,
                max_lag=horizon,
                method="mi",
                min_pairs=min_pairs_partial,
                exog=None,
            )
            ami_values.append(float(ami_curve[horizon - 1]))
            pami_values.append(float(pami_curve[horizon - 1]))

        if ami_values:
            ami_by_horizon[horizon] = float(np.mean(ami_values))
        if pami_values:
            pami_by_horizon[horizon] = float(np.mean(pami_values))

    return TargetBaselineCurves(
        series_name=series_name,
        ami_by_horizon=ami_by_horizon,
        pami_by_horizon=pami_by_horizon,
    )


def bootstrap_descriptor_uncertainty(
    result: CanonicalExampleResult,
    *,
    n_bootstrap: int,
    ci_level: float,
    random_state: int,
) -> pd.DataFrame:
    """Estimate uncertainty intervals for descriptor summaries via bootstrap.

    Args:
        result: Canonical AMI/pAMI analysis result.
        n_bootstrap: Number of bootstrap resamples.
        ci_level: Central confidence interval mass.
        random_state: Deterministic seed.

    Returns:
        Data frame with bootstrap mean and confidence interval bounds.
    """
    if n_bootstrap < 1:
        raise ValueError("n_bootstrap must be >= 1")
    if not 0.0 < ci_level < 1.0:
        raise ValueError("ci_level must be in (0, 1)")

    rng = np.random.default_rng(random_state)
    ami = result.ami.values
    pami = result.pami.values
    n = min(ami.size, pami.size)

    directness_vals = np.empty(n_bootstrap, dtype=float)
    auc_ami_vals = np.empty(n_bootstrap, dtype=float)
    auc_pami_vals = np.empty(n_bootstrap, dtype=float)

    for idx in range(n_bootstrap):
        sample_idx = rng.integers(0, n, size=n)
        ami_s = ami[sample_idx]
        pami_s = pami[sample_idx]
        auc_ami = float(np.trapezoid(ami_s))
        auc_pami = float(np.trapezoid(pami_s))
        directness = auc_pami / max(auc_ami, 1e-12)
        auc_ami_vals[idx] = auc_ami
        auc_pami_vals[idx] = auc_pami
        directness_vals[idx] = directness

    lower_q = 100.0 * (1.0 - ci_level) / 2.0
    upper_q = 100.0 * (1.0 - (1.0 - ci_level) / 2.0)
    rows = [
        {
            "series_name": result.series_name,
            "metric": "auc_ami",
            "mean": float(np.mean(auc_ami_vals)),
            "ci_lower": float(np.percentile(auc_ami_vals, lower_q)),
            "ci_upper": float(np.percentile(auc_ami_vals, upper_q)),
        },
        {
            "series_name": result.series_name,
            "metric": "auc_pami",
            "mean": float(np.mean(auc_pami_vals)),
            "ci_lower": float(np.percentile(auc_pami_vals, lower_q)),
            "ci_upper": float(np.percentile(auc_pami_vals, upper_q)),
        },
        {
            "series_name": result.series_name,
            "metric": "directness_ratio",
            "mean": float(np.mean(directness_vals)),
            "ci_lower": float(np.percentile(directness_vals, lower_q)),
            "ci_upper": float(np.percentile(directness_vals, upper_q)),
        },
    ]
    return pd.DataFrame(rows)
