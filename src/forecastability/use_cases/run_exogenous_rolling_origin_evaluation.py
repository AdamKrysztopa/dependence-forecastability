"""Use-case: rolling-origin exogenous diagnostics evaluation."""

from __future__ import annotations

import numpy as np

from forecastability.metrics.scorers import _mi_scorer
from forecastability.pipeline.rolling_origin import build_expanding_window_splits
from forecastability.services.partial_curve_service import compute_partial_at_horizon
from forecastability.services.raw_curve_service import compute_raw_at_horizon
from forecastability.utils.types import ExogenousBenchmarkResult


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
) -> ExogenousBenchmarkResult:
    """Run train-only rolling-origin exogenous diagnostics for one pair.

    Uses single-horizon helpers to avoid computing a full curve when only one
    horizon value is consumed per rolling origin (PBE-F04).

    Args:
        target: Target time series array.
        exog: Exogenous time series array (must match target shape).
        case_id: Identifier for the experiment case.
        target_name: Human-readable name for the target series.
        exog_name: Human-readable name for the exogenous series.
        horizons: Forecast horizons to evaluate.
        n_origins: Number of rolling origins.
        random_state: Base random seed.
        n_surrogates: Number of surrogates for significance testing (carried
            into result metadata; not used for curve computation).
        min_pairs_raw: Minimum sample pairs for raw MI estimation.
        min_pairs_partial: Minimum sample pairs for partial MI estimation.
        analysis_scope: Scope of analysis ("both", "raw", or "partial").
        project_extension: Whether to project to extension horizons.

    Returns:
        ExogenousBenchmarkResult with per-horizon cross-MI diagnostics.
    """
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
            # Holdout discipline: only exog up to the origin index is used.
            train_exog = exog[: split.origin_index]
            effective_rs = random_state + (1000 * horizon) + idx
            # Single-horizon helpers avoid full-curve computation (PBE-F04).
            raw_val = compute_raw_at_horizon(
                train_target,
                horizon,
                _mi_scorer,
                exog=train_exog,
                min_pairs=min_pairs_raw,
                random_state=effective_rs,
            )
            conditioned_val = compute_partial_at_horizon(
                train_target,
                horizon,
                _mi_scorer,
                exog=train_exog,
                min_pairs=min_pairs_partial,
                random_state=effective_rs,
            )
            raw_vals.append(raw_val)
            conditioned_vals.append(conditioned_val)

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

