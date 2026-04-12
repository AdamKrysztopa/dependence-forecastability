"""Configuration objects for AMI and pAMI workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MetricConfig(BaseModel):
    """Configuration for AMI and pAMI estimation.

    Args:
        max_lag: Maximum lag to evaluate.
        n_neighbors: Number of neighbors for kNN MI estimation.
        min_pairs_ami: Minimum valid lagged pairs for AMI.
        min_pairs_pami: Minimum valid lagged pairs for pAMI.
        n_surrogates: Number of surrogates for significance estimation.
        alpha: Significance level.
        random_state: Seed for deterministic execution.
    """

    model_config = ConfigDict(frozen=True)

    max_lag: Annotated[int, Field(ge=1)] = 100
    n_neighbors: Annotated[int, Field(ge=1)] = 8
    min_pairs_ami: Annotated[int, Field(ge=2)] = 30
    min_pairs_pami: Annotated[int, Field(ge=2)] = 50
    n_surrogates: Annotated[int, Field(ge=99)] = 99
    alpha: Annotated[float, Field(gt=0.0, lt=1.0)] = 0.05
    random_state: int = 42


class PaperBaselineConfig(BaseModel):
    """Paper-aligned M4 frequency support and horizon caps.

    Args:
        frequencies: Supported frequency labels from the paper baseline.
        horizon_caps: Maximum evaluated horizon per supported frequency.
    """

    model_config = ConfigDict(frozen=True)

    frequencies: list[str] = Field(
        default_factory=lambda: [
            "Yearly",
            "Quarterly",
            "Monthly",
            "Weekly",
            "Daily",
            "Hourly",
        ]
    )
    horizon_caps: dict[str, Annotated[int, Field(ge=1)]] = Field(
        default_factory=lambda: {
            "Yearly": 6,
            "Quarterly": 8,
            "Monthly": 18,
            "Weekly": 13,
            "Daily": 14,
            "Hourly": 48,
        }
    )

    @field_validator("frequencies")
    @classmethod
    def _frequencies_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("frequencies must be non-empty")
        return v

    @model_validator(mode="after")
    def _validate_alignment(self) -> PaperBaselineConfig:
        if set(self.frequencies) != set(self.horizon_caps):
            raise ValueError("frequencies and horizon_caps must reference the same frequencies")
        return self

    def horizon_cap_for(self, frequency: str) -> int:
        """Return the paper-aligned horizon cap for one frequency."""
        try:
            return self.horizon_caps[self.normalize_frequency(frequency)]
        except KeyError as exc:
            raise ValueError(f"Unsupported paper-baseline frequency: {frequency}") from exc

    def clamp_horizons(self, frequency: str, horizons: list[int]) -> list[int]:
        """Clamp requested horizons to the paper baseline for a frequency."""
        cap = self.horizon_cap_for(frequency)
        return [h for h in horizons if h <= cap]

    def normalize_frequency(self, frequency: str) -> str:
        """Normalize frequency labels to the canonical paper form."""
        folded = {name.casefold(): name for name in self.frequencies}
        try:
            return folded[frequency.casefold()]
        except KeyError as exc:
            raise ValueError(f"Unsupported paper-baseline frequency: {frequency}") from exc


class RollingOriginConfig(BaseModel):
    """Configuration for rolling-origin evaluation.

    Args:
        n_origins: Number of rolling origins.
        horizons: Forecast horizons.
        seasonal_period: Seasonal period if known.
    """

    model_config = ConfigDict(frozen=True)

    n_origins: Annotated[int, Field(ge=2)] = 10
    horizons: list[int] = Field(default_factory=lambda: list(range(1, 19)))
    seasonal_period: Annotated[int, Field(ge=2)] | None = None

    @model_validator(mode="after")
    def _validate_horizons(self) -> RollingOriginConfig:
        if not self.horizons:
            raise ValueError("horizons must be non-empty")
        if any(h < 1 for h in self.horizons):
            raise ValueError("all horizons must be >= 1")
        return self


class OutputConfig(BaseModel):
    """Output locations for artifacts.

    Args:
        figures_dir: Directory for figures.
        tables_dir: Directory for tables.
        json_dir: Directory for JSON outputs.
        reports_dir: Directory for markdown reports.
    """

    model_config = ConfigDict(frozen=True)

    figures_dir: Path
    tables_dir: Path
    json_dir: Path
    reports_dir: Path


class CMIConfig(BaseModel):
    """Configuration for pluggable conditional-MI backends.

    Args:
        backend: Conditional MI backend name.
        rf_estimators: Number of trees for RF residual backend.
        rf_max_depth: Optional max depth for RF residual backend.
        random_state: Seed for deterministic execution.
    """

    model_config = ConfigDict(frozen=True)

    backend: Literal["linear_residual", "rf_residual"] = "linear_residual"
    rf_estimators: Annotated[int, Field(ge=10)] = 200
    rf_max_depth: Annotated[int, Field(ge=2)] | None = 8
    random_state: int = 42


class BenchmarkDataConfig(BaseModel):
    """Configuration for benchmark panel data source.

    Args:
        source: Benchmark panel source kind.
        frequencies: Frequencies to include for M4-backed panel construction.
        n_series_per_frequency: Number of series per frequency.
        m4_cache_dir: Local cache directory for M4 subset files.
        random_state: Seed for deterministic subset selection.
    """

    model_config = ConfigDict(frozen=True)

    source: Literal["synthetic", "m4_subset", "m4_mock"] = "synthetic"
    frequencies: list[str] = Field(default_factory=lambda: ["Monthly"])
    n_series_per_frequency: Annotated[int, Field(ge=1)] = 20
    m4_cache_dir: Path = Path("data/raw/m4")
    random_state: int = 42

    @field_validator("frequencies")
    @classmethod
    def _frequencies_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("frequencies must be non-empty")
        return v


class ModelConfig(BaseModel):
    """Configuration for baseline + optional model integrations.

    Args:
        include_naive: Include naive baseline.
        include_seasonal_naive: Include seasonal naive baseline.
        include_ets: Include ETS baseline.
        include_lightgbm_autoreg: Include optional LightGBM autoregression.
        include_nbeats: Include optional N-BEATS integration.
    """

    model_config = ConfigDict(frozen=True)

    include_naive: bool = True
    include_seasonal_naive: bool = True
    include_ets: bool = True
    include_lightgbm_autoreg: bool = False
    include_nbeats: bool = False


class ExogenousBenchmarkConfig(BaseModel):
    """Configuration for the fixed exogenous benchmark slice workflow.

    Args:
        purpose: Human-readable workflow identifier.
        rolling_origin: Rolling-origin settings for train-only diagnostics.
        metric: Metric settings and surrogate invariants.
        slice_case_ids: Fixed exogenous benchmark cases to evaluate.
        analysis_scope: Whether outputs are descriptive, guidance, or both.
        project_extension: Disclosure flag for non-paper-native workflow.
    """

    model_config = ConfigDict(frozen=True)

    purpose: str = "benchmark_exog_panel"
    rolling_origin: RollingOriginConfig = Field(default_factory=RollingOriginConfig)
    metric: MetricConfig = Field(default_factory=MetricConfig)
    slice_case_ids: list[str] = Field(
        default_factory=lambda: [
            "bike_cnt_temp",
            "bike_cnt_hum",
            "bike_cnt_noise",
            "aapl_spy",
            "aapl_noise",
            "btc_eth",
            "btc_noise",
        ]
    )
    analysis_scope: Literal["descriptive", "guidance", "both"] = "both"
    project_extension: bool = True

    @field_validator("slice_case_ids")
    @classmethod
    def _validate_slice_case_ids(cls, v: list[str]) -> list[str]:
        expected = {
            "bike_cnt_temp",
            "bike_cnt_hum",
            "bike_cnt_noise",
            "aapl_spy",
            "aapl_noise",
            "btc_eth",
            "btc_noise",
        }
        if not v:
            raise ValueError("slice_case_ids must be non-empty")
        if len(v) != len(set(v)):
            raise ValueError("slice_case_ids must be unique")
        if set(v) != expected:
            raise ValueError("slice_case_ids must match the fixed benchmark exogenous slice")
        return v


class ExogenousLagWindowConfig(BaseModel):
    """Configuration for one lag window used in exogenous screening summaries.

    Args:
        name: Stable lag-window identifier.
        start_horizon: Inclusive start horizon.
        end_horizon: Inclusive end horizon.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    start_horizon: Annotated[int, Field(ge=1)]
    end_horizon: Annotated[int, Field(ge=1)]

    @model_validator(mode="after")
    def _validate_window_bounds(self) -> ExogenousLagWindowConfig:
        if self.start_horizon > self.end_horizon:
            raise ValueError("start_horizon must be <= end_horizon")
        return self


class ExogenousScreeningPruningConfig(BaseModel):
    """Optional pruning heuristics for weak exogenous drivers.

    Args:
        enabled: Whether pruning is applied.
        min_mean_usefulness: Minimum mean usefulness score to avoid pruning.
        min_peak_usefulness: Minimum peak usefulness score to avoid pruning.
        horizon_usefulness_floor: Per-horizon usefulness floor for support counts.
        min_horizons_above_floor: Minimum count of horizons above floor.
    """

    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    min_mean_usefulness: Annotated[float, Field(ge=0.0)] = 0.015
    min_peak_usefulness: Annotated[float, Field(ge=0.0)] = 0.025
    horizon_usefulness_floor: Annotated[float, Field(ge=0.0)] = 0.015
    min_horizons_above_floor: Annotated[int, Field(ge=0)] = 2


class ExogenousScreeningRecommendationConfig(BaseModel):
    """Recommendation thresholds for keep/review/reject mapping.

    Args:
        keep_min_mean_usefulness: Mean usefulness threshold for keep.
        keep_min_peak_usefulness: Peak usefulness threshold for keep.
        review_min_mean_usefulness: Mean usefulness threshold for review.
        review_min_peak_usefulness: Peak usefulness threshold for review.
    """

    model_config = ConfigDict(frozen=True)

    keep_min_mean_usefulness: Annotated[float, Field(ge=0.0)] = 0.04
    keep_min_peak_usefulness: Annotated[float, Field(ge=0.0)] = 0.06
    review_min_mean_usefulness: Annotated[float, Field(ge=0.0)] = 0.02
    review_min_peak_usefulness: Annotated[float, Field(ge=0.0)] = 0.04

    @model_validator(mode="after")
    def _validate_threshold_order(self) -> ExogenousScreeningRecommendationConfig:
        if self.keep_min_mean_usefulness < self.review_min_mean_usefulness:
            raise ValueError("keep_min_mean_usefulness must be >= review_min_mean_usefulness")
        if self.keep_min_peak_usefulness < self.review_min_peak_usefulness:
            raise ValueError("keep_min_peak_usefulness must be >= review_min_peak_usefulness")
        return self


class ExogenousScreeningWorkbenchConfig(BaseModel):
    """Configuration for target-plus-many-driver exogenous screening.

    Args:
        purpose: Human-readable workflow identifier.
        horizons: Horizons used for rolling-origin diagnostics and ranking.
        n_origins: Number of rolling origins.
        random_state: Base random seed.
        n_surrogates: Number of surrogates for train-window diagnostics.
        min_pairs_raw: Minimum sample pairs for raw cross-MI.
        min_pairs_partial: Minimum sample pairs for conditioned cross-MI.
        lag_windows: Horizon windows for compact relevance summaries.
        pruning: Optional weak-driver pruning rules.
        recommendation: Keep/review/reject decision thresholds.
        analysis_scope: Descriptive versus guidance scope disclosure.
        project_extension: Disclosure flag for non-paper-native workflow.
    """

    model_config = ConfigDict(frozen=True)

    purpose: str = "exogenous_screening_workbench"
    horizons: list[int] = Field(default_factory=lambda: list(range(1, 13)))
    n_origins: Annotated[int, Field(ge=2)] = 6
    random_state: int = 42
    n_surrogates: Annotated[int, Field(ge=99)] = 99
    min_pairs_raw: Annotated[int, Field(ge=2)] = 30
    min_pairs_partial: Annotated[int, Field(ge=2)] = 50
    lag_windows: list[ExogenousLagWindowConfig] = Field(
        default_factory=lambda: [
            ExogenousLagWindowConfig(name="near_term", start_horizon=1, end_horizon=3),
            ExogenousLagWindowConfig(name="mid_term", start_horizon=4, end_horizon=8),
            ExogenousLagWindowConfig(name="long_term", start_horizon=9, end_horizon=12),
        ]
    )
    pruning: ExogenousScreeningPruningConfig = Field(
        default_factory=ExogenousScreeningPruningConfig
    )
    recommendation: ExogenousScreeningRecommendationConfig = Field(
        default_factory=ExogenousScreeningRecommendationConfig
    )
    analysis_scope: Literal["descriptive", "guidance", "both"] = "guidance"
    project_extension: bool = True

    @field_validator("horizons")
    @classmethod
    def _validate_horizons(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("horizons must be non-empty")
        if any(h < 1 for h in v):
            raise ValueError("all horizons must be >= 1")
        if len(v) != len(set(v)):
            raise ValueError("horizons must be unique")
        return sorted(v)

    @field_validator("lag_windows")
    @classmethod
    def _validate_lag_windows(
        cls, v: list[ExogenousLagWindowConfig]
    ) -> list[ExogenousLagWindowConfig]:
        if not v:
            raise ValueError("lag_windows must be non-empty")
        names = [window.name for window in v]
        if len(names) != len(set(names)):
            raise ValueError("lag_windows names must be unique")
        return v

    @model_validator(mode="after")
    def _validate_horizon_floor(self) -> ExogenousScreeningWorkbenchConfig:
        if self.pruning.min_horizons_above_floor > len(self.horizons):
            raise ValueError("pruning.min_horizons_above_floor cannot exceed number of horizons")
        return self


class UncertaintyConfig(BaseModel):
    """Configuration for bootstrap uncertainty summaries.

    Args:
        n_bootstrap: Number of bootstrap resamples.
        ci_level: Confidence level for intervals.
        random_state: Seed for deterministic execution.
    """

    model_config = ConfigDict(frozen=True)

    n_bootstrap: Annotated[int, Field(ge=50)] = 500
    ci_level: Annotated[float, Field(gt=0.0, lt=1.0)] = 0.95
    random_state: int = 42


class SensitivityConfig(BaseModel):
    """Configuration for AMI/pAMI k-neighbor sensitivity analysis.

    Args:
        k_values: Neighbor values to evaluate.
        random_state: Seed for deterministic execution.
    """

    model_config = ConfigDict(frozen=True)

    k_values: list[int] = Field(default_factory=lambda: [4, 8, 12, 16])
    random_state: int = 42

    @field_validator("k_values")
    @classmethod
    def _k_values_valid(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("k_values must be non-empty")
        if any(k < 1 for k in v):
            raise ValueError("all k_values must be >= 1")
        return v


class RobustnessStudyConfig(BaseModel):
    """Configuration for pAMI robustness study.

    Args:
        backends: pAMI residual backends to compare.
        sample_fractions: Fractions of series length for stress testing.
        max_lag_ami: Maximum lag for AMI curves.
        max_lag_pami: Maximum lag for pAMI curves.
        n_neighbors: Number of neighbors for kNN MI estimation.
        n_surrogates: Number of surrogates for significance estimation.
        alpha: Significance level.
        random_state: Seed for deterministic execution.
        rank_stability_threshold: Spearman rho threshold for lag ranking stability.
        directness_stability_threshold: Max range of directness_ratio for stability.
        min_series_length: Minimum series length to include in study.
    """

    model_config = ConfigDict(frozen=True)

    backends: list[str] = Field(default_factory=lambda: ["linear_residual", "rf_residual"])
    sample_fractions: list[float] = Field(default_factory=lambda: [0.5, 0.75, 1.0])
    max_lag_ami: Annotated[int, Field(ge=1)] = 60
    max_lag_pami: Annotated[int, Field(ge=1)] = 40
    n_neighbors: Annotated[int, Field(ge=1)] = 8
    n_surrogates: Annotated[int, Field(ge=99)] = 99
    alpha: Annotated[float, Field(gt=0.0, lt=1.0)] = 0.05
    random_state: int = 42
    rank_stability_threshold: Annotated[float, Field(ge=0.0, le=1.0)] = 0.8
    directness_stability_threshold: Annotated[float, Field(gt=0.0)] = 0.15
    min_series_length: Annotated[int, Field(ge=10)] = 100

    @field_validator("backends")
    @classmethod
    def _backends_valid(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("backends must contain at least 2 entries")
        return v

    @field_validator("sample_fractions")
    @classmethod
    def _fractions_valid(cls, v: list[float]) -> list[float]:
        if not v:
            raise ValueError("sample_fractions must be non-empty")
        if any(f <= 0.0 or f > 1.0 for f in v):
            raise ValueError("all sample_fractions must be in (0, 1]")
        return v
