"""Pipeline and analyzer orchestration modules."""

from collections.abc import Sequence

import numpy as np

from forecastability.diagnostics.cmi import compute_pami_with_backend
from forecastability.pipeline.analyzer import ForecastabilityAnalyzerExog
from forecastability.utils.types import (
    CanonicalExampleResult,
    ExogenousBenchmarkResult,
    SeriesEvaluationResult,
)


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
    """Compatibility wrapper for canonical pipeline execution."""
    from forecastability.pipeline import pipeline as _pipeline_module

    return _pipeline_module.run_canonical_example(
        series_name,
        ts,
        max_lag_ami=max_lag_ami,
        max_lag_pami=max_lag_pami,
        n_neighbors=n_neighbors,
        n_surrogates=n_surrogates,
        alpha=alpha,
        random_state=random_state,
        pami_backend=pami_backend,
        metadata=metadata,
        skip_bands=skip_bands,
    )


def run_rolling_origin_evaluation(
    ts: np.ndarray,
    *,
    series_id: str,
    frequency: str,
    horizons: Sequence[int],
    n_origins: int,
    seasonal_period: int | None,
    random_state: int,
    include_lightgbm_autoreg: bool = False,
    include_nbeats: bool = False,
) -> SeriesEvaluationResult:
    """Compatibility wrapper for rolling-origin evaluation."""
    from forecastability.pipeline.pipeline import run_rolling_origin_evaluation as _impl

    return _impl(
        ts,
        series_id=series_id,
        frequency=frequency,
        horizons=list(horizons),
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
    horizons: Sequence[int],
    n_origins: int,
    random_state: int,
    n_surrogates: int = 99,
    min_pairs_raw: int = 30,
    min_pairs_partial: int = 50,
    analysis_scope: str = "both",
    project_extension: bool = True,
) -> ExogenousBenchmarkResult:
    """Compatibility wrapper for exogenous rolling-origin evaluation."""
    from forecastability.pipeline import pipeline as _pipeline_module

    return _pipeline_module.run_exogenous_rolling_origin_evaluation(
        target,
        exog,
        case_id=case_id,
        target_name=target_name,
        exog_name=exog_name,
        horizons=list(horizons),
        n_origins=n_origins,
        random_state=random_state,
        n_surrogates=n_surrogates,
        min_pairs_raw=min_pairs_raw,
        min_pairs_partial=min_pairs_partial,
        analysis_scope=analysis_scope,
        project_extension=project_extension,
    )


__all__ = [
    "compute_pami_with_backend",
    "ForecastabilityAnalyzerExog",
    "run_canonical_example",
    "run_exogenous_rolling_origin_evaluation",
    "run_rolling_origin_evaluation",
]
