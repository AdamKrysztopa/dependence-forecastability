"""Seasonality extraction and primary-lag mapping tests for forecast prep."""

from __future__ import annotations

import numpy as np

from forecastability.services.forecast_prep_mapper import map_target_lag_recommendations
from forecastability.triage.models import (
    AnalysisGoal,
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
    TriageResult,
)
from forecastability.use_cases.build_forecast_prep_contract import build_forecast_prep_contract
from forecastability.utils.types import (
    AmiInformationGeometry,
    Diagnostics,
    FingerprintBundle,
    ForecastabilityFingerprint,
    InterpretationResult,
    RoutingRecommendation,
)


def _fingerprint_bundle(*, structure: str, informative_horizons: list[int]) -> FingerprintBundle:
    """Build a minimal fingerprint bundle for seasonality tests."""
    recommendation = RoutingRecommendation(
        primary_families=["seasonal_naive", "tbats"],
        secondary_families=["arima"],
        rationale=["periodic structure"],
        caution_flags=[],
        confidence_label="high",
    )
    return FingerprintBundle(
        target_name="target",
        geometry=AmiInformationGeometry(
            signal_to_noise=0.4,
            information_horizon=max(informative_horizons, default=0),
            information_structure=structure,  # type: ignore[arg-type]
            informative_horizons=informative_horizons,
            curve=[],
        ),
        fingerprint=ForecastabilityFingerprint(
            information_mass=0.25,
            information_horizon=max(informative_horizons, default=0),
            information_structure=structure,  # type: ignore[arg-type]
            nonlinear_share=0.05,
            signal_to_noise=0.4,
            directness_ratio=0.7,
            informative_horizons=informative_horizons,
        ),
        recommendation=recommendation,
        profile_summary={},
    )


def _triage_result(primary_lags: list[int]) -> TriageResult:
    """Build a minimal non-blocked triage result with provided primary lags."""
    request = TriageRequest(
        series=np.linspace(0.0, 1.0, 120),
        goal=AnalysisGoal.univariate,
        max_lag=30,
        n_surrogates=99,
        random_state=42,
    )
    return TriageResult(
        request=request,
        readiness=ReadinessReport(status=ReadinessStatus.clear, warnings=[]),
        blocked=False,
        interpretation=InterpretationResult(
            forecastability_class="high",
            directness_class="high",
            primary_lags=primary_lags,
            modeling_regime="deterministic triage",
            narrative="seasonality mapping",
            diagnostics=Diagnostics(
                peak_ami_first_5=0.35,
                directness_ratio=0.6,
                n_sig_ami=4,
                n_sig_pami=2,
                exploitability_mismatch=0,
                best_smape=0.1,
            ),
        ),
    )


def test_candidate_periods_can_be_richer_than_recommended_seasonal_lags() -> None:
    """Candidates may contain multiple periods while recommendations stay conservative."""
    fingerprint_bundle = _fingerprint_bundle(
        structure="periodic",
        informative_horizons=[1, 8, 13, 20, 27],
    )

    lag_rows, candidate_periods, recommended_seasonal_lags, _ = map_target_lag_recommendations(
        primary_lags=[1, 7],
        fingerprint_bundle=fingerprint_bundle,
        contract_confidence="high",
    )

    assert candidate_periods == [7, 5]
    assert recommended_seasonal_lags == [7]
    assert any(row.lag == 7 and row.role == "seasonal" for row in lag_rows)


def test_low_confidence_does_not_force_seasonal_recommendation() -> None:
    """Periodic hints should not force seasonal recommendations under low confidence."""
    fingerprint_bundle = _fingerprint_bundle(
        structure="periodic",
        informative_horizons=[1, 8, 15, 22],
    )

    lag_rows, candidate_periods, recommended_seasonal_lags, _ = map_target_lag_recommendations(
        primary_lags=[1, 7],
        fingerprint_bundle=fingerprint_bundle,
        contract_confidence="low",
    )

    assert candidate_periods == [7]
    assert recommended_seasonal_lags == []
    assert all(row.role != "seasonal" for row in lag_rows)


def test_builder_maps_primary_lags_and_seasonality_into_contract_fields() -> None:
    """Builder should place direct and seasonal lags into dedicated contract fields."""
    triage_result = _triage_result(primary_lags=[1, 7, 14])
    fingerprint_bundle = _fingerprint_bundle(
        structure="periodic",
        informative_horizons=[1, 8, 15, 22],
    )

    contract = build_forecast_prep_contract(
        triage_result,
        fingerprint_bundle=fingerprint_bundle,
        routing_recommendation=fingerprint_bundle.recommendation,
        add_calendar_features=False,
    )

    assert 1 in contract.recommended_target_lags
    assert 7 in contract.recommended_seasonal_lags
    assert contract.candidate_seasonal_periods == [7]


def test_seasonality_can_be_empty() -> None:
    """Non-periodic structure or absent fingerprint should yield empty seasonal output."""
    triage_result = _triage_result(primary_lags=[1, 2])
    monotonic_bundle = _fingerprint_bundle(
        structure="monotonic",
        informative_horizons=[1, 2],
    )

    contract_monotonic = build_forecast_prep_contract(
        triage_result,
        fingerprint_bundle=monotonic_bundle,
        routing_recommendation=monotonic_bundle.recommendation,
        add_calendar_features=False,
    )
    assert contract_monotonic.recommended_seasonal_lags == []
    assert contract_monotonic.candidate_seasonal_periods == []

    contract_no_fingerprint = build_forecast_prep_contract(
        triage_result,
        fingerprint_bundle=None,
        routing_recommendation=monotonic_bundle.recommendation,
        add_calendar_features=False,
    )
    assert contract_no_fingerprint.recommended_seasonal_lags == []
    assert contract_no_fingerprint.candidate_seasonal_periods == []
