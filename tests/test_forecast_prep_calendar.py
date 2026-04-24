"""Calendar axis tests for the v0.3.4 ForecastPrepContract builder (FPC-F10)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forecastability.services import calendar_feature_service
from forecastability.triage.models import (
    AnalysisGoal,
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
    TriageResult,
)
from forecastability.use_cases.build_forecast_prep_contract import build_forecast_prep_contract
from forecastability.utils.types import Diagnostics, InterpretationResult, RoutingRecommendation

_DAILY_INDEX = pd.date_range("2024-01-01", periods=30, freq="D")

_EXPECTED_DEFAULT_COLUMNS = {
    "_calendar__dayofweek",
    "_calendar__month",
    "_calendar__quarter",
    "_calendar__is_weekend",
    "_calendar__is_business_day",
}


def _triage_result() -> TriageResult:
    """Build a minimal non-blocked triage result for calendar axis tests."""
    return TriageResult(
        request=TriageRequest(
            series=np.linspace(0.0, 1.0, 30),
            goal=AnalysisGoal.univariate,
            max_lag=12,
            n_surrogates=99,
            random_state=42,
        ),
        readiness=ReadinessReport(status=ReadinessStatus.clear, warnings=[]),
        blocked=False,
        interpretation=InterpretationResult(
            forecastability_class="medium",
            directness_class="medium",
            primary_lags=[1],
            modeling_regime="deterministic triage",
            narrative="calendar test",
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
    return RoutingRecommendation(
        primary_families=["arima"],
        secondary_families=[],
        rationale=["test"],
        caution_flags=[],
        confidence_label="high",
    )


def test_calendar_features_use_underscore_calendar_prefix() -> None:
    """All auto-generated calendar features must start with '_calendar__'."""
    contract = build_forecast_prep_contract(
        _triage_result(),
        routing_recommendation=_routing(),
        add_calendar_features=True,
        datetime_index=_DAILY_INDEX,
    )

    for feature in contract.calendar_features:
        assert feature.startswith("_calendar__"), (
            f"Calendar feature {feature!r} does not start with '_calendar__'"
        )


def test_calendar_features_default_columns_present() -> None:
    """Default (no locale) calendar features must include all five mandatory columns."""
    contract = build_forecast_prep_contract(
        _triage_result(),
        routing_recommendation=_routing(),
        add_calendar_features=True,
        calendar_locale=None,
        datetime_index=_DAILY_INDEX,
    )

    assert _EXPECTED_DEFAULT_COLUMNS.issubset(set(contract.calendar_features)), (
        f"Missing calendar columns. Present: {contract.calendar_features}"
    )


def test_calendar_locale_unset_does_not_emit_holiday_column() -> None:
    """Without locale set, _calendar__is_holiday must not appear."""
    contract = build_forecast_prep_contract(
        _triage_result(),
        routing_recommendation=_routing(),
        add_calendar_features=True,
        calendar_locale=None,
        datetime_index=_DAILY_INDEX,
    )

    assert "_calendar__is_holiday" not in contract.calendar_features


def test_calendar_locale_set_without_holidays_emits_caution_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setting locale without holidays package triggers a specific caution flag."""
    monkeypatch.setattr(calendar_feature_service, "_HOLIDAYS_AVAILABLE", False)

    contract = build_forecast_prep_contract(
        _triage_result(),
        routing_recommendation=_routing(),
        add_calendar_features=True,
        calendar_locale="US",
        datetime_index=_DAILY_INDEX,
    )

    assert "calendar_locale_set_but_holidays_unavailable" in contract.caution_flags
    assert "_calendar__is_holiday" not in contract.calendar_features
    assert _EXPECTED_DEFAULT_COLUMNS.issubset(set(contract.calendar_features))


def test_add_calendar_features_false_emits_no_calendar_columns() -> None:
    """Disabling calendar features must produce no _calendar__* entries."""
    contract = build_forecast_prep_contract(
        _triage_result(),
        routing_recommendation=_routing(),
        add_calendar_features=False,
    )

    assert contract.calendar_features == []
    assert not any(f.startswith("_calendar__") for f in contract.future_covariates)


def test_calendar_features_appear_in_future_covariates() -> None:
    """All auto-generated calendar columns must also be listed in future_covariates."""
    contract = build_forecast_prep_contract(
        _triage_result(),
        routing_recommendation=_routing(),
        add_calendar_features=True,
        datetime_index=_DAILY_INDEX,
    )

    for feature in contract.calendar_features:
        assert feature in contract.future_covariates, (
            f"Calendar feature {feature!r} missing from future_covariates"
        )


def test_calendar_locale_is_preserved_in_contract() -> None:
    """calendar_locale set in the call must be echoed in the contract field."""
    contract = build_forecast_prep_contract(
        _triage_result(),
        routing_recommendation=_routing(),
        add_calendar_features=True,
        calendar_locale="US",
        datetime_index=_DAILY_INDEX,
    )

    assert contract.calendar_locale == "US"


def test_calendar_locale_none_is_preserved_in_contract() -> None:
    """calendar_locale=None (default) should appear as None in the contract."""
    contract = build_forecast_prep_contract(
        _triage_result(),
        routing_recommendation=_routing(),
        add_calendar_features=False,
    )

    assert contract.calendar_locale is None


def test_blocked_contract_emits_no_calendar_features() -> None:
    """A blocked triage must yield empty calendar_features regardless of calendar settings."""
    blocked_result = TriageResult(
        request=TriageRequest(
            series=np.linspace(0.0, 1.0, 30),
            goal=AnalysisGoal.univariate,
            max_lag=12,
            n_surrogates=99,
            random_state=42,
        ),
        readiness=ReadinessReport(status=ReadinessStatus.blocked, warnings=[]),
        blocked=True,
        interpretation=None,
    )

    contract = build_forecast_prep_contract(
        blocked_result,
        routing_recommendation=_routing(),
        add_calendar_features=True,
        datetime_index=_DAILY_INDEX,
    )

    assert contract.blocked is True
    assert contract.calendar_features == []
    assert not any(f.startswith("_calendar__") for f in contract.future_covariates)
