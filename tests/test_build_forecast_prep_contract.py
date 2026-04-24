"""Focused tests for the forecast-prep contract builder use case."""

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


def _make_triage_result(*, blocked: bool, primary_lags: list[int] | None = None) -> TriageResult:
    """Build a minimal deterministic TriageResult for unit tests."""
    request = TriageRequest(
        series=np.linspace(0.0, 1.0, 80),
        goal=AnalysisGoal.univariate,
        max_lag=24,
        n_surrogates=99,
        random_state=42,
    )
    readiness = ReadinessReport(
        status=ReadinessStatus.blocked if blocked else ReadinessStatus.clear,
        warnings=[],
    )
    interpretation = None
    if not blocked:
        interpretation = InterpretationResult(
            forecastability_class="high",
            directness_class="high",
            primary_lags=primary_lags or [1, 7],
            modeling_regime="deterministic triage",
            narrative="test narrative",
            diagnostics=Diagnostics(
                peak_ami_first_5=0.3,
                directness_ratio=0.6,
                n_sig_ami=3,
                n_sig_pami=2,
                exploitability_mismatch=0,
                best_smape=0.12,
            ),
        )
    return TriageResult(
        request=request,
        readiness=readiness,
        blocked=blocked,
        interpretation=interpretation,
    )


def _routing_recommendation(*, confidence_label: str) -> RoutingRecommendation:
    """Build a deterministic routing recommendation fixture."""
    return RoutingRecommendation(
        primary_families=["arima", "ets"],
        secondary_families=["linear_state_space"],
        rationale=["deterministic routing"],
        caution_flags=["near_threshold"],
        confidence_label=confidence_label,  # type: ignore[arg-type]
    )


def test_blocked_triage_yields_conservative_contract() -> None:
    """Blocked triage should produce conservative abstaining contract outputs."""
    contract = build_forecast_prep_contract(
        _make_triage_result(blocked=True),
        routing_recommendation=_routing_recommendation(confidence_label="high"),
        add_calendar_features=False,
    )

    assert contract.blocked is True
    assert contract.confidence_label == "abstain"
    assert contract.recommended_target_lags == []
    assert contract.recommended_families == []
    assert any("blocked" in flag for flag in contract.caution_flags)


def test_blocked_triage_default_calendar_path_does_not_require_datetime_index() -> None:
    """Blocked calls should return conservative contracts under default calendar settings."""
    contract = build_forecast_prep_contract(
        _make_triage_result(blocked=True),
        routing_recommendation=_routing_recommendation(confidence_label="high"),
    )

    assert contract.blocked is True
    assert contract.confidence_label == "abstain"
    assert contract.calendar_features == []
    assert contract.recommended_families == []


def test_abstain_routing_yields_empty_recommended_families() -> None:
    """Abstain confidence should propagate and clear recommended families."""
    contract = build_forecast_prep_contract(
        _make_triage_result(blocked=False, primary_lags=[1, 7]),
        routing_recommendation=_routing_recommendation(confidence_label="abstain"),
        add_calendar_features=False,
    )

    assert contract.blocked is False
    assert contract.confidence_label == "abstain"
    assert contract.recommended_families == []
    assert contract.recommended_target_lags == [1]


def test_missing_datetime_index_for_calendar_features_raises_actionable_error() -> None:
    """Calendar auto-generation requires datetime_index and should fail clearly otherwise."""
    with pytest.raises(ValueError, match="add_calendar_features=True requires datetime_index"):
        build_forecast_prep_contract(
            _make_triage_result(blocked=False),
            routing_recommendation=_routing_recommendation(confidence_label="high"),
            add_calendar_features=True,
            datetime_index=None,
        )


def test_calendar_locale_without_holidays_adds_caution_and_skips_holiday_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Builder should continue when holidays is unavailable and set caution flag."""
    monkeypatch.setattr(calendar_feature_service, "_HOLIDAYS_AVAILABLE", False)

    contract = build_forecast_prep_contract(
        _make_triage_result(blocked=False),
        routing_recommendation=_routing_recommendation(confidence_label="medium"),
        add_calendar_features=True,
        calendar_locale="US",
        datetime_index=pd.date_range("2024-01-01", periods=10, freq="D"),
    )

    expected = {
        "_calendar__dayofweek",
        "_calendar__month",
        "_calendar__quarter",
        "_calendar__is_weekend",
        "_calendar__is_business_day",
    }
    assert expected.issubset(set(contract.calendar_features))
    assert "_calendar__is_holiday" not in contract.calendar_features
    assert "calendar_locale_set_but_holidays_unavailable" in contract.caution_flags
