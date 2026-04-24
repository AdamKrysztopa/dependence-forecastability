"""Known-future axis tests for the v0.3.4 ForecastPrepContract builder (FPC-F10)."""

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


def _triage_result() -> TriageResult:
    """Build a minimal non-blocked triage result."""
    return TriageResult(
        request=TriageRequest(
            series=np.linspace(0.0, 1.0, 90),
            goal=AnalysisGoal.univariate,
            max_lag=24,
            n_surrogates=99,
            random_state=42,
        ),
        readiness=ReadinessReport(status=ReadinessStatus.clear, warnings=[]),
        blocked=False,
        interpretation=InterpretationResult(
            forecastability_class="high",
            directness_class="high",
            primary_lags=[1, 2],
            modeling_regime="deterministic triage",
            narrative="known-future test",
            diagnostics=Diagnostics(
                peak_ami_first_5=0.3,
                directness_ratio=0.6,
                n_sig_ami=3,
                n_sig_pami=2,
                exploitability_mismatch=0,
                best_smape=0.1,
            ),
        ),
    )


def _routing() -> RoutingRecommendation:
    return RoutingRecommendation(
        primary_families=["arima"],
        secondary_families=[],
        rationale=["test route"],
        caution_flags=[],
        confidence_label="high",
    )


def _bundle_with_rows(
    selected_rows: list[LaggedExogSelectionRow],
    *,
    known_future_drivers: list[str] | None = None,
) -> LaggedExogBundle:
    """Build a minimal lagged-exog bundle for known-future tests."""
    driver_names = sorted({row.driver for row in selected_rows})
    return LaggedExogBundle(
        target_name="target",
        driver_names=driver_names,
        max_lag=8,
        profile_rows=[],
        selected_lags=selected_rows,
        known_future_drivers=known_future_drivers or [],
    )


def test_known_future_driver_takes_precedence_over_past_covariate() -> None:
    """A driver declared known-future must appear only in future_covariates."""
    selected_rows = [
        LaggedExogSelectionRow(
            target="target",
            driver="future_driver",
            lag=2,
            selected_for_tensor=True,
            selector_name="xami_sparse",
            tensor_role="predictive",
        ),
        LaggedExogSelectionRow(
            target="target",
            driver="past_only",
            lag=1,
            selected_for_tensor=True,
            selector_name="xami_sparse",
            tensor_role="predictive",
        ),
    ]
    bundle = _bundle_with_rows(selected_rows, known_future_drivers=["future_driver"])

    contract = build_forecast_prep_contract(
        _triage_result(),
        lagged_exog_bundle=bundle,
        routing_recommendation=_routing(),
        known_future_drivers={"future_driver": True},
        add_calendar_features=False,
    )

    assert "future_driver" in contract.future_covariates
    assert "future_driver" not in contract.past_covariates
    assert "past_only" in contract.past_covariates
    assert set(contract.past_covariates).isdisjoint(set(contract.future_covariates))


def test_known_future_declared_false_stays_as_past_covariate() -> None:
    """A driver with known_future_drivers value=False must NOT move to future axis."""
    selected_rows = [
        LaggedExogSelectionRow(
            target="target",
            driver="maybe_future",
            lag=1,
            selected_for_tensor=True,
            selector_name="xami_sparse",
            tensor_role="predictive",
        ),
    ]
    bundle = _bundle_with_rows(selected_rows)

    contract = build_forecast_prep_contract(
        _triage_result(),
        lagged_exog_bundle=bundle,
        routing_recommendation=_routing(),
        known_future_drivers={"maybe_future": False},
        add_calendar_features=False,
    )

    assert "maybe_future" in contract.past_covariates
    assert "maybe_future" not in contract.future_covariates


def test_future_covariate_lag_zero_only_for_known_future_or_calendar() -> None:
    """validate_covariate_recommendations should reject lag-0 future rows for undeclared names."""
    undeclared_future_row = CovariateRecommendation(
        name="undeclared",
        role="future",
        confidence="medium",
        informative=True,
        future_known_required=True,
        selected_lags=[0],
        rationale="test row with lag=0 for undeclared driver",
    )

    with pytest.raises(ValueError, match="Future lag 0"):
        validate_covariate_recommendations(
            covariate_rows=[undeclared_future_row],
            allowed_zero_future_names=set(),
        )

    # Declared as allowed — no error.
    validate_covariate_recommendations(
        covariate_rows=[undeclared_future_row],
        allowed_zero_future_names={"undeclared"},
    )


def test_covariate_role_requires_explicit_future_known_support() -> None:
    """future_known_required must be True for future rows and False for past rows."""
    selected_rows = [
        LaggedExogSelectionRow(
            target="target",
            driver="past_driver",
            lag=2,
            selected_for_tensor=True,
            selector_name="xami_sparse",
            tensor_role="predictive",
        ),
    ]
    bundle = _bundle_with_rows(
        selected_rows, known_future_drivers=["future_declared"]
    )

    covariate_rows, _ = map_covariate_recommendations(
        lagged_exog_bundle=bundle,
        known_future_driver_names={"future_declared"},
        contract_confidence="high",
    )

    for row in covariate_rows:
        if row.role == "past":
            assert row.future_known_required is False, (
                f"Past covariate {row.name!r} must not claim future_known_required"
            )
        if row.role == "future":
            assert row.future_known_required is True, (
                f"Future covariate {row.name!r} must assert future_known_required"
            )


def test_past_covariate_lags_strictly_positive() -> None:
    """Past-covariate lags must all be >= 1; lag=0 selected row must be rejected."""
    selected_rows = [
        LaggedExogSelectionRow(
            target="target",
            driver="bad",
            lag=0,
            selected_for_tensor=True,
            selector_name="xami_sparse",
            tensor_role="predictive",
        )
    ]
    bundle = _bundle_with_rows(selected_rows)

    with pytest.raises(ValueError, match="lag >= 1"):
        map_covariate_recommendations(
            lagged_exog_bundle=bundle,
            known_future_driver_names=set(),
            contract_confidence="high",
        )


def test_unknown_driver_without_selected_tensor_rows_excluded() -> None:
    """Drivers with no selected_for_tensor rows must not appear in past_covariates."""
    selected_rows = [
        LaggedExogSelectionRow(
            target="target",
            driver="not_selected",
            lag=2,
            selected_for_tensor=False,
            selector_name="xami_sparse",
            tensor_role="predictive",
        ),
    ]
    bundle = _bundle_with_rows(selected_rows)

    contract = build_forecast_prep_contract(
        _triage_result(),
        lagged_exog_bundle=bundle,
        routing_recommendation=_routing(),
        add_calendar_features=False,
    )

    assert "not_selected" not in contract.past_covariates
    assert "not_selected" not in contract.future_covariates
