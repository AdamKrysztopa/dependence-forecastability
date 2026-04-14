"""Use-case: rolling-origin exogenous diagnostics evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from forecastability.pipeline.analyzer import ForecastabilityAnalyzerExog as _DefaultAnalyzer
from forecastability.pipeline.rolling_origin import build_expanding_window_splits
from forecastability.utils.types import ExogenousBenchmarkResult

if TYPE_CHECKING:
    from forecastability.pipeline.analyzer import ForecastabilityAnalyzerExog


def run_exogenous_rolling_origin_evaluation(
    target: np.ndarray,
    exog: np.ndarray,
    *,
    case_id: str,
    target_name: str,
    exog_name: str,
    horizons: list[int],
    n_origins: int,
    random_state: int,
    n_surrogates: int = 99,
    min_pairs_raw: int = 30,
    min_pairs_partial: int = 50,
    analysis_scope: str = "both",
    project_extension: bool = True,
    _analyzer_cls: type[ForecastabilityAnalyzerExog] | None = None,
) -> ExogenousBenchmarkResult:
    """Run train-only rolling-origin exogenous diagnostics for one pair.

    Args:
        target: Target time series array.
        exog: Exogenous time series array (must match target shape).
        case_id: Identifier for the experiment case.
        target_name: Human-readable name for the target series.
        exog_name: Human-readable name for the exogenous series.
        horizons: Forecast horizons to evaluate.
        n_origins: Number of rolling origins.
        random_state: Base random seed.
        n_surrogates: Number of surrogates for significance testing.
        min_pairs_raw: Minimum sample pairs for raw MI estimation.
        min_pairs_partial: Minimum sample pairs for partial MI estimation.
        analysis_scope: Scope of analysis ("both", "raw", or "partial").
        project_extension: Whether to project to extension horizons.
        _analyzer_cls: Internal injection point for the analyzer class.
            Used by callers (e.g. pipeline.py) to allow monkeypatching.

    Returns:
        ExogenousBenchmarkResult with per-horizon cross-MI diagnostics.
    """
    AnalyzerCls = _analyzer_cls if _analyzer_cls is not None else _DefaultAnalyzer
    if target.shape != exog.shape:
        raise ValueError("target and exog must have matching shape")

    raw_by_horizon: dict[int, float] = {}
    conditioned_by_horizon: dict[int, float] = {}
    directness_by_horizon: dict[int, float] = {}
    origins_used_by_horizon: dict[int, int] = {}
    warning_horizons: list[int] = []

    for horizon in horizons:
        try:
            splits = build_expanding_window_splits(target, n_origins=n_origins, horizon=horizon)
        except ValueError:
            continue

        raw_vals: list[float] = []
        conditioned_vals: list[float] = []
        for idx, split in enumerate(splits):
            train_target = split.train
            train_exog = exog[: split.origin_index]
            analyzer = AnalyzerCls(
                n_surrogates=n_surrogates,
                random_state=random_state + (1000 * horizon) + idx,
            )
            raw_curve = analyzer.compute_raw(
                train_target,
                max_lag=horizon,
                method="mi",
                min_pairs=min_pairs_raw,
                exog=train_exog,
            )
            conditioned_curve = analyzer.compute_partial(
                train_target,
                max_lag=horizon,
                method="mi",
                min_pairs=min_pairs_partial,
                exog=train_exog,
            )
            raw_vals.append(float(raw_curve[horizon - 1]))
            conditioned_vals.append(float(conditioned_curve[horizon - 1]))

        if not raw_vals:
            continue

        mean_raw = float(np.mean(raw_vals))
        mean_conditioned = float(np.mean(conditioned_vals))
        directness_ratio = float(mean_conditioned / max(mean_raw, 1e-12))

        raw_by_horizon[horizon] = mean_raw
        conditioned_by_horizon[horizon] = mean_conditioned
        directness_by_horizon[horizon] = directness_ratio
        origins_used_by_horizon[horizon] = len(raw_vals)
        if directness_ratio > 1.0:
            warning_horizons.append(horizon)

    return ExogenousBenchmarkResult(
        case_id=case_id,
        target_name=target_name,
        exog_name=exog_name,
        horizons=sorted(raw_by_horizon),
        raw_cross_mi_by_horizon=raw_by_horizon,
        conditioned_cross_mi_by_horizon=conditioned_by_horizon,
        directness_ratio_by_horizon=directness_by_horizon,
        origins_used_by_horizon=origins_used_by_horizon,
        warning_horizons=warning_horizons,
        metadata={
            "n_origins": n_origins,
            "n_surrogates": n_surrogates,
            "train_only_diagnostics": 1,
            "holdout_only_scoring": 1,
            "analysis_scope": analysis_scope,
            "project_extension": int(project_extension),
        },
    )
