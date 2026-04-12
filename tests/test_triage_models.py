"""Tests for triage domain models (AGT-004)."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from forecastability.triage.models import (
    AnalysisGoal,
    MethodPlan,
    ReadinessReport,
    ReadinessStatus,
    ReadinessWarning,
    TriageRequest,
    TriageResult,
)


class TestAnalysisGoal:
    def test_enum_values(self) -> None:
        assert AnalysisGoal.univariate == "univariate"
        assert AnalysisGoal.exogenous == "exogenous"

    def test_comparison_removed(self) -> None:
        """AGT-022: comparison was removed; verify it is not in the enum."""
        assert not hasattr(AnalysisGoal, "comparison")

    def test_is_str_subclass(self) -> None:
        assert isinstance(AnalysisGoal.univariate, str)


class TestReadinessStatus:
    def test_enum_values(self) -> None:
        assert ReadinessStatus.blocked == "blocked"
        assert ReadinessStatus.warning == "warning"
        assert ReadinessStatus.clear == "clear"

    def test_is_str_subclass(self) -> None:
        assert isinstance(ReadinessStatus.clear, str)


class TestTriageRequest:
    def _make_request(self) -> TriageRequest:
        return TriageRequest(series=np.arange(100, dtype=float))

    def test_defaults(self) -> None:
        req = self._make_request()
        assert req.goal == AnalysisGoal.univariate
        assert req.max_lag == 40
        assert req.n_surrogates == 99
        assert req.random_state == 42
        assert req.exog is None

    def test_serialization_round_trip(self) -> None:
        rng = np.random.default_rng(0)
        series = rng.standard_normal(200)
        req = TriageRequest(
            series=series,
            goal=AnalysisGoal.exogenous,
            max_lag=20,
            n_surrogates=199,
            random_state=7,
        )
        dumped = req.model_dump()
        restored = TriageRequest.model_validate(dumped)
        assert restored.goal == req.goal
        assert restored.max_lag == req.max_lag
        assert restored.n_surrogates == req.n_surrogates
        assert restored.random_state == req.random_state
        np.testing.assert_array_equal(restored.series, req.series)

    def test_frozen(self) -> None:
        req = self._make_request()
        with pytest.raises(ValidationError):
            req.max_lag = 99  # type: ignore[misc]


class TestReadinessReport:
    def test_frozen(self) -> None:
        report = ReadinessReport(
            status=ReadinessStatus.clear,
            warnings=[],
        )
        with pytest.raises(ValidationError):
            report.status = ReadinessStatus.blocked  # type: ignore[misc]

    def test_construction(self) -> None:
        w = ReadinessWarning(code="TEST", message="test message")
        report = ReadinessReport(status=ReadinessStatus.warning, warnings=[w])
        assert report.status == ReadinessStatus.warning
        assert len(report.warnings) == 1
        assert report.warnings[0].code == "TEST"


class TestMethodPlan:
    def test_frozen(self) -> None:
        plan = MethodPlan(
            route="univariate_with_significance",
            compute_surrogates=True,
            assumptions=["a"],
            rationale="r",
        )
        with pytest.raises(ValidationError):
            plan.route = "other"  # type: ignore[misc]


class TestTriageResult:
    def test_blocked_result(self) -> None:
        req = TriageRequest(series=np.arange(100, dtype=float))
        report = ReadinessReport(
            status=ReadinessStatus.blocked,
            warnings=[ReadinessWarning(code="VALIDATION_ERROR", message="bad")],
        )
        result = TriageResult(request=req, readiness=report, blocked=True)
        assert result.blocked is True
        assert result.method_plan is None
        assert result.analyze_result is None
        assert result.interpretation is None

    def test_clear_result(self) -> None:
        req = TriageRequest(series=np.arange(300, dtype=float))
        report = ReadinessReport(status=ReadinessStatus.clear, warnings=[])
        plan = MethodPlan(
            route="univariate_with_significance",
            compute_surrogates=True,
            assumptions=[],
            rationale="ok",
        )
        result = TriageResult(
            request=req,
            readiness=report,
            method_plan=plan,
            blocked=False,
            recommendation="HIGH -> ...",
        )
        assert result.blocked is False
        assert result.method_plan is not None
        assert result.recommendation == "HIGH -> ..."
