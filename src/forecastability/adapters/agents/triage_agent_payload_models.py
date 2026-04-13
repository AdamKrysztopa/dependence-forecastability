"""Agent adapter payload models for the AMI → pAMI triage system.

These Pydantic models are the serialisation boundary between triage domain
results and agentic consumers.  All numpy types are converted to plain Python
types before they reach these models.

Payload model classes (F1–F8 + composite) must NOT import domain application
code at module level.  The factory functions at the bottom of this file may
import domain models at call time.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from forecastability.triage.batch_models import BatchTriageItemResult
    from forecastability.triage.complexity_band import ComplexityBandResult
    from forecastability.triage.forecastability_profile import ForecastabilityProfile
    from forecastability.triage.lyapunov import LargestLyapunovExponentResult
    from forecastability.triage.models import TriageResult
    from forecastability.triage.predictive_info_learning_curve import PredictiveInfoLearningCurve
    from forecastability.triage.spectral_predictability import SpectralPredictabilityResult
    from forecastability.triage.theoretical_limit_diagnostics import TheoreticalLimitDiagnostics
    from forecastability.types import ExogenousDriverSummary


# ---------------------------------------------------------------------------
# F1 — Forecastability Profile Payload
# ---------------------------------------------------------------------------


class F1ProfilePayload(BaseModel):
    """Agent-serialisable payload for F1 forecastability profile.

    Attributes:
        schema_version: Payload schema version string.
        peak_horizon: Horizon at which the AMI curve is maximised.
        informative_horizons: Horizons where AMI ≥ epsilon.
        profile_shape_label: Shape classification for the AMI curve.
        profile_summary: One-sentence human-readable description.
        model_now: Immediate modeling-decision recommendation.
        review_horizons: Horizons warranting modeling review.
        avoid_horizons: Non-informative horizons to exclude from models.
        epsilon: Significance threshold used for horizon classification.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    peak_horizon: int
    informative_horizons: list[int]
    profile_shape_label: str
    profile_summary: str
    model_now: str
    review_horizons: list[int]
    avoid_horizons: list[int]
    epsilon: float


# ---------------------------------------------------------------------------
# F2 — Theoretical Limit Diagnostics Payload
# ---------------------------------------------------------------------------


class F2LimitsPayload(BaseModel):
    """Agent-serialisable payload for F2 theoretical limit diagnostics.

    Attributes:
        schema_version: Payload schema version string.
        theoretical_ceiling_by_horizon: MI ceiling as a plain float list.
        ceiling_summary: One-sentence ceiling summary.
        compression_warning: Destructive-transform warning or None.
        dpi_warning: Data-processing-inequality warning or None.
        exploitation_ratio_supported: Whether exploitation ratio is available.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    theoretical_ceiling_by_horizon: list[float]
    ceiling_summary: str
    compression_warning: str | None
    dpi_warning: str | None
    exploitation_ratio_supported: bool


# ---------------------------------------------------------------------------
# F3 — Predictive Info Learning Curve Payload
# ---------------------------------------------------------------------------


class F3LearningCurvePayload(BaseModel):
    """Agent-serialisable payload for F3 predictive-info learning curve.

    Attributes:
        schema_version: Payload schema version string.
        recommended_lookback: Recommended lookback length.
        plateau_detected: Whether a convergence plateau was found.
        reliability_warnings: List of reliability warning strings.
        lookback_summary: Human-readable recommended-lookback sentence.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    recommended_lookback: int
    plateau_detected: bool
    reliability_warnings: list[str]
    lookback_summary: str


# ---------------------------------------------------------------------------
# F4 — Spectral Predictability Payload
# ---------------------------------------------------------------------------


class F4SpectralPayload(BaseModel):
    """Agent-serialisable payload for F4 spectral predictability.

    Attributes:
        schema_version: Payload schema version string.
        spectral_predictability_score: Spectral predictability Ω ∈ [0, 1].
        spectral_summary: One-sentence human-readable explanation.
        spectral_reliability_notes: Note about Welch PSD assumptions.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    spectral_predictability_score: float
    spectral_summary: str
    spectral_reliability_notes: str


# ---------------------------------------------------------------------------
# F5 — Largest Lyapunov Exponent Payload
# ---------------------------------------------------------------------------


class F5LyapunovPayload(BaseModel):
    """Agent-serialisable payload for F5 largest Lyapunov exponent.

    This result is experimental and must not be used as the sole
    triage decision-maker.  ``is_experimental`` is permanently True.

    Attributes:
        schema_version: Payload schema version string.
        lyapunov_estimate: Estimated LLE value; NaN encoded as None.
        lyapunov_interpretation: Human-readable characterisation.
        lyapunov_warning: Mandatory reliability caution text.
        experimental_flag_required: Mirrors is_experimental from domain.
        is_experimental: Always True; signals experimental status.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    lyapunov_estimate: float | None
    lyapunov_interpretation: str
    lyapunov_warning: str
    experimental_flag_required: bool
    is_experimental: bool = True


# ---------------------------------------------------------------------------
# F6 — Complexity Band Payload
# ---------------------------------------------------------------------------


class F6ComplexityPayload(BaseModel):
    """Agent-serialisable payload for F6 complexity band.

    Attributes:
        schema_version: Payload schema version string.
        permutation_entropy: Normalised permutation entropy ∈ [0, 1].
        spectral_entropy: Normalised spectral entropy ∈ [0, 1].
        complexity_band: Band label: "low", "medium", or "high".
        complexity_summary: Human-readable band explanation.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    permutation_entropy: float
    spectral_entropy: float
    complexity_band: str
    complexity_summary: str


# ---------------------------------------------------------------------------
# F7 — Batch Triage Rank Payload (per-series)
# ---------------------------------------------------------------------------


class F7BatchRankPayload(BaseModel):
    """Agent-serialisable payload for one F7 batch triage result.

    Attributes:
        schema_version: Payload schema version string.
        series_id: Series identifier.
        batch_rank: 1-based rank; None when outcome is not "ok".
        outcome: Outcome label: "ok", "blocked", or "failed".
        forecastability_class: Class label when available.
        directness_class: Directness label when available.
        directness_ratio: pAMI/AMI ratio when available.
        complexity_band: Complexity band label when available.
        spectral_predictability: Spectral score when available.
        diagnostic_vector: Flat dict of all numeric diagnostics.
        ranking_summary: Human-readable one-line ranking summary.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    series_id: str
    batch_rank: int | None
    outcome: str
    forecastability_class: str | None
    directness_class: str | None
    directness_ratio: float | None
    complexity_band: str | None
    spectral_predictability: float | None
    diagnostic_vector: dict[str, float | None]
    ranking_summary: str


# ---------------------------------------------------------------------------
# F8 — Exogenous Driver Payload (per-driver)
# ---------------------------------------------------------------------------


class F8ExogDriverPayload(BaseModel):
    """Agent-serialisable payload for one F8 exogenous driver screening result.

    Attributes:
        schema_version: Payload schema version string.
        driver_name: Exogenous driver identifier.
        driver_rank: Overall screening rank.
        recommendation: Screening recommendation: "keep", "review", or "reject".
        mean_usefulness_score: Mean usefulness score across horizons.
        peak_usefulness_score: Peak usefulness score across horizons.
        driver_scores_summary: ``[mean_usefulness_score, peak_usefulness_score]`` summary
            pair.  Per-horizon breakdown is not available in the domain summary model;
            obtain per-horizon rows from ``ExogenousScreeningWorkbenchResult`` directly.
        redundancy_flag: True when redundancy_score > 0.1.
        driver_recommendation_summary: Human-readable one-line recommendation.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    driver_name: str
    driver_rank: int
    recommendation: str
    mean_usefulness_score: float
    peak_usefulness_score: float
    driver_scores_summary: list[float]
    redundancy_flag: bool
    driver_recommendation_summary: str


# ---------------------------------------------------------------------------
# Top-level composite payload
# ---------------------------------------------------------------------------


class TriageAgentPayload(BaseModel):
    """Top-level composite payload for agentic triage consumers.

    Attributes:
        schema_version: Payload schema version string.
        series_id: Optional identifier for the target series.
        blocked: True when the readiness gate blocked further analysis.
        readiness_status: Overall readiness label.
        forecastability_class: Class label from interpretation, when available.
        directness_class: Directness label from interpretation, when available.
        modeling_regime: Modeling regime from interpretation, when available.
        recommendation: Human-readable triage recommendation.
        f1_profile: F1 forecastability profile payload, when available.
        f2_limits: F2 theoretical limit diagnostics payload, when available.
        f3_learning_curve: F3 learning curve payload, when available.
        f4_spectral: F4 spectral predictability payload, when available.
        f5_lyapunov: F5 Lyapunov exponent payload, when available.
        f6_complexity: F6 complexity band payload, when available.
        warnings: Collected readiness and diagnostic warning strings.
        experimental_notes: Notes for experimental diagnostics (LLE).
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    series_id: str | None
    blocked: bool
    readiness_status: str
    forecastability_class: str | None
    directness_class: str | None
    modeling_regime: str | None
    recommendation: str | None
    f1_profile: F1ProfilePayload | None
    f2_limits: F2LimitsPayload | None
    f3_learning_curve: F3LearningCurvePayload | None
    f4_spectral: F4SpectralPayload | None
    f5_lyapunov: F5LyapunovPayload | None
    f6_complexity: F6ComplexityPayload | None
    warnings: list[str]
    experimental_notes: list[str]


# ---------------------------------------------------------------------------
# Factory functions — runtime imports of domain models are permitted here
# ---------------------------------------------------------------------------


def _profile_shape_label(values_list: list[float], *, is_non_monotone: bool, epsilon: float) -> str:
    """Derive profile shape label from domain curve attributes.

    Args:
        values_list: Raw AMI values as a Python float list.
        is_non_monotone: Whether the curve increases after the first element.
        epsilon: Significance threshold.

    Returns:
        One of ``"non_monotone"``, ``"flat"``, or ``"monotone_decay"``.
    """
    if is_non_monotone:
        return "non_monotone"
    if all(v < epsilon for v in values_list):
        return "flat"
    return "monotone_decay"


def f1_profile_payload(profile: ForecastabilityProfile) -> F1ProfilePayload:
    """Convert a domain ForecastabilityProfile to an F1ProfilePayload.

    Args:
        profile: Domain forecastability profile.

    Returns:
        F1ProfilePayload ready for JSON serialisation.
    """
    from forecastability.triage.forecastability_profile import (
        ForecastabilityProfile as _,  # noqa: F401
    )

    values_list: list[float] = profile.values.tolist()
    shape_label = _profile_shape_label(
        values_list,
        is_non_monotone=profile.is_non_monotone,
        epsilon=profile.epsilon,
    )
    return F1ProfilePayload(
        peak_horizon=profile.peak_horizon,
        informative_horizons=profile.informative_horizons,
        profile_shape_label=shape_label,
        profile_summary=profile.summary,
        model_now=profile.model_now,
        review_horizons=profile.review_horizons,
        avoid_horizons=profile.avoid_horizons,
        epsilon=profile.epsilon,
    )


def f2_limits_payload(diagnostics: TheoreticalLimitDiagnostics) -> F2LimitsPayload:
    """Convert domain TheoreticalLimitDiagnostics to an F2LimitsPayload.

    Args:
        diagnostics: Domain theoretical limit diagnostics.

    Returns:
        F2LimitsPayload ready for JSON serialisation.
    """
    return F2LimitsPayload(
        theoretical_ceiling_by_horizon=diagnostics.forecastability_ceiling_by_horizon.tolist(),
        ceiling_summary=diagnostics.ceiling_summary,
        compression_warning=diagnostics.compression_warning,
        dpi_warning=diagnostics.dpi_warning,
        exploitation_ratio_supported=diagnostics.exploitation_ratio_supported,
    )


def f3_learning_curve_payload(curve: PredictiveInfoLearningCurve) -> F3LearningCurvePayload:
    """Convert domain PredictiveInfoLearningCurve to an F3LearningCurvePayload.

    Args:
        curve: Domain predictive info learning curve.

    Returns:
        F3LearningCurvePayload ready for JSON serialisation.
    """
    return F3LearningCurvePayload(
        recommended_lookback=curve.recommended_lookback,
        plateau_detected=curve.plateau_detected,
        reliability_warnings=list(curve.reliability_warnings),
        lookback_summary=f"Recommended lookback: {curve.recommended_lookback} steps",
    )


def f4_spectral_payload(result: SpectralPredictabilityResult) -> F4SpectralPayload:
    """Convert domain SpectralPredictabilityResult to an F4SpectralPayload.

    Args:
        result: Domain spectral predictability result.

    Returns:
        F4SpectralPayload ready for JSON serialisation.
    """
    if result.n_bins < 32:
        reliability_notes = "Welch PSD used fewer than 32 bins; interpret score with caution."
    else:
        reliability_notes = "Welch PSD applied with standard parameters."
    return F4SpectralPayload(
        spectral_predictability_score=result.score,
        spectral_summary=result.interpretation,
        spectral_reliability_notes=reliability_notes,
    )


def f5_lyapunov_payload(result: LargestLyapunovExponentResult) -> F5LyapunovPayload:
    """Convert domain LargestLyapunovExponentResult to an F5LyapunovPayload.

    NaN lambda values are converted to None for JSON safety.

    Args:
        result: Domain LLE result.

    Returns:
        F5LyapunovPayload with is_experimental always True.
    """
    safe_estimate: float | None = (
        None if math.isnan(result.lambda_estimate) else result.lambda_estimate
    )
    return F5LyapunovPayload(
        lyapunov_estimate=safe_estimate,
        lyapunov_interpretation=result.interpretation,
        lyapunov_warning=result.reliability_warning,
        experimental_flag_required=result.is_experimental,
    )


def f6_complexity_payload(result: ComplexityBandResult) -> F6ComplexityPayload:
    """Convert domain ComplexityBandResult to an F6ComplexityPayload.

    Args:
        result: Domain complexity band result.

    Returns:
        F6ComplexityPayload ready for JSON serialisation.
    """
    return F6ComplexityPayload(
        permutation_entropy=result.permutation_entropy,
        spectral_entropy=result.spectral_entropy,
        complexity_band=result.complexity_band,
        complexity_summary=result.interpretation,
    )


def f7_batch_rank_payload(item: BatchTriageItemResult) -> F7BatchRankPayload:
    """Convert a domain BatchTriageItemResult to an F7BatchRankPayload.

    Args:
        item: Domain per-series batch triage result.

    Returns:
        F7BatchRankPayload ready for JSON serialisation.
    """
    diagnostic_vector: dict[str, float | None] = {
        "spectral_predictability": item.spectral_predictability,
        "permutation_entropy": item.permutation_entropy,
        "directness_ratio": item.directness_ratio,
    }
    fc = item.forecastability_class or "unknown"
    ranking_summary = f"Rank {item.rank}: {item.series_id} — {fc}, {item.outcome}"
    return F7BatchRankPayload(
        series_id=item.series_id,
        batch_rank=item.rank,
        outcome=item.outcome,
        forecastability_class=item.forecastability_class,
        directness_class=item.directness_class,
        directness_ratio=item.directness_ratio,
        complexity_band=item.complexity_band_label,
        spectral_predictability=item.spectral_predictability,
        diagnostic_vector=diagnostic_vector,
        ranking_summary=ranking_summary,
    )


def f8_exog_driver_payload(summary: ExogenousDriverSummary) -> F8ExogDriverPayload:
    """Convert a domain ExogenousDriverSummary to an F8ExogDriverPayload.

    Args:
        summary: Domain exogenous driver summary.

    Returns:
        F8ExogDriverPayload ready for JSON serialisation.
    """
    redundancy_flag = summary.redundancy_score is not None and summary.redundancy_score > 0.1
    recommendation_summary = (
        f"Driver '{summary.driver_name}' — {summary.recommendation}: "
        f"mean_usefulness={summary.mean_usefulness_score:.3f}"
    )
    return F8ExogDriverPayload(
        driver_name=summary.driver_name,
        driver_rank=summary.overall_rank,
        recommendation=summary.recommendation,
        mean_usefulness_score=summary.mean_usefulness_score,
        peak_usefulness_score=summary.peak_usefulness_score,
        driver_scores_summary=[summary.mean_usefulness_score, summary.peak_usefulness_score],
        redundancy_flag=redundancy_flag,
        driver_recommendation_summary=recommendation_summary,
    )


def triage_agent_payload(
    result: TriageResult, *, series_id: str | None = None
) -> TriageAgentPayload:
    """Convert a domain TriageResult into a TriageAgentPayload.

    Args:
        result: Full domain triage result.
        series_id: Optional stable identifier for the target series.

    Returns:
        TriageAgentPayload ready for JSON serialisation.
    """
    readiness_status = result.readiness.status.value
    warnings: list[str] = [w.message for w in result.readiness.warnings]
    experimental_notes: list[str] = []

    forecastability_class: str | None = None
    directness_class: str | None = None
    modeling_regime: str | None = None
    if result.interpretation is not None:
        forecastability_class = result.interpretation.forecastability_class
        directness_class = result.interpretation.directness_class
        modeling_regime = result.interpretation.modeling_regime

    f1: F1ProfilePayload | None = None
    if result.forecastability_profile is not None:
        f1 = f1_profile_payload(result.forecastability_profile)

    f2: F2LimitsPayload | None = None
    if result.theoretical_limit_diagnostics is not None:
        f2 = f2_limits_payload(result.theoretical_limit_diagnostics)

    f5: F5LyapunovPayload | None = None
    if result.largest_lyapunov_exponent is not None:
        lle = result.largest_lyapunov_exponent
        f5 = f5_lyapunov_payload(lle)
        if lle.reliability_warning:
            experimental_notes.append(lle.reliability_warning)

    f6: F6ComplexityPayload | None = None
    if result.complexity_band is not None:
        f6 = f6_complexity_payload(result.complexity_band)
        if result.complexity_band.pe_reliability_warning is not None:
            warnings.append(result.complexity_band.pe_reliability_warning)

    return TriageAgentPayload(
        series_id=series_id,
        blocked=result.blocked,
        readiness_status=readiness_status,
        forecastability_class=forecastability_class,
        directness_class=directness_class,
        modeling_regime=modeling_regime,
        recommendation=result.recommendation,
        f1_profile=f1,
        f2_limits=f2,
        f3_learning_curve=None,
        f4_spectral=None,
        f5_lyapunov=f5,
        f6_complexity=f6,
        warnings=warnings,
        experimental_notes=experimental_notes,
    )
