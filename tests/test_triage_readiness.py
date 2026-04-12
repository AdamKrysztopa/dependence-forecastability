"""Tests for the triage readiness gate (AGT-005)."""

from __future__ import annotations

import numpy as np

from forecastability.triage.models import (
    AnalysisGoal,
    ReadinessStatus,
    TriageRequest,
)
from forecastability.triage.readiness import assess_readiness


def _make_series(n: int, *, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n)


class TestAssessReadiness:
    def test_short_series_lag_blocks(self) -> None:
        """max_lag=40 >= n-50=30-50 (negative) → blocked for n=30 since 40>=30-50=-20 holds,
        but also 40>=n=30 is checked first; effectively blocked with LAG_FEASIBILITY."""
        req = TriageRequest(series=_make_series(30), max_lag=40)
        report = assess_readiness(req)
        assert report.status == ReadinessStatus.blocked
        codes = [w.code for w in report.warnings]
        assert "LAG_FEASIBILITY" in codes

    def test_long_series_is_clear(self) -> None:
        """Series of length 500 with default max_lag → clear."""
        req = TriageRequest(series=_make_series(500))
        report = assess_readiness(req)
        assert report.status == ReadinessStatus.clear
        assert report.warnings == []

    def test_short_series_significance_warning(self) -> None:
        """Series of length 150 → warning for SIGNIFICANCE_FEASIBILITY."""
        # max_lag default=40, n=150, 40 < 150 (no lag block), 40 < 100=150-50 (no lag warn)
        req = TriageRequest(series=_make_series(150), max_lag=20)
        report = assess_readiness(req)
        assert report.status == ReadinessStatus.warning
        codes = [w.code for w in report.warnings]
        assert "SIGNIFICANCE_FEASIBILITY" in codes

    def test_all_nan_series_blocks(self) -> None:
        """All-NaN series → blocked with VALIDATION_ERROR."""
        req = TriageRequest(series=np.full(50, np.nan))
        report = assess_readiness(req)
        assert report.status == ReadinessStatus.blocked
        codes = [w.code for w in report.warnings]
        assert "VALIDATION_ERROR" in codes

    def test_constant_series_blocks(self) -> None:
        """Constant series → blocked with VALIDATION_ERROR."""
        req = TriageRequest(series=np.ones(50))
        report = assess_readiness(req)
        assert report.status == ReadinessStatus.blocked
        codes = [w.code for w in report.warnings]
        assert "VALIDATION_ERROR" in codes

    def test_exog_length_mismatch_blocks(self) -> None:
        """Exog length != series length → blocked with EXOG_LENGTH_MISMATCH."""
        series = _make_series(300)
        exog = _make_series(200)
        req = TriageRequest(series=series, exog=exog)
        report = assess_readiness(req)
        assert report.status == ReadinessStatus.blocked
        codes = [w.code for w in report.warnings]
        assert "EXOG_LENGTH_MISMATCH" in codes

    def test_adequate_series_no_exog_is_clear(self) -> None:
        """Long adequate series, no exog → clear with no warnings."""
        req = TriageRequest(series=_make_series(400), max_lag=30)
        report = assess_readiness(req)
        assert report.status == ReadinessStatus.clear
        assert report.warnings == []

    def test_lag_near_boundary_warning(self) -> None:
        """max_lag=110 > n//2=100 but < n-50=150 → warning (not blocked)."""
        n = 200
        # max_lag=110: 110 < 200-50=150 (no block), 110 > 200//2=100 (warn)
        req = TriageRequest(series=_make_series(n), max_lag=110)
        report = assess_readiness(req)
        assert report.status == ReadinessStatus.warning
        codes = [w.code for w in report.warnings]
        assert "LAG_FEASIBILITY" in codes

    def test_lag_boundary_blocks(self) -> None:
        """max_lag=150 >= n-50=150 → blocked with LAG_FEASIBILITY."""
        n = 200
        req = TriageRequest(series=_make_series(n), max_lag=150)
        report = assess_readiness(req)
        assert report.status == ReadinessStatus.blocked
        codes = [w.code for w in report.warnings]
        assert "LAG_FEASIBILITY" in codes

    def test_goal_exogenous_no_exog_blocks(self) -> None:
        """goal='exogenous' with exog=None → blocked with MISSING_EXOG."""
        req = TriageRequest(
            series=_make_series(500),
            goal=AnalysisGoal.exogenous,
            exog=None,
        )
        report = assess_readiness(req)
        assert report.status == ReadinessStatus.blocked
        codes = [w.code for w in report.warnings]
        assert "MISSING_EXOG" in codes

    def test_goal_univariate_with_exog_warns(self) -> None:
        """goal='univariate' with non-None exog → warning with GOAL_EXOG_MISMATCH."""
        series = _make_series(500)
        exog = np.random.default_rng(0).standard_normal(500)
        req = TriageRequest(
            series=series,
            goal=AnalysisGoal.univariate,
            exog=exog,
        )
        report = assess_readiness(req)
        assert report.status == ReadinessStatus.warning
        codes = [w.code for w in report.warnings]
        assert "GOAL_EXOG_MISMATCH" in codes

    def test_too_short_validation_error(self) -> None:
        """Series shorter than min_length=10 → blocked with VALIDATION_ERROR."""
        req = TriageRequest(series=_make_series(5), max_lag=2)
        report = assess_readiness(req)
        assert report.status == ReadinessStatus.blocked
        codes = [w.code for w in report.warnings]
        assert "VALIDATION_ERROR" in codes
