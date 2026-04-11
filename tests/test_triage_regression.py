"""Benchmark regression tests for triage routing and interpretation (AGT-016).

These tests pin the deterministic behaviour of the method router and
forecastability interpreter against four canonical series types.  Any
routing drift or interpretation regression causes an immediate CI failure.

Canonical series used:
- AR(1) φ=0.85            → high forecastability, univariate route
- White noise             → low forecastability, univariate route
- Trend + seasonal        → medium forecastability, univariate route
- Exogenous (AR(1)+noise) → exogenous route

Series length is kept at n=150 so the SIGNIFICANCE_FEASIBILITY warning is
triggered and surrogates are skipped — this keeps run time fast while still
exercising the full pipeline.
"""

from __future__ import annotations

import numpy as np

from forecastability.triage.models import (
    AnalysisGoal,
    ReadinessStatus,
    TriageRequest,
)
from forecastability.triage.run_triage import run_triage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RNG_SEED = 42


def _ar1(n: int, phi: float = 0.85, *, seed: int = _RNG_SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    ts = np.zeros(n)
    ts[0] = rng.standard_normal()
    for i in range(1, n):
        ts[i] = phi * ts[i - 1] + rng.standard_normal()
    return ts


def _white_noise(n: int, *, seed: int = _RNG_SEED) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(n)


def _trend_seasonal(n: int, *, seed: int = _RNG_SEED) -> np.ndarray:
    """Linear trend + weekly seasonal component + moderate noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    trend = 0.05 * t
    seasonal = 2.0 * np.sin(2.0 * np.pi * t / 7.0)
    noise = 0.8 * rng.standard_normal(n)
    return trend + seasonal + noise


_N = 150  # n < 200 → sig-infeasible → no surrogates (fast runs)
_MAX_LAG = 20


# ---------------------------------------------------------------------------
# Route regression
# ---------------------------------------------------------------------------


class TestRouteRegression:
    """Router must emit the same route for each canonical input type."""

    def test_ar1_routes_univariate_no_significance(self) -> None:
        req = TriageRequest(series=_ar1(_N), max_lag=_MAX_LAG, random_state=_RNG_SEED)
        result = run_triage(req)
        assert result.blocked is False
        assert result.method_plan is not None
        assert result.method_plan.route == "univariate_no_significance"
        assert result.method_plan.compute_surrogates is False

    def test_white_noise_routes_univariate_no_significance(self) -> None:
        req = TriageRequest(series=_white_noise(_N), max_lag=_MAX_LAG, random_state=_RNG_SEED)
        result = run_triage(req)
        assert result.blocked is False
        assert result.method_plan is not None
        assert result.method_plan.route == "univariate_no_significance"

    def test_trend_seasonal_routes_univariate_no_significance(self) -> None:
        req = TriageRequest(
            series=_trend_seasonal(_N), max_lag=_MAX_LAG, random_state=_RNG_SEED
        )
        result = run_triage(req)
        assert result.blocked is False
        assert result.method_plan is not None
        assert result.method_plan.route == "univariate_no_significance"

    def test_exog_routes_exogenous(self) -> None:
        rng = np.random.default_rng(_RNG_SEED)
        target = _ar1(_N)
        exog = target + 0.3 * rng.standard_normal(_N)
        req = TriageRequest(
            series=target,
            exog=exog,
            goal=AnalysisGoal.exogenous,
            max_lag=_MAX_LAG,
            random_state=_RNG_SEED,
        )
        result = run_triage(req)
        assert result.blocked is False
        assert result.method_plan is not None
        assert result.method_plan.route == "exogenous"
        assert result.method_plan.compute_surrogates is False


# ---------------------------------------------------------------------------
# Interpretation regression
# ---------------------------------------------------------------------------


class TestInterpretationRegression:
    """Forecastability class must be stable for canonical inputs."""

    def test_ar1_forecastability_class_is_high(self) -> None:
        req = TriageRequest(series=_ar1(_N), max_lag=_MAX_LAG, random_state=_RNG_SEED)
        result = run_triage(req)
        assert result.interpretation is not None
        assert result.interpretation.forecastability_class == "high"

    def test_white_noise_forecastability_class_is_low(self) -> None:
        req = TriageRequest(
            series=_white_noise(_N, seed=2),  # seed=2 is a reliable low draw
            max_lag=_MAX_LAG,
            random_state=2,
        )
        result = run_triage(req)
        assert result.interpretation is not None
        assert result.interpretation.forecastability_class == "low"

    def test_trend_seasonal_forecastability_class_is_not_low(self) -> None:
        """Trend + seasonal has meaningful structure; class must not be 'low'."""
        req = TriageRequest(
            series=_trend_seasonal(_N), max_lag=_MAX_LAG, random_state=_RNG_SEED
        )
        result = run_triage(req)
        assert result.interpretation is not None
        assert result.interpretation.forecastability_class != "low"

    def test_exog_has_interpretation_result(self) -> None:
        rng = np.random.default_rng(_RNG_SEED)
        target = _ar1(_N)
        exog = target + 0.3 * rng.standard_normal(_N)
        req = TriageRequest(
            series=target,
            exog=exog,
            goal=AnalysisGoal.exogenous,
            max_lag=_MAX_LAG,
            random_state=_RNG_SEED,
        )
        result = run_triage(req)
        assert result.interpretation is not None
        assert result.interpretation.forecastability_class in {"high", "medium", "low"}


# ---------------------------------------------------------------------------
# Readiness gate regression
# ---------------------------------------------------------------------------


class TestReadinessGateRegression:
    """Readiness gate must emit the correct status for canonical inputs."""

    def test_long_adequate_series_is_clear_or_warning(self) -> None:
        """n=150 is valid but sig-infeasible → warning, never blocked."""
        req = TriageRequest(series=_ar1(_N), max_lag=_MAX_LAG, random_state=_RNG_SEED)
        result = run_triage(req)
        assert result.readiness.status in {ReadinessStatus.clear, ReadinessStatus.warning}
        assert result.blocked is False

    def test_very_short_series_is_blocked(self) -> None:
        """Series of 20 points with max_lag=40 → blocked."""
        req = TriageRequest(series=_ar1(20), max_lag=40, random_state=_RNG_SEED)
        result = run_triage(req)
        assert result.blocked is True
        assert result.readiness.status == ReadinessStatus.blocked

    def test_sig_infeasibility_warning_present(self) -> None:
        """n=150 → SIGNIFICANCE_FEASIBILITY warning is emitted."""
        req = TriageRequest(series=_ar1(_N), max_lag=_MAX_LAG, random_state=_RNG_SEED)
        result = run_triage(req)
        warning_codes = {w.code for w in result.readiness.warnings}
        assert "SIGNIFICANCE_FEASIBILITY" in warning_codes


# ---------------------------------------------------------------------------
# Determinism regression
# ---------------------------------------------------------------------------


class TestDeterminismRegression:
    """Two calls with the same random_state must produce identical results."""

    def test_ar1_is_deterministic(self) -> None:
        series = _ar1(_N)
        req = TriageRequest(series=series, max_lag=_MAX_LAG, random_state=_RNG_SEED)
        r1 = run_triage(req)
        r2 = run_triage(req)
        assert r1.interpretation is not None
        assert r2.interpretation is not None
        assert r1.interpretation.forecastability_class == r2.interpretation.forecastability_class
        assert r1.method_plan == r2.method_plan
        assert np.allclose(r1.analyze_result.raw, r2.analyze_result.raw)

    def test_exog_is_deterministic(self) -> None:
        rng = np.random.default_rng(_RNG_SEED)
        target = _ar1(_N)
        exog = target + 0.3 * rng.standard_normal(_N)
        req = TriageRequest(
            series=target,
            exog=exog,
            goal=AnalysisGoal.exogenous,
            max_lag=_MAX_LAG,
            random_state=_RNG_SEED,
        )
        r1 = run_triage(req)
        r2 = run_triage(req)
        assert r1.method_plan == r2.method_plan
        assert np.allclose(r1.analyze_result.raw, r2.analyze_result.raw)
