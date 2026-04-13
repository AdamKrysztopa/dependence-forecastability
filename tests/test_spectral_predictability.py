"""Tests for F4 Spectral Predictability components."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.scorers import (
    ScorerInfo,
    _spectral_predictability_scorer,
    default_registry,
)
from forecastability.services.spectral_predictability_service import (
    build_spectral_predictability,
)
from forecastability.triage.spectral_predictability import SpectralPredictabilityResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def periodic_series() -> np.ndarray:
    """Pure sine wave — spectrally concentrated, high predictability."""
    t = np.linspace(0, 16 * np.pi, 512)
    return np.sin(t)


@pytest.fixture()
def white_noise_series() -> np.ndarray:
    """White noise — flat spectrum, low predictability."""
    return np.random.default_rng(0).standard_normal(512)


@pytest.fixture()
def ar1_series() -> np.ndarray:
    """AR(1) with φ=0.7 — moderate structure between extremes."""
    rng = np.random.default_rng(42)
    n = 512
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.7 * x[i - 1] + rng.standard_normal()
    return x


# ---------------------------------------------------------------------------
# TestSpectralPredictabilityScorer
# ---------------------------------------------------------------------------


class TestSpectralPredictabilityScorer:
    def test_white_noise_scores_low(self, white_noise_series: np.ndarray) -> None:
        score = _spectral_predictability_scorer(white_noise_series)
        assert score < 0.30, f"Expected Ω < 0.30 for white noise; got {score:.4f}"

    def test_periodic_scores_high(self, periodic_series: np.ndarray) -> None:
        score = _spectral_predictability_scorer(periodic_series)
        assert score > 0.70, f"Expected Ω > 0.70 for pure sine; got {score:.4f}"

    def test_ar1_moderate_between_extremes(self, ar1_series: np.ndarray) -> None:
        score = _spectral_predictability_scorer(ar1_series)
        assert 0.0 < score < 1.0, f"Expected Ω ∈ (0, 1) for AR(1); got {score:.4f}"

    def test_returns_float_in_unit_interval(self, ar1_series: np.ndarray) -> None:
        score = _spectral_predictability_scorer(ar1_series)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_deterministic(self, ar1_series: np.ndarray) -> None:
        score1 = _spectral_predictability_scorer(ar1_series)
        score2 = _spectral_predictability_scorer(ar1_series)
        assert score1 == score2

    def test_raises_for_short_series(self) -> None:
        with pytest.raises(ValueError):
            _spectral_predictability_scorer(np.ones(5))

    def test_registered_in_default_registry(self) -> None:
        registry = default_registry()
        info = registry.get("spectral_predictability")
        assert isinstance(info, ScorerInfo)

    def test_kind_is_univariate(self) -> None:
        registry = default_registry()
        info = registry.get("spectral_predictability")
        assert info.kind == "univariate"


# ---------------------------------------------------------------------------
# TestBuildSpectralPredictability
# ---------------------------------------------------------------------------


class TestBuildSpectralPredictability:
    def test_returns_spectral_predictability_result(self, ar1_series: np.ndarray) -> None:
        result = build_spectral_predictability(ar1_series)
        assert isinstance(result, SpectralPredictabilityResult)

    def test_score_equals_one_minus_normalised_entropy(self, ar1_series: np.ndarray) -> None:
        result = build_spectral_predictability(ar1_series)
        assert result.score == pytest.approx(1.0 - result.normalised_entropy, abs=1e-12)

    def test_score_in_unit_interval(self, ar1_series: np.ndarray) -> None:
        result = build_spectral_predictability(ar1_series)
        assert 0.0 <= result.score <= 1.0

    def test_n_bins_positive(self, ar1_series: np.ndarray) -> None:
        result = build_spectral_predictability(ar1_series)
        assert result.n_bins > 0

    def test_detrend_preserved(self, ar1_series: np.ndarray) -> None:
        result = build_spectral_predictability(ar1_series, detrend="linear")
        assert result.detrend == "linear"

    def test_interpretation_high_for_periodic(self, periodic_series: np.ndarray) -> None:
        result = build_spectral_predictability(periodic_series)
        assert "High spectral" in result.interpretation

    def test_interpretation_low_for_white_noise(self, white_noise_series: np.ndarray) -> None:
        result = build_spectral_predictability(white_noise_series)
        assert "Low spectral" in result.interpretation

    def test_nperseg_override(self, ar1_series: np.ndarray) -> None:
        result = build_spectral_predictability(ar1_series, nperseg=32)
        assert isinstance(result, SpectralPredictabilityResult)
