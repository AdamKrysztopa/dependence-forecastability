"""Focused covariate-axis tests for forecast-prep contract mapping."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.services.forecast_prep_mapper import (
    map_covariate_recommendations,
    validate_covariate_recommendations,
)
from forecastability.triage.models import (
    AnalysisGoal,
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
    TriageResult,
)
from forecastability.use_cases.build_forecast_prep_contract import build_forecast_prep_contract
from forecastability.utils.types import (
    CovariateRecommendation,
    Diagnostics,
    InterpretationResult,
    LaggedExogBundle,
    LaggedExogSelectionRow,
    RoutingRecommendation,
)


def _make_triage_result() -> TriageResult:
    """Build a minimal non-blocked triage result."""
    request = TriageRequest(
        series=np.linspace(0.0, 1.0, 90),
        goal=AnalysisGoal.univariate,
        max_lag=24,
        n_surrogates=99,
        random_state=42,
    )
    return TriageResult(
        request=request,
        readiness=ReadinessReport(status=ReadinessStatus.clear, warnings=[]),
        blocked=False,
        interpretation=InterpretationResult(
            forecastability_class="medium",
            directness_class="medium",
            primary_lags=[1, 2],
            modeling_regime="deterministic triage",
            narrative="test",
            diagnostics=Diagnostics(
                peak_ami_first_5=0.2,
                directness_ratio=0.4,
                n_sig_ami=2,
                n_sig_pami=1,
                exploitability_mismatch=0,
                best_smape=0.2,
            ),
        ),
    )


def _routing() -> RoutingRecommendation:
    """Build a deterministic routing recommendation fixture."""
    return RoutingRecommendation(
        primary_families=["arima"],
        secondary_families=[],
        rationale=["deterministic route"],
        caution_flags=[],
        confidence_label="high",
    )


def _bundle(
    *,
    selected_rows: list[LaggedExogSelectionRow],
    known_future_drivers: list[str] | None = None,
) -> LaggedExogBundle:
    """Build a minimal lagged-exogenous bundle for mapper tests."""
    driver_names = sorted({row.driver for row in selected_rows})
    return LaggedExogBundle(
        target_name="target",
        driver_names=driver_names,
        max_lag=8,
        profile_rows=[],
        selected_lags=selected_rows,
        known_future_drivers=known_future_drivers or [],
    )


def test_past_covariates_use_selected_for_tensor_positive_lags_only() -> None:
    """Past covariate mapping should use selected rows with lag>=1 only."""
    selected_rows = [
        LaggedExogSelectionRow(
            target="target",
            driver="driver_a",
            lag=2,
            selected_for_tensor=True,
            selector_name="xami_sparse",
            tensor_role="predictive",
        ),
        LaggedExogSelectionRow(
            target="target",
            driver="driver_a",
            lag=3,
            selected_for_tensor=False,
            selector_name="xami_sparse",
            tensor_role="predictive",
        ),
    ]
    bundle = _bundle(selected_rows=selected_rows)

    covariate_rows, _ = map_covariate_recommendations(
        lagged_exog_bundle=bundle,
        known_future_driver_names=set(),
        contract_confidence="high",
    )

    past_rows = [row for row in covariate_rows if row.role == "past"]
    assert len(past_rows) == 1
    assert past_rows[0].name == "driver_a"
    assert past_rows[0].selected_lags == [2]


def test_known_future_precedence_keeps_driver_out_of_past_covariates() -> None:
    """Known-future declarations should take precedence over past mapping."""
    selected_rows = [
        LaggedExogSelectionRow(
            target="target",
            driver="known_driver",
            lag=2,
            selected_for_tensor=True,
            selector_name="xami_sparse",
            tensor_role="predictive",
        ),
        LaggedExogSelectionRow(
            target="target",
            driver="other_driver",
            lag=2,
            selected_for_tensor=True,
            selector_name="xami_sparse",
            tensor_role="predictive",
        ),
    ]
    bundle = _bundle(selected_rows=selected_rows, known_future_drivers=["known_driver"])

    contract = build_forecast_prep_contract(
        _make_triage_result(),
        lagged_exog_bundle=bundle,
        routing_recommendation=_routing(),
        known_future_drivers={"known_driver": True},
        add_calendar_features=False,
    )

    assert "known_driver" in contract.future_covariates
    assert "known_driver" not in contract.past_covariates
    assert set(contract.past_covariates).isdisjoint(set(contract.future_covariates))


def test_selected_tensor_lag_must_be_positive_for_past_covariates() -> None:
    """Defensive validation should reject lag<=0 selected past-covariate rows."""
    selected_rows = [
        LaggedExogSelectionRow(
            target="target",
            driver="bad_driver",
            lag=0,
            selected_for_tensor=True,
            selector_name="xami_sparse",
            tensor_role="predictive",
        )
    ]
    bundle = _bundle(selected_rows=selected_rows)

    with pytest.raises(ValueError, match="lag >= 1"):
        map_covariate_recommendations(
            lagged_exog_bundle=bundle,
            known_future_driver_names=set(),
            contract_confidence="medium",
        )


def test_future_lag_zero_requires_known_future_or_calendar_role() -> None:
    """Lag-0 future rows for undeclared drivers should be rejected."""
    invalid_future_row = CovariateRecommendation(
        name="future_driver_without_contract",
        role="future",
        confidence="low",
        informative=True,
        future_known_required=True,
        selected_lags=[0],
        rationale="invalid test row",
    )

    with pytest.raises(ValueError, match="Future lag 0"):
        validate_covariate_recommendations(
            covariate_rows=[invalid_future_row],
            allowed_zero_future_names=set(),
        )


def test_covariate_role_requires_explicit_future_known_support() -> None:
    """future_known_required must be True only for role='future'; past rows must have False."""
    selected_rows = [
        LaggedExogSelectionRow(
            target="target",
            driver="past_driver",
            lag=1,
            selected_for_tensor=True,
            selector_name="xami_sparse",
            tensor_role="predictive",
        ),
    ]
    bundle = _bundle(
        selected_rows=selected_rows,
        known_future_drivers=["future_declared"],
    )

    contract = build_forecast_prep_contract(
        _make_triage_result(),
        lagged_exog_bundle=bundle,
        routing_recommendation=_routing(),
        known_future_drivers={"future_declared": True},
        add_calendar_features=False,
    )

    assert "past_driver" in contract.past_covariates
    assert "future_declared" in contract.future_covariates

    covariate_rows, _ = map_covariate_recommendations(
        lagged_exog_bundle=bundle,
        known_future_driver_names={"future_declared"},
        contract_confidence="high",
    )
    for row in covariate_rows:
        if row.role == "past":
            assert row.future_known_required is False, (
                f"Past covariate {row.name!r} must have future_known_required=False"
            )
        if row.role == "future":
            assert row.future_known_required is True, (
                f"Future covariate {row.name!r} must have future_known_required=True"
            )
