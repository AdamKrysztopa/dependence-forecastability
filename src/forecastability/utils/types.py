"""Core typed result containers for AMI and pAMI workflows."""

from __future__ import annotations

from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
LagRoleLabel = Literal["instant", "predictive"]
TensorRoleLabel = Literal["diagnostic", "predictive", "known_future"]
LagSelectorLabel = Literal["xcorr_top_k", "xami_sparse"]
LagSignificanceSource = Literal[
    "phase_surrogate_xami",
    "phase_surrogate_xcorr",
    "not_computed",
]


class LaggedExogProfileRow(BaseModel):
    """One lag-domain diagnostic row for a target-driver pair."""

    model_config = ConfigDict(frozen=True)

    target: str
    driver: str
    lag: int
    lag_role: LagRoleLabel
    tensor_role: TensorRoleLabel
    correlation: float | None = None
    cross_ami: float | None = None
    cross_pami: float | None = None
    significance: str | None = None
    significance_source: LagSignificanceSource = "not_computed"
    metadata: dict[str, str | int | float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_significance_consistency(self) -> LaggedExogProfileRow:
        """Enforce consistency between significance and significance_source."""
        if self.significance_source == "not_computed" and self.significance is not None:
            raise ValueError("significance must be None when significance_source is 'not_computed'")
        if self.significance_source != "not_computed" and (
            self.significance is None or self.significance == ""
        ):
            raise ValueError(
                "significance must be non-None and non-empty "
                "when significance_source is not 'not_computed'"
            )
        return self


class LaggedExogSelectionRow(BaseModel):
    """Sparse predictive lag selection row."""

    model_config = ConfigDict(frozen=True)

    target: str
    driver: str
    lag: int
    selected_for_tensor: bool
    selection_order: int | None = None
    selector_name: LagSelectorLabel
    score: float | None = None
    tensor_role: TensorRoleLabel = "predictive"
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class LaggedExogBundle(BaseModel):
    """Composite output from fixed-lag exogenous triage."""

    model_config = ConfigDict(frozen=True)

    target_name: str
    driver_names: list[str]
    max_lag: int
    profile_rows: list[LaggedExogProfileRow]
    selected_lags: list[LaggedExogSelectionRow]
    known_future_drivers: list[str] = Field(default_factory=list)
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


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
    lagged_exog: LaggedExogBundle | None = None
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


# ---------------------------------------------------------------------------
# v0.3.1 Forecastability Fingerprint result containers (V3_1-F00)
# ---------------------------------------------------------------------------

GeometryMethodLabel = Literal["ksg2_shuffle_surrogate"]
FingerprintStructure = Literal["none", "monotonic", "periodic", "mixed"]
RoutingConfidenceLabel = Literal["low", "medium", "high", "abstain"]
ModelFamilyLabel = Literal[
    "naive",
    "seasonal_naive",
    "downscope",
    "arima",
    "ets",
    "linear_state_space",
    "dynamic_regression",
    "harmonic_regression",
    "tbats",
    "seasonal_state_space",
    "tree_on_lags",
    "tcn",
    "nbeats",
    "nhits",
    "nonlinear_tabular",
]
RoutingCautionFlag = Literal[
    "near_threshold",
    "mixed_structure",
    "low_directness",
    "high_nonlinear_share",
    "short_information_horizon",
    "weak_informative_support",
    "signal_conflict",
    "low_signal_to_noise",
    "geometry_threshold_borderline",
    "nonstationarity_risk",
]


class AmiGeometryCurvePoint(BaseModel):
    """One horizon point in the AMI Information Geometry curve."""

    model_config = ConfigDict(frozen=True)

    horizon: int
    ami_raw: float | None = None
    ami_bias: float | None = None
    ami_corrected: float | None = None
    tau: float | None = None
    accepted: bool = False
    valid: bool = True
    caution: str | None = None


class AmiInformationGeometry(BaseModel):
    """Deterministic AMI Information Geometry outputs."""

    model_config = ConfigDict(frozen=True)

    method: GeometryMethodLabel = "ksg2_shuffle_surrogate"
    signal_to_noise: float
    information_horizon: int
    information_structure: FingerprintStructure
    informative_horizons: list[int] = Field(default_factory=list)
    curve: list[AmiGeometryCurvePoint] = Field(default_factory=list)
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class ForecastabilityFingerprint(BaseModel):
    """Compact summary of forecastability profile semantics.

    Attributes:
        information_mass: Normalized masked area under the accepted corrected
            AMI profile. Low = weak forecastability; high = rich predictive
            information over the evaluated horizon grid.
        information_horizon: Latest horizon h still informative under the
            geometry acceptance rule. Zero when no informative horizons exist.
        information_structure: Shape label sourced from the corrected AMI
            profile and geometry classifier.
            One of: none, monotonic, periodic, mixed.
        nonlinear_share: Fraction of accepted corrected AMI in excess of a
            Gaussian-information linear baseline. Zero when no informative
            horizons or when the corrected-AMI denominator is near zero.
        signal_to_noise: Share of corrected AMI that sits meaningfully above
            the surrogate threshold profile.
        directness_ratio: Direct vs. mediated lag structure ratio, kept semantically
            separate from nonlinear_share. None if not computed.
        informative_horizons: List of horizon indices accepted by the geometry mask.
        metadata: Optional key/value annotations for provenance tracking.
    """

    model_config = ConfigDict(frozen=True)

    information_mass: float
    information_horizon: int
    information_structure: FingerprintStructure
    nonlinear_share: float
    signal_to_noise: float
    directness_ratio: float | None = None
    informative_horizons: list[int] = Field(default_factory=list)
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class RoutingRecommendation(BaseModel):
    """Model-family recommendation driven by a forecastability fingerprint.

    Routing is heuristic product guidance derived from deterministic bucket rules.
    It is NOT empirical model selection, a ranking guarantee, or a performance promise.

    Attributes:
        primary_families: Recommended model family labels for this fingerprint pattern.
        secondary_families: Secondary / fallback model families to consider.
        rationale: Human-readable strings explaining routing decisions.
        caution_flags: Flags indicating uncertainty or conflicting signals.
        confidence_label: Deterministic confidence level derived from penalty counts.
            0 penalties -> high; 1 -> medium; 2 or 3 -> low.
        metadata: Optional annotations for policy versioning.
    """

    model_config = ConfigDict(frozen=True)

    primary_families: list[ModelFamilyLabel]
    secondary_families: list[ModelFamilyLabel] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    caution_flags: list[RoutingCautionFlag] = Field(default_factory=list)
    confidence_label: RoutingConfidenceLabel = "medium"
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class FingerprintBundle(BaseModel):
    """Composite output from the forecastability fingerprint use case.

    Attributes:
        target_name: Name of the series being fingerprinted.
        geometry: Deterministic AMI Information Geometry output.
        fingerprint: Compact forecastability fingerprint.
        recommendation: Model-family routing recommendation.
        profile_summary: Scalar summary of the underlying AMI profile.
        metadata: Optional annotations for provenance tracking.
    """

    model_config = ConfigDict(frozen=True)

    target_name: str
    geometry: AmiInformationGeometry
    fingerprint: ForecastabilityFingerprint
    recommendation: RoutingRecommendation
    profile_summary: dict[str, str | int | float]
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# v0.3.3 Routing validation result containers (Phase 0)
# ---------------------------------------------------------------------------


RoutingValidationOutcome = Literal["pass", "fail", "abstain", "downgrade"]
RoutingValidationSourceKind = Literal["synthetic", "real"]


class RoutingPolicyAuditConfig(BaseModel):
    """Versioned scalars for routing validation and confidence calibration."""

    model_config = ConfigDict(frozen=True)

    tau_margin: float = Field(default=0.05, ge=0.0)
    tau_margin_medium: float = Field(default=0.02, ge=0.0)
    tau_stable: float = Field(default=0.80, ge=0.0, le=1.0)
    tau_stable_high: float = Field(default=0.95, ge=0.0, le=1.0)
    tau_stable_medium: float = Field(default=0.75, ge=0.0, le=1.0)
    perturbation_radius: float = Field(default=0.05, gt=0.0)
    coordinate_scales: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_cross_field_ordering(self) -> RoutingPolicyAuditConfig:
        if self.tau_margin_medium > self.tau_margin:
            raise ValueError(
                "tau_margin_medium must be <= tau_margin "
                f"(got {self.tau_margin_medium} > {self.tau_margin})"
            )
        if not (self.tau_stable_medium <= self.tau_stable <= self.tau_stable_high):
            raise ValueError(
                "Expected tau_stable_medium <= tau_stable <= tau_stable_high "
                f"(got {self.tau_stable_medium}, {self.tau_stable}, {self.tau_stable_high})"
            )
        for key, value in self.coordinate_scales.items():
            if value <= 0.0:
                raise ValueError(f"coordinate_scales['{key}'] must be > 0 (got {value})")
        return self


class RoutingValidationCase(BaseModel):
    """One validation case pairing expected and observed routing behavior."""

    model_config = ConfigDict(frozen=True)

    case_name: str
    source_kind: RoutingValidationSourceKind
    expected_primary_families: list[str]
    observed_primary_families: list[str]
    outcome: RoutingValidationOutcome
    confidence_label: RoutingConfidenceLabel
    threshold_margin: float
    rule_stability: float = Field(ge=0.0, le=1.0)
    fingerprint_penalty_count: int = Field(ge=0)
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, str | int | float] = Field(default_factory=dict)

    @field_validator("expected_primary_families")
    @classmethod
    def _validate_expected_primary_families(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("expected_primary_families must be non-empty")
        return value


class RoutingPolicyAudit(BaseModel):
    """Aggregate routing validation counts across a panel."""

    model_config = ConfigDict(frozen=True)

    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    downgraded_cases: int = Field(ge=0)
    abstained_cases: int = Field(ge=0)
    metadata: dict[str, str | int | float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_count_consistency(self) -> RoutingPolicyAudit:
        counted = (
            self.passed_cases + self.failed_cases + self.downgraded_cases + self.abstained_cases
        )
        if counted != self.total_cases:
            raise ValueError(
                "RoutingPolicyAudit counts must sum to total_cases "
                f"(got {counted} != {self.total_cases})"
            )
        return self


class RoutingValidationBundle(BaseModel):
    """Composite typed output for routing-validation orchestration."""

    model_config = ConfigDict(frozen=True)

    cases: list[RoutingValidationCase]
    audit: RoutingPolicyAudit
    config: RoutingPolicyAuditConfig
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# v0.3.4 Forecast Prep Contract result containers (FPC-F00)
# ---------------------------------------------------------------------------


ForecastPrepLagRole = Literal["direct", "seasonal", "secondary", "excluded"]
ForecastPrepCovariateRole = Literal["past", "future", "static", "rejected"]
ForecastPrepConfidence = Literal["low", "medium", "high"]
ForecastPrepFamilyTier = Literal["baseline", "preferred", "fallback"]
ForecastPrepContractConfidence = Literal["high", "medium", "low", "abstain"]


class LagRecommendation(BaseModel):
    """One recommended (or excluded) target lag with rationale."""

    model_config = ConfigDict(frozen=True)

    lag: int = Field(ge=1, description="Strictly positive lag of the target.")
    role: ForecastPrepLagRole
    confidence: ForecastPrepConfidence
    selected_for_handoff: bool
    rationale: str


class CovariateRecommendation(BaseModel):
    """One recommended (or rejected) covariate with role and rationale."""

    model_config = ConfigDict(frozen=True)

    name: str
    role: ForecastPrepCovariateRole
    confidence: ForecastPrepConfidence
    informative: bool
    future_known_required: bool = Field(
        description=(
            "True only when role == 'future'. Indicates the user contractually "
            "guarantees this column is observable for the entire horizon."
        ),
    )
    selected_lags: list[int] = Field(
        default_factory=list,
        description=(
            "For role='past': sparse predictive lags (>= 1). "
            "For role='future': horizon-relative lags (>= 0)."
        ),
    )
    lagged_feature_names: list[str] = Field(
        default_factory=list,
        exclude_if=lambda value: len(value) == 0,
        description=(
            "Deterministic lagged feature identifiers aligned 1:1 with "
            "selected_lags when available."
        ),
    )
    known_future_provenance: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Known-future provenance label when role='future' is backed by an "
            "explicit contractual or calendar guarantee."
        ),
    )
    rationale: str

    @model_validator(mode="after")
    def _validate_role_consistency(self) -> CovariateRecommendation:
        if self.future_known_required and self.role != "future":
            raise ValueError("future_known_required must be False unless role='future'")
        if self.role == "future":
            if any(lag < 0 for lag in self.selected_lags):
                raise ValueError("Future covariate selected_lags must all be >= 0")
        elif any(lag < 1 for lag in self.selected_lags):
            raise ValueError("Non-future covariate selected_lags must all be >= 1")
        if self.known_future_provenance is not None and self.role != "future":
            raise ValueError("known_future_provenance requires role='future'")
        if self.lagged_feature_names and len(self.lagged_feature_names) != len(self.selected_lags):
            raise ValueError("lagged_feature_names must align 1:1 with selected_lags when provided")
        return self


class FamilyRecommendation(BaseModel):
    """One recommended model family with tier and rationale."""

    model_config = ConfigDict(frozen=True)

    family: str
    tier: ForecastPrepFamilyTier
    rationale: str


class ForecastPrepTargetHistoryContext(BaseModel):
    """Target-history novelty context attached to a ForecastPrepContract."""

    model_config = ConfigDict(frozen=True)

    enabled: bool
    target_lags: list[int] = Field(default_factory=list)
    scorer_name: str | None = None
    normalization_strategy: str | None = None
    penalized_selected_features: int = Field(default=0, ge=0)
    max_selected_redundancy: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)


class ForecastPrepContract(BaseModel):
    """Neutral, deterministic, additive hand-off contract for downstream forecasting."""

    model_config = ConfigDict(frozen=True)

    contract_version: str = Field(
        default="0.3.4",
        description=(
            "Schema version for ForecastPrepContract. Additive field changes do "
            "not bump this value."
        ),
    )
    source_goal: Literal["univariate", "covariant", "lagged_exogenous"]
    blocked: bool = Field(
        description="Mirrors TriageResult.blocked. True yields conservative empties.",
    )
    readiness_status: str
    forecastability_class: str | None = None
    confidence_label: ForecastPrepContractConfidence = "medium"
    target_frequency: str | None = None
    horizon: int | None = Field(default=None, ge=1)
    recommended_target_lags: list[int] = Field(default_factory=list)
    recommended_seasonal_lags: list[int] = Field(default_factory=list)
    excluded_target_lags: list[int] = Field(default_factory=list)
    lag_rationale: list[str] = Field(default_factory=list)
    candidate_seasonal_periods: list[int] = Field(default_factory=list)
    recommended_families: list[str] = Field(default_factory=list)
    baseline_families: list[str] = Field(default_factory=list)
    past_covariates: list[str] = Field(default_factory=list)
    future_covariates: list[str] = Field(default_factory=list)
    static_features: list[str] = Field(default_factory=list)
    rejected_covariates: list[str] = Field(default_factory=list)
    covariate_notes: list[str] = Field(default_factory=list)
    covariate_rows: list[CovariateRecommendation] = Field(
        default_factory=list,
        exclude_if=lambda value: len(value) == 0,
        description=(
            "Typed covariate rows used when sparse lag detail is available from "
            "lagged-exogenous or lag-aware covariate selection."
        ),
    )
    transformation_hints: list[str] = Field(default_factory=list)
    caution_flags: list[str] = Field(default_factory=list)
    downstream_notes: list[str] = Field(default_factory=list)
    calendar_features: list[str] = Field(
        default_factory=list,
        description=(
            "Subset of future_covariates auto-generated by the calendar feature "
            "service. Entries must start with '_calendar__'."
        ),
    )
    calendar_locale: str | None = None
    target_history_context: ForecastPrepTargetHistoryContext | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Optional lag-aware target-history novelty context when the contract "
            "was built from Lag-Aware ModMRMR selections."
        ),
    )
    metadata: dict[str, str | int | float] = Field(default_factory=dict)

    @field_validator("recommended_target_lags", "excluded_target_lags")
    @classmethod
    def _strictly_positive_target_lags(cls, value: list[int]) -> list[int]:
        if any(lag < 1 for lag in value):
            raise ValueError("Target lags must all be >= 1.")
        return value

    @field_validator("calendar_features")
    @classmethod
    def _calendar_features_have_prefix(cls, value: list[str]) -> list[str]:
        for feature_name in value:
            if not feature_name.startswith("_calendar__"):
                raise ValueError(
                    f"Calendar feature {feature_name!r} must start with '_calendar__'."
                )
        return value

    @model_validator(mode="after")
    def _validate_covariate_row_name_consistency(self) -> ForecastPrepContract:
        if not self.covariate_rows:
            return self

        past_covariates = sorted({row.name for row in self.covariate_rows if row.role == "past"})
        future_covariates = sorted(
            {row.name for row in self.covariate_rows if row.role == "future"}
        )
        static_features = sorted({row.name for row in self.covariate_rows if row.role == "static"})
        rejected_covariates = sorted(
            {row.name for row in self.covariate_rows if row.role == "rejected"}
        )

        if past_covariates != sorted(self.past_covariates):
            raise ValueError("covariate_rows are inconsistent with past_covariates")
        if future_covariates != sorted(self.future_covariates):
            raise ValueError("covariate_rows are inconsistent with future_covariates")
        if static_features != sorted(self.static_features):
            raise ValueError("covariate_rows are inconsistent with static_features")
        if rejected_covariates != sorted(self.rejected_covariates):
            raise ValueError("covariate_rows are inconsistent with rejected_covariates")
        return self


class ForecastPrepBundle(BaseModel):
    """Richer bundle carrying typed recommendation rows and compact contract."""

    model_config = ConfigDict(frozen=True)

    contract: ForecastPrepContract
    lag_rows: list[LagRecommendation] = Field(default_factory=list)
    covariate_rows: list[CovariateRecommendation] = Field(default_factory=list)
    family_rows: list[FamilyRecommendation] = Field(default_factory=list)
    metadata: dict[str, str | int | float] = Field(default_factory=dict)
