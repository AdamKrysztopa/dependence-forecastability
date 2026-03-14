"""Pipeline orchestration for canonical and benchmark analyses."""

from __future__ import annotations

import numpy as np

from forecastability.analyzer import ForecastabilityAnalyzerExog
from forecastability.cmi import compute_pami_with_backend
from forecastability.metrics import compute_ami, compute_pami_linear_residual
from forecastability.models import (
    forecast_ets,
    forecast_lightgbm_autoreg,
    forecast_naive,
    forecast_nbeats,
    forecast_seasonal_naive,
    smape,
)
from forecastability.rolling_origin import build_expanding_window_splits
from forecastability.surrogates import compute_significance_bands
from forecastability.types import (
    CanonicalExampleResult,
    ExogenousBenchmarkResult,
    ForecastResult,
    MetricCurve,
    SeriesEvaluationResult,
)


def _significant_lags(values: np.ndarray, upper_band: np.ndarray) -> np.ndarray:
    """Return 1-based significant lag indices."""
    return np.where(values > upper_band)[0] + 1


def run_canonical_example(
    series_name: str,
    ts: np.ndarray,
    *,
    max_lag_ami: int,
    max_lag_pami: int,
    n_neighbors: int,
    n_surrogates: int,
    alpha: float,
    random_state: int,
    pami_backend: str = "linear_residual",
    metadata: dict[str, str | int | float] | None = None,
    skip_bands: bool = False,
) -> CanonicalExampleResult:
    """Run AMI and pAMI analysis for one canonical series.

    Args:
        skip_bands: When True, skip surrogate significance-band computation.
            Bands will be ``None``; significant_lags will be empty.  Useful for
            fast exploratory runs where statistical annotation is not needed.
    """
    ami_values = compute_ami(
        ts,
        max_lag_ami,
        n_neighbors=n_neighbors,
        random_state=random_state,
    )
    if skip_bands:
        ami_lower: np.ndarray | None = None
        ami_upper: np.ndarray | None = None
        ami_sig = np.array([], dtype=int)
    else:
        ami_lower, ami_upper = compute_significance_bands(
            ts,
            metric_name="ami",
            max_lag=max_lag_ami,
            n_surrogates=n_surrogates,
            alpha=alpha,
            n_neighbors=n_neighbors,
            random_state=random_state,
        )
        ami_sig = _significant_lags(ami_values, ami_upper)

    if pami_backend == "linear_residual":
        pami_values = compute_pami_linear_residual(
            ts,
            max_lag_pami,
            n_neighbors=n_neighbors,
            random_state=random_state,
        )
    else:
        pami_values = compute_pami_with_backend(
            ts,
            max_lag_pami,
            backend="rf_residual",
            n_neighbors=n_neighbors,
            random_state=random_state,
        )
    if skip_bands:
        pami_lower: np.ndarray | None = None
        pami_upper: np.ndarray | None = None
        pami_sig = np.array([], dtype=int)
    else:
        pami_lower, pami_upper = compute_significance_bands(
            ts,
            metric_name="pami_linear_residual",
            max_lag=max_lag_pami,
            n_surrogates=n_surrogates,
            alpha=alpha,
            n_neighbors=n_neighbors,
            random_state=random_state,
        )
        pami_sig = _significant_lags(pami_values, pami_upper)

    payload = {} if metadata is None else dict(metadata)
    payload.update(
        {
            "n_samples": len(ts),
            "n_neighbors": n_neighbors,
            "n_surrogates": n_surrogates,
            "alpha": alpha,
            "random_state": random_state,
            "horizon_specific": 1,
            "pami_backend": pami_backend,
        }
    )

    return CanonicalExampleResult(
        series_name=series_name,
        series=np.asarray(ts, dtype=float).reshape(-1),
        ami=MetricCurve(
            values=ami_values,
            lower_band=ami_lower,
            upper_band=ami_upper,
            significant_lags=ami_sig,
        ),
        pami=MetricCurve(
            values=pami_values,
            lower_band=pami_lower,
            upper_band=pami_upper,
            significant_lags=pami_sig,
        ),
        metadata=payload,
    )


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
    """Run rolling-origin evaluation for one series."""
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
        n_series = len(ts)
        n_origins_eff = max(3, min(n_origins, (n_series - 21) // horizon))
        if n_origins_eff < 3:
            continue  # horizon truly infeasible for this series — skip it

        splits = build_expanding_window_splits(
            ts,
            n_origins=n_origins_eff,
            horizon=horizon,
        )

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

            # Horizon-specific diagnostics are computed on train windows only.
            ami_curve = compute_ami(
                train,
                max_lag=horizon,
                n_neighbors=8,
                min_pairs=20,  # kNN k=8 requires at least ~20 pairs for reliable estimates
                random_state=random_state + idx,
            )
            pami_curve = compute_pami_linear_residual(
                train,
                max_lag=horizon,
                n_neighbors=8,
                min_pairs=30,  # kNN k=8 requires at least ~20 pairs for reliable estimates
                random_state=random_state + idx,
            )

            ami_vals.append(float(ami_curve[horizon - 1]))
            pami_vals.append(float(pami_curve[horizon - 1]))

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
    """Run train-only rolling-origin exogenous diagnostics for one pair."""
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
            analyzer = ForecastabilityAnalyzerExog(
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
