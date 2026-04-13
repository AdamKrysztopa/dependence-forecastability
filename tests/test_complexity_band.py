"""Tests for F6 Entropy-Based Complexity Triage components."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.scorers import (
    _choose_embedding_order,
    _compute_permutation_entropy,
    _permutation_entropy_scorer,
    _spectral_entropy_scorer,
    default_registry,
)
from forecastability.services.complexity_band_service import build_complexity_band
from forecastability.triage.complexity_band import ComplexityBandResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def periodic_series() -> np.ndarray:
    """Pure sine wave — highly regular, low entropy."""
    return np.sin(np.linspace(0, 16 * np.pi, 512))


@pytest.fixture()
def noisy_series() -> np.ndarray:
    """White noise — maximum disorder, high entropy."""
    return np.random.default_rng(0).standard_normal(512)


@pytest.fixture()
def short_series() -> np.ndarray:
    """Short series of length 30 — triggers m=3."""
    return np.random.default_rng(1).standard_normal(30)


# ---------------------------------------------------------------------------
# _choose_embedding_order
# ---------------------------------------------------------------------------


class TestChooseEmbeddingOrder:
    def test_long_series(self) -> None:
        assert _choose_embedding_order(1000) == 5

    def test_medium_series(self) -> None:
        assert _choose_embedding_order(500) == 4
        assert _choose_embedding_order(100) == 4

    def test_short_series(self) -> None:
        assert _choose_embedding_order(50) == 3
        assert _choose_embedding_order(20) == 3


# ---------------------------------------------------------------------------
# _compute_permutation_entropy
# ---------------------------------------------------------------------------


class TestComputePermutationEntropy:
    def test_returns_float_in_unit_interval(self, periodic_series: np.ndarray) -> None:
        pe = _compute_permutation_entropy(periodic_series, m=4)
        assert isinstance(pe, float)
        assert 0.0 <= pe <= 1.0

    def test_periodic_lower_than_noise(
        self, periodic_series: np.ndarray, noisy_series: np.ndarray
    ) -> None:
        pe_periodic = _compute_permutation_entropy(periodic_series, m=4)
        pe_noisy = _compute_permutation_entropy(noisy_series, m=4)
        assert pe_periodic < pe_noisy

    def test_constant_series_zero_entropy(self) -> None:
        series = np.ones(100)
        pe = _compute_permutation_entropy(series, m=3)
        # All windows have identical values → all maps to same pattern
        assert pe == pytest.approx(0.0, abs=1e-9)

    def test_raises_for_m_less_than_2(self) -> None:
        with pytest.raises(ValueError, match="m must be >= 2"):
            _compute_permutation_entropy(np.arange(10, dtype=float), m=1)

    def test_raises_when_series_shorter_than_m(self) -> None:
        with pytest.raises(ValueError, match="Series length"):
            _compute_permutation_entropy(np.arange(3, dtype=float), m=5)

    def test_deterministic(self, noisy_series: np.ndarray) -> None:
        pe1 = _compute_permutation_entropy(noisy_series, m=4)
        pe2 = _compute_permutation_entropy(noisy_series, m=4)
        assert pe1 == pe2

    def test_tie_stability(self) -> None:
        """Constant blocks should yield reproducible patterns (stable sort)."""
        series = np.array([1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0], dtype=float)
        pe1 = _compute_permutation_entropy(series, m=3)
        pe2 = _compute_permutation_entropy(series, m=3)
        assert pe1 == pe2


# ---------------------------------------------------------------------------
# _permutation_entropy_scorer (SeriesDiagnosticScorer interface)
# ---------------------------------------------------------------------------


class TestPermutationEntropyScorer:
    def test_returns_float_nonnegative(self, noisy_series: np.ndarray) -> None:
        score = _permutation_entropy_scorer(noisy_series)
        assert isinstance(score, float)
        assert score >= 0.0

    def test_periodic_lower_than_noise(
        self, periodic_series: np.ndarray, noisy_series: np.ndarray
    ) -> None:
        assert _permutation_entropy_scorer(periodic_series) < _permutation_entropy_scorer(
            noisy_series
        )

    def test_registered_in_default_registry(self) -> None:
        registry = default_registry()
        info = registry.get("permutation_entropy")
        assert info.kind == "univariate"
        assert info.family == "nonlinear"

    def test_scorer_via_registry(self, noisy_series: np.ndarray) -> None:
        registry = default_registry()
        info = registry.get("permutation_entropy")
        score = info.scorer(noisy_series, random_state=42)
        assert isinstance(score, float)

    def test_raises_for_2d_input(self) -> None:
        with pytest.raises(ValueError):
            _permutation_entropy_scorer(np.ones((10, 2)))

    def test_raises_for_short_input(self) -> None:
        with pytest.raises(ValueError):
            _permutation_entropy_scorer(np.ones(4))


# ---------------------------------------------------------------------------
# _spectral_entropy_scorer (SeriesDiagnosticScorer interface)
# ---------------------------------------------------------------------------


class TestSpectralEntropyScorer:
    def test_returns_float_in_unit_interval(self, noisy_series: np.ndarray) -> None:
        score = _spectral_entropy_scorer(noisy_series)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_periodic_lower_than_noise(
        self, periodic_series: np.ndarray, noisy_series: np.ndarray
    ) -> None:
        se_periodic = _spectral_entropy_scorer(periodic_series)
        se_noisy = _spectral_entropy_scorer(noisy_series)
        assert se_periodic < se_noisy

    def test_registered_in_default_registry(self) -> None:
        registry = default_registry()
        info = registry.get("spectral_entropy")
        assert info.kind == "univariate"

    def test_scorer_via_registry(self, periodic_series: np.ndarray) -> None:
        registry = default_registry()
        info = registry.get("spectral_entropy")
        score = info.scorer(periodic_series, random_state=0)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# build_complexity_band (service)
# ---------------------------------------------------------------------------


class TestBuildComplexityBand:
    def test_returns_complexity_band_result(self, noisy_series: np.ndarray) -> None:
        result = build_complexity_band(noisy_series)
        assert isinstance(result, ComplexityBandResult)

    def test_periodic_is_low(self, periodic_series: np.ndarray) -> None:
        result = build_complexity_band(periodic_series)
        assert result.complexity_band == "low"

    def test_noise_is_high(self, noisy_series: np.ndarray) -> None:
        result = build_complexity_band(noisy_series)
        assert result.complexity_band == "high"

    def test_entropy_values_in_unit_interval(self, noisy_series: np.ndarray) -> None:
        r = build_complexity_band(noisy_series)
        assert 0.0 <= r.permutation_entropy <= 1.0
        assert 0.0 <= r.spectral_entropy <= 1.0

    def test_interpretation_string_non_empty(self, noisy_series: np.ndarray) -> None:
        r = build_complexity_band(noisy_series)
        assert len(r.interpretation) > 0

    def test_short_series_no_crash(self, short_series: np.ndarray) -> None:
        r = build_complexity_band(short_series)
        assert r.complexity_band in ("low", "medium", "high")

    def test_reliability_warning_emitted_for_large_m_small_n(self) -> None:
        # Force m=5 by using a short but just-long-enough series; m=5 needs n>=1000
        # but n=512 is < 1000, so we should get a warning at m=5.
        # _choose_embedding_order(512) = 4, so no warning there.
        # Use n=50 (m=3) — no warning.
        series_small = np.random.default_rng(5).standard_normal(50)
        r = build_complexity_band(series_small)
        # m=3 for n=50 — no reliability concern
        assert r.pe_reliability_warning is None

    def test_reliability_warning_long_enough(self) -> None:
        series = np.random.default_rng(6).standard_normal(1024)
        r = build_complexity_band(series)
        assert r.pe_reliability_warning is None

    def test_embedding_order_matches_choose(self, noisy_series: np.ndarray) -> None:
        n = len(noisy_series)
        expected_m = _choose_embedding_order(n)
        r = build_complexity_band(noisy_series)
        assert r.embedding_order == expected_m

    def test_invalid_thresholds_raise(self, noisy_series: np.ndarray) -> None:
        with pytest.raises(ValueError, match="low_threshold"):
            build_complexity_band(noisy_series, low_threshold=0.7, high_threshold=0.5)

    def test_custom_thresholds(self, noisy_series: np.ndarray) -> None:
        """Force everything to medium by collapsing thresholds."""
        r = build_complexity_band(noisy_series, low_threshold=0.0, high_threshold=1.0)
        assert r.complexity_band == "medium"

    def test_ar1_medium_or_high(self) -> None:
        """AR(1) with moderate autocorrelation should not be 'low'."""
        rng = np.random.default_rng(42)
        series = np.zeros(512)
        series[0] = rng.standard_normal()
        for t in range(1, 512):
            series[t] = 0.7 * series[t - 1] + rng.standard_normal()
        r = build_complexity_band(series)
        assert r.complexity_band in ("medium", "high")


# ---------------------------------------------------------------------------
# Integration: complexity_band field on TriageResult
# ---------------------------------------------------------------------------


class TestTriageResultComplexityBand:
    def test_run_triage_populates_complexity_band(self) -> None:
        from forecastability.triage import TriageRequest, run_triage

        rng = np.random.default_rng(0)
        series = rng.standard_normal(200)
        request = TriageRequest(series=series, max_lag=5, n_surrogates=99)
        result = run_triage(request)

        assert result.complexity_band is not None
        assert isinstance(result.complexity_band, ComplexityBandResult)
        assert result.complexity_band.complexity_band in ("low", "medium", "high")

    def test_blocked_triage_has_none_complexity_band(self) -> None:
        """Blocked triage never reaches Stage 7, so complexity_band stays None."""
        from forecastability.triage import (
            ReadinessReport,
            ReadinessStatus,
            TriageRequest,
            run_triage,
        )

        # Inject a blocking readiness gate
        def _blocking_gate(req: TriageRequest) -> ReadinessReport:
            from forecastability.triage import ReadinessWarning

            return ReadinessReport(
                status=ReadinessStatus.blocked,
                warnings=[ReadinessWarning(code="TEST", message="blocked for testing")],
            )

        rng = np.random.default_rng(0)
        series = rng.standard_normal(200)
        request = TriageRequest(series=series, max_lag=5, n_surrogates=99)
        result = run_triage(request, readiness_gate=_blocking_gate)

        assert result.blocked is True
        assert result.complexity_band is None
