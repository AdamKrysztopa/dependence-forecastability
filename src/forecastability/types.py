"""Core typed result containers for AMI and pAMI workflows."""

from __future__ import annotations

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
