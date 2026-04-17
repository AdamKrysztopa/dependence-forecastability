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
    bh_significant: bool = False
    redundancy_score: float | None = None


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
    ami_significance_status: Literal["computed", "not computed"] = "computed"
    pami_significance_status: Literal["computed", "not computed"] = "computed"
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


# ---------------------------------------------------------------------------
# v0.3.0 Covariant result containers (V3-F00)
# ---------------------------------------------------------------------------


LaggedExogConditioningTag = Literal["none", "target_only", "full_mci"]


class CovariantMethodConditioning(BaseModel):
    """Per-method lagged exogenous conditioning semantics for one summary row."""

    model_config = ConfigDict(frozen=True)

    cross_ami: LaggedExogConditioningTag | None = None
    cross_pami: LaggedExogConditioningTag | None = None
    transfer_entropy: LaggedExogConditioningTag | None = None
    gcmi: LaggedExogConditioningTag | None = None
    pcmci: LaggedExogConditioningTag | None = None
    pcmci_ami: LaggedExogConditioningTag | None = None


class CovariantSummaryRow(BaseModel):
    """One row of the unified covariant summary table (V3-F07)."""

    model_config = ConfigDict(frozen=True)

    target: str
    driver: str
    lag: int
    cross_ami: float | None = None
    cross_pami: float | None = None
    transfer_entropy: float | None = None
    gcmi: float | None = None
    pcmci_link: str | None = None  # e.g. "-->" or "o->" from PCMCI+
    pcmci_ami_parent: bool | None = None  # True if selected by PCMCI-AMI
    significance: str | None = None  # e.g. "p<0.01", "above_band"
    rank: int | None = None
    interpretation_tag: str | None = None  # e.g. "direct_driver", "mediated", "spurious"
    lagged_exog_conditioning: CovariantMethodConditioning = Field(
        default_factory=CovariantMethodConditioning
    )


class TransferEntropyResult(BaseModel):
    """Per-pair Transfer Entropy result (V3-F01)."""

    model_config = ConfigDict(frozen=True)

    source: str
    target: str
    lag: int
    te_value: float
    p_value: float | None = None
    significant: bool | None = None
    lagged_exog_conditioning: LaggedExogConditioningTag = "target_only"


class GcmiResult(BaseModel):
    """Per-pair Gaussian Copula MI result (V3-F02)."""

    model_config = ConfigDict(frozen=True)

    source: str
    target: str
    lag: int
    gcmi_value: float
    lagged_exog_conditioning: LaggedExogConditioningTag = "none"


class CausalGraphResult(BaseModel):
    """Graph output from PCMCI+ or PCMCI-AMI-Hybrid (V3-F03 / V3-F04)."""

    model_config = ConfigDict(frozen=True)

    parents: dict[str, list[tuple[str, int]]]  # target → [(source, lag), ...]
    link_matrix: list[list[str]] | None = None  # tigramite-style link summary
    val_matrix: list[list[float]] | None = None  # test statistic matrix
    metadata: dict[str, str | int | float] = Field(default_factory=dict)
    lagged_exog_conditioning: LaggedExogConditioningTag = "full_mci"


class Phase0MiScore(BaseModel):
    """One MI score entry from the Phase 0 AMI triage in PCMCI-AMI-Hybrid (V3-F04).

    Captures the (source, lag, target) triplet and its unconditional MI value.
    Using a dedicated model instead of dict[tuple[str, int, str], float] ensures
    JSON serialisability and stays idiomatic with the project's Pydantic-first
    convention.  (Plan spec listed dict[tuple, float] but tuple dict keys are not
    JSON-serialisable in Pydantic v2.)
    """

    model_config = ConfigDict(frozen=True)

    source: str
    lag: int
    target: str
    mi_value: float


class PcmciAmiResult(BaseModel):
    """Full output from the PCMCI-AMI-Hybrid method (V3-F04)."""

    model_config = ConfigDict(frozen=True)

    causal_graph: CausalGraphResult
    phase0_mi_scores: list[Phase0MiScore]
    phase0_pruned_count: int
    phase0_kept_count: int
    phase1_skeleton: CausalGraphResult
    phase2_final: CausalGraphResult
    ami_threshold: float
    metadata: dict[str, str | int | float] = Field(default_factory=dict)
    lagged_exog_conditioning: LaggedExogConditioningTag = "full_mci"


class CovariantAnalysisBundle(BaseModel):
    """Composite output from the covariant orchestration facade (V3-F06)."""

    model_config = ConfigDict(frozen=True)

    summary_table: list[CovariantSummaryRow]
    te_results: list[TransferEntropyResult] | None = None
    gcmi_results: list[GcmiResult] | None = None
    pcmci_graph: CausalGraphResult | None = None
    pcmci_ami_result: PcmciAmiResult | None = None
    target_name: str
    driver_names: list[str]
    horizons: list[int]
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# v0.3.0 Covariant interpretation result containers (V3-F09)
# ---------------------------------------------------------------------------


CovariantRoleTag = Literal[
    "direct_driver",
    "nonlinear_driver",
    "mediated_driver",
    "redundant",
    "contemporaneous",
    "noise_or_weak",
    "inconclusive",
]


class CovariantDriverRole(BaseModel):
    """Deterministic interpretation of one driver's role toward the target."""

    model_config = ConfigDict(frozen=True)

    driver: str
    role: CovariantRoleTag
    best_lag: int | None
    evidence: list[str]
    methods_supporting: list[str]
    methods_missing: list[str]
    conditioning: CovariantMethodConditioning
    warnings: list[str] = Field(default_factory=list)


class CovariantInterpretationResult(BaseModel):
    """Bundle-level deterministic interpretation of covariant drivers."""

    model_config = ConfigDict(frozen=True)

    target: str
    driver_roles: list[CovariantDriverRole]
    forecastability_class: Literal["high", "medium", "low"]
    directness_class: Literal["high", "medium", "low", "mixed"]
    primary_drivers: list[str]
    modeling_regime: str
    conditioning_disclaimer: str
    warnings: list[str] = Field(default_factory=list)
    schema_version: str = "1"
