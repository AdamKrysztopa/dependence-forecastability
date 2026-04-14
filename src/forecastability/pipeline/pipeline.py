"""Pipeline orchestration for canonical and benchmark analyses."""

from __future__ import annotations

import numpy as np

from forecastability.diagnostics.cmi import compute_pami_with_backend
from forecastability.diagnostics.surrogates import compute_significance_bands
from forecastability.metrics.metrics import compute_ami, compute_pami_linear_residual
from forecastability.pipeline.analyzer import ForecastabilityAnalyzerExog
from forecastability.use_cases.run_exogenous_rolling_origin_evaluation import (
    run_exogenous_rolling_origin_evaluation as _impl_exog,
)
from forecastability.use_cases.run_rolling_origin_evaluation import (
    run_rolling_origin_evaluation as _impl_rolling,
)
from forecastability.utils.types import (
    CanonicalExampleResult,
    ExogenousBenchmarkResult,
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
            Bands will be ``None``; significant_lags will be ``None``. Useful for
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
        ami_sig: np.ndarray | None = None
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
            backend=pami_backend,
            n_neighbors=n_neighbors,
            random_state=random_state,
        )
    if skip_bands:
        pami_lower: np.ndarray | None = None
        pami_upper: np.ndarray | None = None
        pami_sig: np.ndarray | None = None
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
    return _impl_rolling(
        ts,
        series_id=series_id,
        frequency=frequency,
        horizons=horizons,
        n_origins=n_origins,
        seasonal_period=seasonal_period,
        random_state=random_state,
        include_lightgbm_autoreg=include_lightgbm_autoreg,
        include_nbeats=include_nbeats,
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
    return _impl_exog(
        target,
        exog,
        case_id=case_id,
        target_name=target_name,
        exog_name=exog_name,
        horizons=horizons,
        n_origins=n_origins,
        random_state=random_state,
        n_surrogates=n_surrogates,
        min_pairs_raw=min_pairs_raw,
        min_pairs_partial=min_pairs_partial,
        analysis_scope=analysis_scope,
        project_extension=project_extension,
        _analyzer_cls=ForecastabilityAnalyzerExog,
    )
