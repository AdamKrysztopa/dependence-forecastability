"""Tests for F3 — Predictive Information Learning Curves."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from forecastability.services.predictive_info_learning_curve_service import (
    build_predictive_info_learning_curve,
)
from forecastability.triage.predictive_info_learning_curve import PredictiveInfoLearningCurve

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def ar1_signal() -> np.ndarray:
    """AR(1) with phi=0.9, n=500 — should exhibit a plateau."""
    rng = np.random.default_rng(42)
    n = 500
    out = np.zeros(n)
    out[0] = rng.standard_normal()
    for i in range(1, n):
        out[i] = 0.9 * out[i - 1] + rng.standard_normal()
    return out


@pytest.fixture()
def white_noise() -> np.ndarray:
    """IID white noise, n=500 — should have near-zero information values."""
    return np.random.default_rng(7).standard_normal(500)


@pytest.fixture()
def short_series() -> np.ndarray:
    """Very short series, n=15 — edge case."""
    return np.random.default_rng(3).standard_normal(15)


# ---------------------------------------------------------------------------
# PredictiveInfoLearningCurve domain model
# ---------------------------------------------------------------------------


class TestPredictiveInfoLearningCurveModel:
    def test_frozen_model_raises_on_mutation(self) -> None:
        curve = PredictiveInfoLearningCurve(
            window_sizes=[1, 2],
            information_values=[0.5, 0.4],
            convergence_index=1,
            recommended_lookback=2,
            plateau_detected=True,
            reliability_warnings=[],
        )
        with pytest.raises(ValidationError):
            curve.plateau_detected = False

    def test_valid_construction(self) -> None:
        curve = PredictiveInfoLearningCurve(
            window_sizes=[1, 2, 3],
            information_values=[0.3, 0.25, 0.24],
            convergence_index=1,
            recommended_lookback=2,
            plateau_detected=True,
            reliability_warnings=["Some warning"],
        )
        assert curve.window_sizes == [1, 2, 3]
        assert curve.plateau_detected is True
        assert len(curve.reliability_warnings) == 1

    def test_no_plateau_construction(self) -> None:
        curve = PredictiveInfoLearningCurve(
            window_sizes=[1, 2],
            information_values=[0.1, 0.2],
            convergence_index=-1,
            recommended_lookback=2,
            plateau_detected=False,
            reliability_warnings=[],
        )
        assert curve.convergence_index == -1
        assert not curve.plateau_detected


# ---------------------------------------------------------------------------
# build_predictive_info_learning_curve — return type and structure
# ---------------------------------------------------------------------------


class TestBuildReturnType:
    def test_returns_predictive_info_learning_curve(self, ar1_signal: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(ar1_signal)
        assert isinstance(result, PredictiveInfoLearningCurve)

    def test_window_sizes_start_at_one(self, ar1_signal: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(ar1_signal, max_k=5)
        assert result.window_sizes[0] == 1

    def test_window_sizes_length_matches_max_k(self, ar1_signal: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(ar1_signal, max_k=5)
        assert len(result.window_sizes) == 5
        assert result.window_sizes == list(range(1, 6))

    def test_information_values_length_matches_window_sizes(self, ar1_signal: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(ar1_signal, max_k=4)
        assert len(result.information_values) == len(result.window_sizes)

    def test_information_values_non_negative(self, ar1_signal: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(ar1_signal, max_k=8)
        assert all(v >= 0.0 for v in result.information_values)

    def test_accepts_list_input(self) -> None:
        data: list[float] = [float(i) * 0.1 for i in range(50)]
        result = build_predictive_info_learning_curve(data, max_k=3)
        assert isinstance(result, PredictiveInfoLearningCurve)


# ---------------------------------------------------------------------------
# Plateau detection on AR(1) signal
# ---------------------------------------------------------------------------


class TestPlateauDetectionAR1:
    def test_ar1_plateau_detected(self, ar1_signal: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(
            ar1_signal,
            max_k=8,
            random_state=42,
        )
        assert result.plateau_detected
        assert result.recommended_lookback <= 4

    def test_ar1_curve_rises_or_plateaus(self, ar1_signal: np.ndarray) -> None:
        # Joint MI increases with k until memory is captured; k=2 >= k=1 - tolerance
        result = build_predictive_info_learning_curve(
            ar1_signal,
            max_k=8,
            random_state=42,
        )
        v = result.information_values
        assert v[1] >= v[0] - 0.05, (
            f"Expected curve to be flat/rising at k=2 vs k=1; got {v[0]:.4f} -> {v[1]:.4f}"
        )

    def test_recommended_lookback_within_window_sizes(self, ar1_signal: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(ar1_signal, max_k=8)
        assert result.recommended_lookback in result.window_sizes

    def test_convergence_index_non_negative_when_plateau(self, ar1_signal: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(ar1_signal, max_k=8)
        if result.plateau_detected:
            assert result.convergence_index >= 0


# ---------------------------------------------------------------------------
# White noise — near-zero information
# ---------------------------------------------------------------------------


class TestWhiteNoise:
    def test_white_noise_all_values_low(self, white_noise: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(
            white_noise,
            max_k=4,
            random_state=7,
        )
        assert all(v < 0.15 for v in result.information_values)

    def test_white_noise_plateau_behavior(self, white_noise: np.ndarray) -> None:
        # White noise has near-zero MI for all k; plateau triggers early
        # recommended_lookback must always be within window_sizes
        result = build_predictive_info_learning_curve(
            white_noise,
            max_k=4,
            random_state=7,
        )
        assert result.recommended_lookback in result.window_sizes


# ---------------------------------------------------------------------------
# Short series edge case
# ---------------------------------------------------------------------------


class TestShortSeries:
    def test_short_series_does_not_crash(self, short_series: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(short_series, max_k=8)
        assert isinstance(result, PredictiveInfoLearningCurve)

    def test_short_series_returns_some_window_sizes_or_empty(
        self, short_series: np.ndarray
    ) -> None:
        result = build_predictive_info_learning_curve(short_series, max_k=8)
        # Series of length 15: n-k < 24 for all k >= 1, so no windows computed
        assert len(result.window_sizes) == 0

    def test_short_series_recommended_lookback_valid(self, short_series: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(short_series, max_k=8)
        if result.window_sizes:
            assert result.recommended_lookback in result.window_sizes
        else:
            assert result.recommended_lookback == 1


# ---------------------------------------------------------------------------
# Reliability warnings
# ---------------------------------------------------------------------------


class TestReliabilityWarnings:
    def test_short_series_triggers_length_warning(self, ar1_signal: np.ndarray) -> None:
        # n=500 < 1000 → must warn
        result = build_predictive_info_learning_curve(ar1_signal, max_k=5)
        assert any("500" in w for w in result.reliability_warnings)

    def test_long_series_no_length_warning(self) -> None:
        rng = np.random.default_rng(0)
        n = 1000
        series = np.zeros(n)
        series[0] = rng.standard_normal()
        for i in range(1, n):
            series[i] = 0.5 * series[i - 1] + rng.standard_normal()
        result = build_predictive_info_learning_curve(series, max_k=5)
        # n==1000 is exactly at the threshold — no length warning expected
        assert not any(str(n) in w and "unreliable" in w for w in result.reliability_warnings)

    def test_max_k_cap_warning_present(self, ar1_signal: np.ndarray) -> None:
        # requesting max_k > 8 should include the cap warning
        result = build_predictive_info_learning_curve(ar1_signal, max_k=9)
        assert any("capped" in w.lower() for w in result.reliability_warnings)

    def test_no_cap_warning_when_within_limit(self, ar1_signal: np.ndarray) -> None:
        # default max_k=8 == _MAX_K_CAP, no cap warning
        result = build_predictive_info_learning_curve(ar1_signal, max_k=8)
        assert not any("capped" in w.lower() for w in result.reliability_warnings)


# ---------------------------------------------------------------------------
# No-plateau case: convergence_index == -1
# ---------------------------------------------------------------------------


class TestNoPlateau:
    def test_monotone_increasing_no_plateau(self) -> None:
        # Strictly increasing values → relative gain always positive → no plateau
        rng = np.random.default_rng(99)
        # Construct a series where I values will not plateau by using max_plateau_tol=0
        series = rng.standard_normal(200)
        # With plateau_tol=0.0, gains are always >= 0 but the condition gain < 0 fails
        # Use tol < 0 to force no plateau trigger
        result = build_predictive_info_learning_curve(
            series,
            max_k=5,
            plateau_tol=-1.0,  # impossible to satisfy relative_gain < -1
        )
        assert not result.plateau_detected
        assert result.convergence_index == -1

    def test_no_plateau_recommended_lookback_is_last(self) -> None:
        rng = np.random.default_rng(99)
        series = rng.standard_normal(200)
        result = build_predictive_info_learning_curve(
            series,
            max_k=4,
            plateau_tol=-1.0,
        )
        assert result.recommended_lookback == result.window_sizes[-1]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_seed_same_result(self, ar1_signal: np.ndarray) -> None:
        r1 = build_predictive_info_learning_curve(ar1_signal, max_k=5, random_state=42)
        r2 = build_predictive_info_learning_curve(ar1_signal, max_k=5, random_state=42)
        assert r1.window_sizes == r2.window_sizes
        assert r1.information_values == r2.information_values
        assert r1.plateau_detected == r2.plateau_detected
        assert r1.recommended_lookback == r2.recommended_lookback

    def test_different_seed_may_differ(self, ar1_signal: np.ndarray) -> None:
        r1 = build_predictive_info_learning_curve(ar1_signal, max_k=5, random_state=0)
        r2 = build_predictive_info_learning_curve(ar1_signal, max_k=5, random_state=999)
        # Values may differ; this test just asserts both are valid
        assert isinstance(r1, PredictiveInfoLearningCurve)
        assert isinstance(r2, PredictiveInfoLearningCurve)


# ---------------------------------------------------------------------------
# max_k cap enforcement
# ---------------------------------------------------------------------------


class TestMaxKCap:
    def test_max_k_capped_at_8(self, ar1_signal: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(ar1_signal, max_k=20)
        assert max(result.window_sizes) <= 8

    def test_max_k_respects_smaller_value(self, ar1_signal: np.ndarray) -> None:
        result = build_predictive_info_learning_curve(ar1_signal, max_k=3)
        assert result.window_sizes == [1, 2, 3]
