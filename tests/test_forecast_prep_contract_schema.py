"""Schema and validator tests for v0.3.4 Forecast Prep Contract Phase 0."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from forecastability import (
    CovariateRecommendation,
    FamilyRecommendation,
    ForecastPrepConfidence,
    ForecastPrepContract,
    ForecastPrepContractConfidence,
    ForecastPrepCovariateRole,
    ForecastPrepFamilyTier,
    ForecastPrepLagRole,
    LagRecommendation,
)
from forecastability.triage import ForecastPrepBundle


def test_contract_version_default_is_v034() -> None:
    """Contract version defaults to 0.3.4 for the Phase 0 schema."""
    contract = ForecastPrepContract(
        source_goal="univariate",
        blocked=False,
        readiness_status="ready",
    )

    assert contract.contract_version == "0.3.4"


def test_target_lag_validator_rejects_non_positive_recommended_lags() -> None:
    """recommended_target_lags must contain values >= 1 only."""
    with pytest.raises(ValidationError, match="Target lags must all be >= 1"):
        ForecastPrepContract(
            source_goal="univariate",
            blocked=False,
            readiness_status="ready",
            recommended_target_lags=[1, 0, 3],
        )

    with pytest.raises(ValidationError, match="Target lags must all be >= 1"):
        ForecastPrepContract(
            source_goal="univariate",
            blocked=False,
            readiness_status="ready",
            recommended_target_lags=[-1],
        )


def test_target_lag_validator_rejects_non_positive_excluded_lags() -> None:
    """excluded_target_lags must contain values >= 1 only."""
    with pytest.raises(ValidationError, match="Target lags must all be >= 1"):
        ForecastPrepContract(
            source_goal="univariate",
            blocked=False,
            readiness_status="ready",
            excluded_target_lags=[0],
        )

    with pytest.raises(ValidationError, match="Target lags must all be >= 1"):
        ForecastPrepContract(
            source_goal="univariate",
            blocked=False,
            readiness_status="ready",
            excluded_target_lags=[2, -2],
        )


def test_calendar_feature_prefix_validator_rejects_non_calendar_names() -> None:
    """calendar_features must all use the deterministic _calendar__ prefix."""
    with pytest.raises(ValidationError, match="must start with '_calendar__'"):
        ForecastPrepContract(
            source_goal="univariate",
            blocked=False,
            readiness_status="ready",
            calendar_features=["month"],
        )

    with pytest.raises(ValidationError, match="must start with '_calendar__'"):
        ForecastPrepContract(
            source_goal="univariate",
            blocked=False,
            readiness_status="ready",
            calendar_features=["_calendar__dayofweek", "holiday_flag"],
        )


def test_import_surfaces_resolve_for_phase0_symbols() -> None:
    """Phase 0 symbols should be importable from forecastability and triage APIs."""
    lag_role: ForecastPrepLagRole = "direct"
    cov_role: ForecastPrepCovariateRole = "future"
    confidence: ForecastPrepConfidence = "high"
    family_tier: ForecastPrepFamilyTier = "preferred"
    contract_confidence: ForecastPrepContractConfidence = "abstain"

    lag = LagRecommendation(
        lag=1,
        role=lag_role,
        confidence=confidence,
        selected_for_handoff=True,
        rationale="primary direct lag",
    )
    covariate = CovariateRecommendation(
        name="_calendar__dayofweek",
        role=cov_role,
        confidence=confidence,
        informative=True,
        future_known_required=True,
        selected_lags=[0],
        rationale="deterministic calendar feature",
    )
    family = FamilyRecommendation(
        family="naive",
        tier=family_tier,
        rationale="baseline guardrail",
    )
    contract = ForecastPrepContract(
        source_goal="univariate",
        blocked=False,
        readiness_status="ready",
        confidence_label=contract_confidence,
    )
    bundle = ForecastPrepBundle(
        contract=contract,
        lag_rows=[lag],
        covariate_rows=[covariate],
        family_rows=[family],
    )

    assert lag.role == "direct"
    assert covariate.role == "future"
    assert family.tier == "preferred"
    assert bundle.contract.confidence_label == "abstain"
