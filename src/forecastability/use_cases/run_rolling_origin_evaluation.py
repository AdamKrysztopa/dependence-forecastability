"""Use-case: rolling-origin series evaluation."""

from __future__ import annotations

import numpy as np

from forecastability.metrics import (
    compute_ami_at_horizon,
    compute_pami_at_horizon,
)
from forecastability.models import (
    forecast_ets,
    forecast_lightgbm_autoreg,
    forecast_naive,
    forecast_nbeats,
    forecast_seasonal_naive,
    smape,
)
from forecastability.pipeline.rolling_origin import build_expanding_window_splits
from forecastability.utils.types import ForecastResult, SeriesEvaluationResult

_AMI_MIN_PAIRS = 30
_PAMI_MIN_PAIRS = 50


def _effective_n_origins(*, series_size: int, requested_n_origins: int, horizon: int) -> int | None:
    """Return feasible rolling origins or None when horizon is infeasible."""
    max_feasible_origins = (series_size - 21) // horizon
    if max_feasible_origins < 3:
        return None
    return min(requested_n_origins, max_feasible_origins)


def _min_train_window_size(*, horizon: int) -> int:
    """Return minimum train size needed for strict AMI and pAMI floors."""
    return horizon + _PAMI_MIN_PAIRS + 1


def run_rolling_origin_evaluation(
    ts: np.ndarray,
    *,
    series_id: str,
    frequency: str,
    horizons: list[int],
    n_origins: int,
    seasonal_period: int | None,
    random_state: int,
    include_lightgbm_autoreg: bool = False,
    include_nbeats: bool = False,
) -> SeriesEvaluationResult:
    """Run rolling-origin evaluation for one series.

    Args:
        ts: Univariate time series array.
        series_id: Identifier for the series.
        frequency: Frequency label (e.g. "Monthly").
        horizons: Forecast horizons to evaluate.
        n_origins: Requested number of rolling origins.
        seasonal_period: Seasonal period for seasonal-naive and ETS.
        random_state: Base random seed.
        include_lightgbm_autoreg: Whether to score LightGBM autoreg.
        include_nbeats: Whether to score N-BEATS.

    Returns:
        SeriesEvaluationResult with per-horizon AMI/pAMI and forecast sMAPE.
    """
    ami_by_horizon: dict[int, float] = {}
    pami_by_horizon: dict[int, float] = {}
    naive_smape: dict[int, float] = {}
    snaive_smape: dict[int, float] = {}
    ets_smape: dict[int, float] = {}
    lightgbm_smape: dict[int, float] = {}
    nbeats_smape: dict[int, float] = {}

    for horizon in horizons:
        # Adapt n_origins downward when the series is too short for the
        # requested horizon so short-but-valid series (e.g. M4 Yearly with
        # n≈30–50) are not silently skipped.  Keep at least 3 origins.
        n_origins_eff = _effective_n_origins(
            series_size=len(ts),
            requested_n_origins=n_origins,
            horizon=horizon,
        )
        if n_origins_eff is None:
            continue  # horizon truly infeasible for this series — skip it

        try:
            splits = build_expanding_window_splits(
                ts,
                n_origins=n_origins_eff,
                horizon=horizon,
            )
        except ValueError:
            continue

        min_train_size = _min_train_window_size(horizon=horizon)

        ami_vals: list[float] = []
        pami_vals: list[float] = []
        naive_vals: list[float] = []
        snaive_vals: list[float] = []
        ets_vals: list[float] = []
        lightgbm_vals: list[float] = []
        nbeats_vals: list[float] = []

        for idx, split in enumerate(splits):
            train = split.train
            test = split.test

            if train.size < min_train_size:
                continue

            # Horizon-specific diagnostics are computed on train windows only.
            # Single-horizon helpers avoid computing the full curve when only
            # one horizon value is consumed (PBE-F04).
            ami_val = compute_ami_at_horizon(
                train,
                horizon,
                n_neighbors=8,
                min_pairs=_AMI_MIN_PAIRS,
                random_state=random_state + idx,
            )
            pami_val = compute_pami_at_horizon(
                train,
                horizon,
                n_neighbors=8,
                min_pairs=_PAMI_MIN_PAIRS,
                random_state=random_state + idx,
            )

            ami_vals.append(ami_val)
            pami_vals.append(pami_val)

            # Forecast scoring is computed on post-origin holdout only.
            pred_naive = forecast_naive(train, horizon)
            pred_snaive = forecast_seasonal_naive(
                train,
                horizon,
                seasonal_period=seasonal_period or 1,
            )
            pred_ets = forecast_ets(
                train,
                horizon,
                seasonal_period=seasonal_period,
            )

            naive_vals.append(smape(test, pred_naive))
            snaive_vals.append(smape(test, pred_snaive))
            ets_vals.append(smape(test, pred_ets))
            if include_lightgbm_autoreg:
                pred_lightgbm = forecast_lightgbm_autoreg(train, horizon, n_lags=max(horizon, 12))
                lightgbm_vals.append(smape(test, pred_lightgbm))
            if include_nbeats:
                pred_nbeats = forecast_nbeats(train, horizon, input_size=max(2 * horizon, 24))
                nbeats_vals.append(smape(test, pred_nbeats))

        if not ami_vals:
            continue

        ami_by_horizon[horizon] = float(np.mean(ami_vals))
        pami_by_horizon[horizon] = float(np.mean(pami_vals))
        naive_smape[horizon] = float(np.mean(naive_vals))
        snaive_smape[horizon] = float(np.mean(snaive_vals))
        ets_smape[horizon] = float(np.mean(ets_vals))
        if include_lightgbm_autoreg:
            lightgbm_smape[horizon] = float(np.mean(lightgbm_vals))
        if include_nbeats:
            nbeats_smape[horizon] = float(np.mean(nbeats_vals))

    forecasts = [
        ForecastResult(
            model_name="naive",
            horizons=horizons,
            smape_by_horizon=naive_smape,
        ),
        ForecastResult(
            model_name="seasonal_naive",
            horizons=horizons,
            smape_by_horizon=snaive_smape,
        ),
        ForecastResult(
            model_name="ets",
            horizons=horizons,
            smape_by_horizon=ets_smape,
        ),
    ]
    if include_lightgbm_autoreg:
        forecasts.append(
            ForecastResult(
                model_name="lightgbm_autoreg",
                horizons=horizons,
                smape_by_horizon=lightgbm_smape,
            )
        )
    if include_nbeats:
        forecasts.append(
            ForecastResult(
                model_name="nbeats",
                horizons=horizons,
                smape_by_horizon=nbeats_smape,
            )
        )

    return SeriesEvaluationResult(
        series_id=series_id,
        frequency=frequency,
        ami_by_horizon=ami_by_horizon,
        pami_by_horizon=pami_by_horizon,
        forecast_results=forecasts,
        metadata={
            "n_origins": n_origins,
            "train_only_diagnostics": 1,
            "holdout_only_scoring": 1,
        },
    )
