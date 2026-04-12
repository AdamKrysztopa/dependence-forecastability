"""Tests for Largest Lyapunov Exponent (F5) — model, helpers, service, and triage integration."""

from __future__ import annotations

import math

import numpy as np
import pytest

from forecastability.scorers import _embed_series, _estimate_lle_rosenstein
from forecastability.services.lyapunov_service import build_largest_lyapunov_exponent
from forecastability.triage.lyapunov import LargestLyapunovExponentResult

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _sine_series(n: int = 500) -> np.ndarray:
    """Pure sine wave — periodic (λ ≈ 0 or slightly negative)."""
    t = np.linspace(0, 4 * np.pi, n)
    return np.sin(t)


def _white_noise(n: int = 200) -> np.ndarray:
    """IID standard normal noise."""
    rng = np.random.default_rng(42)
    return rng.standard_normal(n)


def _logistic_series(n: int = 500) -> np.ndarray:
    """Logistic map r=3.9 — chaotic (λ > 0)."""
    x = np.empty(n)
    x[0] = 0.5
    for i in range(1, n):
        x[i] = 3.9 * x[i - 1] * (1.0 - x[i - 1])
    return x


def _ar1_series(phi: float = 0.9, n: int = 300) -> np.ndarray:
    """AR(1) process with given autoregressive coefficient."""
    rng = np.random.default_rng(0)
    eps = rng.standard_normal(n)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + eps[i]
    return x


def _constant_series(n: int = 100) -> np.ndarray:
    """Constant series — edge case for LLE."""
    return np.ones(n)


# ---------------------------------------------------------------------------
# TestLargestLyapunovExponentResult
# ---------------------------------------------------------------------------


class TestLargestLyapunovExponentResult:
    """Frozen Pydantic model contract tests."""

    def _make(self, **overrides: object) -> LargestLyapunovExponentResult:
        defaults: dict[str, object] = {
            "lambda_estimate": 0.5,
            "embedding_dim": 3,
            "delay": 1,
            "evolution_steps": 25,
            "n_embedded_points": 498,
            "interpretation": "Chaotic-like divergence detected",
            "reliability_warning": "EXPERIMENTAL — use with caution",
        }
        defaults.update(overrides)
        return LargestLyapunovExponentResult(**defaults)  # type: ignore[arg-type]

    def test_model_is_frozen(self) -> None:
        from pydantic import ValidationError

        result = self._make()
        with pytest.raises((TypeError, ValidationError)):
            result.lambda_estimate = 0.0  # type: ignore[misc]

    def test_all_fields_present(self) -> None:
        result = self._make()
        assert hasattr(result, "lambda_estimate")
        assert hasattr(result, "embedding_dim")
        assert hasattr(result, "delay")
        assert hasattr(result, "evolution_steps")
        assert hasattr(result, "n_embedded_points")
        assert hasattr(result, "interpretation")
        assert hasattr(result, "reliability_warning")
        assert hasattr(result, "is_experimental")

    def test_is_experimental_always_true(self) -> None:
        result = self._make()
        assert result.is_experimental is True

    def test_nan_lambda_accepted(self) -> None:
        result = self._make(lambda_estimate=float("nan"))
        assert math.isnan(result.lambda_estimate)

    def test_field_types(self) -> None:
        result = self._make()
        assert isinstance(result.lambda_estimate, float)
        assert isinstance(result.embedding_dim, int)
        assert isinstance(result.delay, int)
        assert isinstance(result.evolution_steps, int)
        assert isinstance(result.n_embedded_points, int)
        assert isinstance(result.interpretation, str)
        assert isinstance(result.reliability_warning, str)
        assert isinstance(result.is_experimental, bool)


# ---------------------------------------------------------------------------
# TestEmbedSeries
# ---------------------------------------------------------------------------


class TestEmbedSeries:
    """Tests for the Takens delay embedding helper."""

    def test_correct_shape_default(self) -> None:
        series = np.arange(10.0)
        embedded = _embed_series(series, m=3, tau=1)
        assert embedded.shape == (8, 3)  # N - (m-1)*tau = 10 - 2 = 8

    def test_correct_shape_tau2(self) -> None:
        series = np.arange(20.0)
        embedded = _embed_series(series, m=3, tau=2)
        # N - (m-1)*tau = 20 - 4 = 16
        assert embedded.shape == (16, 3)

    def test_first_row_values(self) -> None:
        series = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        embedded = _embed_series(series, m=3, tau=1)
        np.testing.assert_array_equal(embedded[0], [1.0, 2.0, 3.0])
        np.testing.assert_array_equal(embedded[1], [2.0, 3.0, 4.0])
        np.testing.assert_array_equal(embedded[2], [3.0, 4.0, 5.0])

    def test_too_short_returns_empty(self) -> None:
        series = np.array([1.0, 2.0])
        embedded = _embed_series(series, m=3, tau=1)
        assert embedded.shape == (0, 3)

    def test_m_equals_1(self) -> None:
        series = np.arange(5.0)
        embedded = _embed_series(series, m=1, tau=1)
        assert embedded.shape == (5, 1)

    def test_exact_length(self) -> None:
        # n = m → one embedded point
        series = np.arange(3.0)
        embedded = _embed_series(series, m=3, tau=1)
        assert embedded.shape == (1, 3)


# ---------------------------------------------------------------------------
# TestEstimateLLERosenstein
# ---------------------------------------------------------------------------


class TestEstimateLLERosenstein:
    """Tests for the core Rosenstein LLE estimation."""

    def _estimate(self, series: np.ndarray, *, m: int = 3, tau: int = 1) -> float:
        n = len(series)
        embedded = _embed_series(series, m=m, tau=tau)
        theiler = max(1, int(0.1 * n))
        steps = max(1, n // 20)
        return _estimate_lle_rosenstein(embedded, theiler_window=theiler, evolution_steps=steps)

    def test_sine_series_finite(self) -> None:
        lam = self._estimate(_sine_series(n=500))
        assert math.isfinite(lam)

    def test_white_noise_finite(self) -> None:
        lam = self._estimate(_white_noise(n=200))
        assert math.isfinite(lam)

    def test_logistic_map_positive(self) -> None:
        """Logistic map is chaotic — LLE should be positive."""
        lam = self._estimate(_logistic_series(n=500))
        assert math.isfinite(lam)
        assert lam > 0.0, f"Expected positive LLE for chaotic logistic map, got {lam}"

    def test_ar1_finite(self) -> None:
        lam = self._estimate(_ar1_series(phi=0.9, n=300))
        assert math.isfinite(lam)

    def test_constant_series_no_crash(self) -> None:
        lam = self._estimate(_constant_series(n=100))
        # Constant series → all distances 0 → nan or finite without error
        assert isinstance(lam, float)

    def test_too_few_embedded_points_returns_nan(self) -> None:
        series = np.arange(5.0)
        embedded = _embed_series(series, m=3, tau=1)
        lam = _estimate_lle_rosenstein(embedded, theiler_window=1, evolution_steps=2)
        assert math.isnan(lam)


# ---------------------------------------------------------------------------
# TestBuildLargestLyapunovExponent
# ---------------------------------------------------------------------------


class TestBuildLargestLyapunovExponent:
    """Service contract and safety tests."""

    def test_never_raises_on_sine(self) -> None:
        result = build_largest_lyapunov_exponent(_sine_series(500))
        assert isinstance(result, LargestLyapunovExponentResult)

    def test_never_raises_on_constant(self) -> None:
        result = build_largest_lyapunov_exponent(_constant_series(100))
        assert isinstance(result, LargestLyapunovExponentResult)

    def test_never_raises_on_very_short(self) -> None:
        result = build_largest_lyapunov_exponent(np.array([1.0, 2.0, 3.0]))
        assert isinstance(result, LargestLyapunovExponentResult)
        assert math.isnan(result.lambda_estimate)

    def test_all_fields_populated(self) -> None:
        result = build_largest_lyapunov_exponent(_logistic_series(200))
        assert result.embedding_dim == 3
        assert result.delay == 1
        assert result.evolution_steps > 0
        assert result.n_embedded_points > 0
        assert len(result.interpretation) > 0
        assert len(result.reliability_warning) > 0

    def test_is_experimental_always_true(self) -> None:
        for series in [_sine_series(100), _white_noise(100), _constant_series(50)]:
            result = build_largest_lyapunov_exponent(series)
            assert result.is_experimental is True

    def test_reliability_warning_always_present(self) -> None:
        result = build_largest_lyapunov_exponent(_ar1_series(phi=0.7, n=200))
        assert isinstance(result.reliability_warning, str)
        assert len(result.reliability_warning) > 0

    def test_custom_embedding_params(self) -> None:
        result = build_largest_lyapunov_exponent(
            _sine_series(300),
            embedding_dim=4,
            delay=2,
        )
        assert result.embedding_dim == 4
        assert result.delay == 2

    def test_chaotic_lambda_positive(self) -> None:
        result = build_largest_lyapunov_exponent(_logistic_series(500))
        assert math.isfinite(result.lambda_estimate)
        assert result.lambda_estimate > 0.0


# ---------------------------------------------------------------------------
# TestTriageResultLargestLyapunovExponent
# ---------------------------------------------------------------------------


class TestTriageResultLargestLyapunovExponent:
    """Integration test: run_triage populates LLE on the result."""

    def test_run_triage_populates_lle(self) -> None:
        from forecastability.triage import TriageRequest, run_triage

        rng = np.random.default_rng(7)
        series = rng.standard_normal(300)
        request = TriageRequest(series=series, max_lag=20, n_surrogates=99, random_state=42)
        result = run_triage(request)
        assert result.largest_lyapunov_exponent is not None

    def test_triage_lle_is_experimental(self) -> None:
        from forecastability.triage import TriageRequest, run_triage

        rng = np.random.default_rng(8)
        series = rng.standard_normal(300)
        request = TriageRequest(series=series, max_lag=20, n_surrogates=99, random_state=42)
        result = run_triage(request)
        assert result.largest_lyapunov_exponent is not None
        assert result.largest_lyapunov_exponent.is_experimental is True

    def test_lle_result_has_interpretation(self) -> None:
        from forecastability.triage import TriageRequest, run_triage

        rng = np.random.default_rng(9)
        series = rng.standard_normal(300)
        request = TriageRequest(series=series, max_lag=20, n_surrogates=99, random_state=42)
        result = run_triage(request)
        lle = result.largest_lyapunov_exponent
        assert lle is not None
        assert len(lle.interpretation) > 0
        assert len(lle.reliability_warning) > 0
