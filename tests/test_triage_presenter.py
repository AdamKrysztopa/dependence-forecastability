"""Tests for the shared triage presenter (C6 — presenter/port cleanup)."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.adapters.triage_presenter import (
    TriageAnalyticsView,
    TriageResultView,
    present_triage_analytics,
    present_triage_result,
)
from forecastability.triage.models import TriageRequest
from forecastability.use_cases.run_triage import run_triage


@pytest.fixture()
def ar1_result():
    """Run triage on an AR(1) series and return the TriageResult."""
    rng = np.random.default_rng(42)
    n = 150
    ts = np.zeros(n)
    ts[0] = rng.standard_normal()
    for i in range(1, n):
        ts[i] = 0.85 * ts[i - 1] + rng.standard_normal()

    req = TriageRequest(series=ts, max_lag=20, random_state=42)
    return run_triage(req)


@pytest.fixture()
def blocked_result():
    """Run triage on a short series that triggers the readiness block."""
    rng = np.random.default_rng(0)
    req = TriageRequest(series=rng.standard_normal(30), max_lag=40)
    return run_triage(req)


class TestPresentTriageResultBlocked:
    def test_blocked_view_has_correct_flag(self, blocked_result) -> None:
        view = present_triage_result(blocked_result)
        assert isinstance(view, TriageResultView)
        assert view.blocked is True

    def test_blocked_view_has_readiness_status(self, blocked_result) -> None:
        view = present_triage_result(blocked_result)
        assert view.readiness_status == "blocked"

    def test_blocked_view_optional_fields_are_none(self, blocked_result) -> None:
        view = present_triage_result(blocked_result)
        assert view.route is None
        assert view.compute_surrogates is None
        assert view.recommendation is None
        assert view.forecastability_class is None
        assert view.method is None

    def test_blocked_view_primary_lags_empty(self, blocked_result) -> None:
        view = present_triage_result(blocked_result)
        assert view.primary_lags == []


class TestPresentTriageResultUnblocked:
    def test_unblocked_view_not_blocked(self, ar1_result) -> None:
        view = present_triage_result(ar1_result)
        assert view.blocked is False

    def test_unblocked_view_has_route(self, ar1_result) -> None:
        view = present_triage_result(ar1_result)
        assert view.route is not None

    def test_unblocked_view_has_forecastability_class(self, ar1_result) -> None:
        view = present_triage_result(ar1_result)
        assert view.forecastability_class is not None

    def test_unblocked_view_has_method(self, ar1_result) -> None:
        view = present_triage_result(ar1_result)
        assert view.method is not None

    def test_unblocked_view_has_method_plan_fields(self, ar1_result) -> None:
        view = present_triage_result(ar1_result)
        assert view.method_plan_rationale is not None
        assert view.method_plan_assumptions is not None

    def test_unblocked_view_has_recommendation(self, ar1_result) -> None:
        view = present_triage_result(ar1_result)
        assert view.recommendation is not None

    def test_unblocked_view_sig_lags_are_ints(self, ar1_result) -> None:
        view = present_triage_result(ar1_result)
        assert isinstance(view.n_sig_raw_lags, int)
        assert isinstance(view.n_sig_partial_lags, int)

    def test_view_model_dump_is_json_safe(self, ar1_result) -> None:
        """model_dump should produce only JSON-native types."""
        view = present_triage_result(ar1_result)
        data = view.model_dump()
        assert isinstance(data, dict)
        assert isinstance(data["blocked"], bool)
        assert isinstance(data["readiness_warnings"], list)


class TestPresentTriageAnalytics:
    def test_analytics_none_when_blocked(self, blocked_result) -> None:
        analytics = present_triage_analytics(blocked_result)
        assert analytics is None

    def test_analytics_present_for_unblocked(self, ar1_result) -> None:
        analytics = present_triage_analytics(ar1_result)
        assert isinstance(analytics, TriageAnalyticsView)

    def test_analytics_has_curve_stats(self, ar1_result) -> None:
        analytics = present_triage_analytics(ar1_result)
        assert analytics is not None
        assert isinstance(analytics.raw_curve_mean, float)
        assert isinstance(analytics.partial_curve_mean, float)
        assert isinstance(analytics.raw_curve_max, float)
        assert isinstance(analytics.partial_curve_max, float)

    def test_analytics_has_diagnostics(self, ar1_result) -> None:
        analytics = present_triage_analytics(ar1_result)
        assert analytics is not None
        assert analytics.diagnostics is not None
        assert "peak_ami_first_5" in analytics.diagnostics
        assert "directness_ratio" in analytics.diagnostics
