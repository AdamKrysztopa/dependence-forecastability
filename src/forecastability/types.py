"""Core typed result containers for AMI and pAMI workflows."""

from __future__ import annotations

from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class MetricCurve(BaseModel):
    """Container for a metric curve and significance bands."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    values: np.ndarray
    lower_band: np.ndarray | None = None
    upper_band: np.ndarray | None = None
    significant_lags: np.ndarray | None = None


class CanonicalExampleResult(BaseModel):
    """Result for one canonical example."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    series_name: str
    series: np.ndarray
    ami: MetricCurve
    pami: MetricCurve
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class ForecastResult(BaseModel):
    """Forecast results across horizons."""

    model_config = ConfigDict(frozen=True)

    model_name: str
    horizons: list[int]
    smape_by_horizon: dict[int, float]


class SeriesEvaluationResult(BaseModel):
    """Rolling-origin evaluation result for one series."""

    model_config = ConfigDict(frozen=True)

    series_id: str
    frequency: str
    ami_by_horizon: dict[int, float]
    pami_by_horizon: dict[int, float]
    forecast_results: list[ForecastResult]
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class ExogenousBenchmarkResult(BaseModel):
    """Rolling-origin exogenous benchmark result for one target/exog pair."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    target_name: str
    exog_name: str
    horizons: list[int]
    raw_cross_mi_by_horizon: dict[int, float]
    conditioned_cross_mi_by_horizon: dict[int, float]
    directness_ratio_by_horizon: dict[int, float]
    origins_used_by_horizon: dict[int, int]
    warning_horizons: list[int] = Field(default_factory=list)
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class ExogenousHorizonUsefulnessRow(BaseModel):
    """Per-driver, per-horizon usefulness row for screening ranking."""

    model_config = ConfigDict(frozen=True)

    driver_name: str
    horizon: int
    raw_cross_mi: float
    conditioned_cross_mi: float
    directness_ratio: float
    usefulness_score: float
    horizon_rank: int


class ExogenousLagWindowSummaryRow(BaseModel):
    """Lag-window summary row for one candidate exogenous driver."""

    model_config = ConfigDict(frozen=True)

    driver_name: str
    window_name: str
    start_horizon: int
    end_horizon: int
    n_horizons_covered: int
    mean_usefulness_score: float
    peak_usefulness_score: float


class ExogenousDriverSummary(BaseModel):
    """Screening summary for one exogenous driver."""

    model_config = ConfigDict(frozen=True)

    overall_rank: int
    driver_name: str
    recommendation: Literal["keep", "review", "reject"]
    pruned: bool
    prune_reason: str | None = None
    mean_usefulness_score: float
    peak_usefulness_score: float
    top_horizon: int | None = None
    top_horizon_usefulness_score: float | None = None
    n_horizons_above_floor: int
    warning_horizon_count: int


class ExogenousScreeningWorkbenchResult(BaseModel):
    """Composite result for target-plus-many-drivers exogenous screening."""

    model_config = ConfigDict(frozen=True)

    target_name: str
    horizons: list[int]
    driver_summaries: list[ExogenousDriverSummary]
    horizon_usefulness_rows: list[ExogenousHorizonUsefulnessRow]
    lag_window_summaries: list[ExogenousLagWindowSummaryRow]
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class Diagnostics(BaseModel):
    """Validated diagnostics bundle produced by interpretation."""

    model_config = ConfigDict(frozen=True)

    peak_ami_first_5: float
    directness_ratio: float
    n_sig_ami: int
    n_sig_pami: int
    exploitability_mismatch: int
    best_smape: float


class InterpretationResult(BaseModel):
    """Interpretation result for one series."""

    model_config = ConfigDict(frozen=True)

    forecastability_class: str
    directness_class: str
    primary_lags: list[int]
    modeling_regime: str
    narrative: str
    diagnostics: Diagnostics


class CanonicalSummary(BaseModel):
    """Summary descriptors for one canonical example."""

    model_config = ConfigDict(frozen=True)

    series_name: str
    n_sig_ami: int
    n_sig_pami: int
    peak_lag_ami: int
    peak_lag_pami: int
    peak_ami: float
    peak_pami: float
    auc_ami: float
    auc_pami: float
    directness_ratio: float
    pami_to_ami_sig_ratio: float
    first_sig_ami: int
    first_sig_pami: int
    last_sig_ami: int
    last_sig_pami: int


# ---------------------------------------------------------------------------
# Robustness study result containers
# ---------------------------------------------------------------------------


class BackendComparisonEntry(BaseModel):
    """Comparison of one backend for one series."""

    model_config = ConfigDict(frozen=True)

    backend: str
    n_sig_ami: int
    n_sig_pami: int
    directness_ratio: float
    auc_ami: float
    auc_pami: float
    pami_values: list[float]
    directness_ratio_warning: bool
    auc_pami_delta_vs_linear: float | None = None
    directness_ratio_delta_vs_linear: float | None = None
    n_sig_pami_delta_vs_linear: int | None = None


class BackendComparisonResult(BaseModel):
    """Backend comparison for one series."""

    model_config = ConfigDict(frozen=True)

    series_name: str
    entries: list[BackendComparisonEntry]
    rank_correlation: float
    directness_ratio_range: float
    lag_ranking_stable: bool
    directness_ratio_stable: bool
    warnings: list[str] = Field(default_factory=list)


class SampleSizeStressEntry(BaseModel):
    """Result for one sample-size fraction."""

    model_config = ConfigDict(frozen=True)

    fraction: float
    n_observations: int
    directness_ratio: float
    auc_ami: float
    auc_pami: float
    n_sig_ami: int
    n_sig_pami: int
    directness_ratio_warning: bool


class SampleSizeStressResult(BaseModel):
    """Sample-size stress test for one series."""

    model_config = ConfigDict(frozen=True)

    series_name: str
    entries: list[SampleSizeStressEntry]
    directness_ratio_stable: bool
    warnings: list[str] = Field(default_factory=list)


class RobustnessStudyResult(BaseModel):
    """Full robustness study result."""

    model_config = ConfigDict(frozen=True)

    backend_comparisons: list[BackendComparisonResult]
    sample_size_tests: list[SampleSizeStressResult]
    excluded_series: list[str] = Field(default_factory=list)
    overall_stable: bool
    summary_narrative: str
