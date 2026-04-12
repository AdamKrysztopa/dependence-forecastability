"""Tests for the triage method router (AGT-006)."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.triage.models import (
    AnalysisGoal,
    ReadinessReport,
    ReadinessStatus,
    ReadinessWarning,
    TriageRequest,
)
from forecastability.triage.router import plan_method


def _clear_report() -> ReadinessReport:
    return ReadinessReport(status=ReadinessStatus.clear, warnings=[])


def _warning_report(*codes: str) -> ReadinessReport:
    warnings = [ReadinessWarning(code=c, message=f"warn:{c}") for c in codes]
    return ReadinessReport(status=ReadinessStatus.warning, warnings=warnings)


def _blocked_report() -> ReadinessReport:
    return ReadinessReport(
        status=ReadinessStatus.blocked,
        warnings=[ReadinessWarning(code="VALIDATION_ERROR", message="bad")],
    )


def _make_series(n: int, *, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n)


class TestPlanMethod:
    def test_blocked_raises(self) -> None:
        req = TriageRequest(series=_make_series(300))
        with pytest.raises(ValueError, match="blocked"):
            plan_method(req, _blocked_report())

    def test_exog_not_none_routes_exogenous(self) -> None:
        series = _make_series(300)
        exog = _make_series(300)
        req = TriageRequest(series=series, exog=exog)
        plan = plan_method(req, _clear_report())
        assert plan.route == "exogenous"
        assert plan.compute_surrogates is True

    def test_goal_exogenous_routes_exogenous(self) -> None:
        req = TriageRequest(series=_make_series(300), goal=AnalysisGoal.exogenous)
        plan = plan_method(req, _clear_report())
        assert plan.route == "exogenous"

    def test_significance_infeasible_routes_univariate_no_sig(self) -> None:
        req = TriageRequest(series=_make_series(300))
        readiness = _warning_report("SIGNIFICANCE_FEASIBILITY")
        plan = plan_method(req, readiness)
        assert plan.route == "univariate_no_significance"
        assert plan.compute_surrogates is False

    def test_default_routes_univariate_with_significance(self) -> None:
        req = TriageRequest(series=_make_series(300))
        plan = plan_method(req, _clear_report())
        assert plan.route == "univariate_with_significance"
        assert plan.compute_surrogates is True

    def test_exog_with_sig_infeasible_no_surrogates(self) -> None:
        """Exogenous route with significance infeasibility → no surrogates."""
        series = _make_series(300)
        exog = _make_series(300)
        req = TriageRequest(series=series, exog=exog)
        readiness = _warning_report("SIGNIFICANCE_FEASIBILITY")
        plan = plan_method(req, readiness)
        assert plan.route == "exogenous"
        assert plan.compute_surrogates is False

    def test_plan_has_assumptions_and_rationale(self) -> None:
        req = TriageRequest(series=_make_series(300))
        plan = plan_method(req, _clear_report())
        assert len(plan.assumptions) > 0
        assert len(plan.rationale) > 0
