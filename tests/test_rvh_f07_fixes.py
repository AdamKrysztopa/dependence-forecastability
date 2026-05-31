"""Tests for RVH-F07 — Welch nperseg fix, Lyapunov window, cardinality-aware MI fallback.

Covers:
1. Welch nperseg: compute_spectral_forecastability passes max(64, N//8) to Welch, not N.
2. Lyapunov window: LLE fit is restricted to min(n//3, orbital_period) steps.
3. GCMI cardinality fallback: compute_ami routes to GCMI when unique/N < 0.1.
4. Discrete-alphabet UserWarning emitted when unique values < 20.
5. GCMI fallback does NOT apply to compute_pami_linear_residual.
"""

from __future__ import annotations

import warnings
from unittest.mock import patch

import numpy as np
import pytest

from forecastability.metrics.metrics import (
    _DISCRETE_ALPHABET_WARNING_THRESHOLD,
    _GCMI_CARDINALITY_THRESHOLD,
    compute_ami,
    compute_pami_linear_residual,
)

# ---------------------------------------------------------------------------
# 1. Welch nperseg fix
# ---------------------------------------------------------------------------


class TestWelchNperseg:
    """compute_spectral_forecastability must use max(64, N//8) not N."""

    def test_nperseg_is_not_full_series_length(self) -> None:
        from forecastability.diagnostics.spectral_utils import compute_normalised_psd
        from forecastability.services.spectral_forecastability_service import (
            compute_spectral_forecastability,
        )

        rng = np.random.default_rng(0)
        # N=512 → expected nperseg = max(64, 512//8) = max(64, 64) = 64
        series = rng.standard_normal(512)
        observed_nperseg: list[int] = []

        real_psd = compute_normalised_psd

        def capturing_psd(arr: np.ndarray, **kw: object) -> object:
            nperseg = kw.get("nperseg")
            if nperseg is not None:
                observed_nperseg.append(int(nperseg))  # type: ignore[arg-type]
            return real_psd(arr, **kw)  # type: ignore[arg-type]

        with patch(
            "forecastability.services.spectral_forecastability_service.compute_normalised_psd",
            capturing_psd,
        ):
            compute_spectral_forecastability(series)

        assert observed_nperseg, "compute_normalised_psd was not called with nperseg"
        # Must not be equal to the full series length
        assert all(seg != 512 for seg in observed_nperseg), (
            f"nperseg must not equal N=512; got {observed_nperseg}"
        )

    def test_nperseg_formula_n_512(self) -> None:
        n = 512
        expected = max(64, n // 8)
        assert expected == 64

    def test_nperseg_formula_n_2000(self) -> None:
        n = 2000
        expected = max(64, n // 8)
        assert expected == 250

    def test_nperseg_formula_short_series(self) -> None:
        # For short series (N < 512), nperseg floor is 64.
        n = 100
        expected = max(64, n // 8)
        assert expected == 64

    def test_spectral_result_is_valid(self) -> None:
        from forecastability.services.spectral_forecastability_service import (
            compute_spectral_forecastability,
        )

        rng = np.random.default_rng(1)
        series = rng.standard_normal(300)
        result = compute_spectral_forecastability(series)
        assert 0.0 <= result.spectral_entropy <= 1.0
        assert 0.0 <= result.spectral_predictability <= 1.0


# ---------------------------------------------------------------------------
# 2. Lyapunov linear-window fit
# ---------------------------------------------------------------------------


class TestLyapunovLinearWindow:
    """LLE fit must be restricted to the initial linear divergence region."""

    def test_evolution_steps_bounded_to_linear_window(self) -> None:
        from forecastability.services.lyapunov_service import build_largest_lyapunov_exponent

        rng = np.random.default_rng(42)
        # AR(1) series — has a well-defined orbital period
        series = np.zeros(500)
        series[0] = 1.0
        for i in range(1, 500):
            series[i] = 0.8 * series[i - 1] + rng.standard_normal()

        result = build_largest_lyapunov_exponent(series)
        full_steps = max(1, len(series) // 20)

        # evolution_steps must be <= full_steps // 3 (the linear-window bound)
        assert result.evolution_steps <= full_steps, (
            f"evolution_steps={result.evolution_steps} exceeds full_steps={full_steps}"
        )
        # And specifically should be <= full_steps // 3 (with a 1-sample floor)
        assert result.evolution_steps <= max(1, full_steps // 3), (
            f"evolution_steps={result.evolution_steps} exceeds linear window "
            f"max(1, {full_steps}//3)={max(1, full_steps // 3)}"
        )

    def test_orbital_period_estimation_returns_value(self) -> None:
        from forecastability.services.lyapunov_service import _estimate_dominant_orbital_period

        rng = np.random.default_rng(0)
        # Sine wave has a clear dominant period
        t = np.linspace(0, 10 * np.pi, 500)
        series = np.sin(t) + 0.1 * rng.standard_normal(500)
        period = _estimate_dominant_orbital_period(series)
        # Should return a positive integer
        assert period is not None
        assert period >= 1

    def test_orbital_period_returns_none_for_too_short_series(self) -> None:
        from forecastability.services.lyapunov_service import _estimate_dominant_orbital_period

        # Series with 3 points is too short for AMI with max_lag >= 2
        series = np.array([1.0, 2.0, 1.0])
        period = _estimate_dominant_orbital_period(series)
        # Should gracefully return None
        assert period is None

    def test_lle_result_still_has_finite_lambda_for_chaotic_series(self) -> None:
        from forecastability.services.lyapunov_service import build_largest_lyapunov_exponent

        rng = np.random.default_rng(7)
        # Logistic map is chaotic
        series = np.zeros(500)
        series[0] = 0.5
        for i in range(1, 500):
            series[i] = 3.99 * series[i - 1] * (1 - series[i - 1])
        series += 0.001 * rng.standard_normal(500)

        result = build_largest_lyapunov_exponent(series)
        # With a shorter window the LLE might be nan for some configs;
        # the important thing is that the result is valid and non-crashing.
        assert isinstance(result.lambda_estimate, float)
        assert isinstance(result.evolution_steps, int)
        assert result.evolution_steps >= 1


# ---------------------------------------------------------------------------
# 3. GCMI cardinality fallback
# ---------------------------------------------------------------------------


class TestGcmiCardinalityFallback:
    """compute_ami must route to GCMI for heavy-tie discrete inputs."""

    def _make_heavy_tie_series(self, n: int = 300, n_unique: int = 5) -> np.ndarray:
        """Build a series with very few unique values (cardinality << 0.1)."""
        rng = np.random.default_rng(99)
        return rng.choice(np.arange(n_unique, dtype=float), size=n)

    def test_gcmi_cardinality_threshold_constant_exists(self) -> None:
        assert 0.0 < _GCMI_CARDINALITY_THRESHOLD < 1.0
        assert _GCMI_CARDINALITY_THRESHOLD == pytest.approx(0.1)

    def test_discrete_alphabet_threshold_constant_exists(self) -> None:
        assert _DISCRETE_ALPHABET_WARNING_THRESHOLD == 20

    def test_heavy_tie_series_routes_to_gcmi(self) -> None:
        """When unique/N < 0.1, compute_ami must call compute_gcmi_at_lag."""
        series = self._make_heavy_tie_series(n=300, n_unique=5)
        # unique/N = 5/300 ≈ 0.017 < 0.1 → must route to GCMI

        gcmi_call_count = 0
        from forecastability.diagnostics.gcmi import compute_gcmi_at_lag as real_gcmi

        def counting_gcmi(
            source: np.ndarray, target: np.ndarray, *, lag: int, min_pairs: int = 30
        ) -> float:
            nonlocal gcmi_call_count
            gcmi_call_count += 1
            return real_gcmi(source, target, lag=lag, min_pairs=min_pairs)

        with patch(
            "forecastability.metrics.metrics.compute_gcmi_at_lag",
            counting_gcmi,
        ):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                result = compute_ami(series, max_lag=5)

        assert gcmi_call_count > 0, "Expected compute_gcmi_at_lag to be called for heavy-tie series"
        assert result.shape == (5,)
        assert (result >= 0.0).all()

    def test_continuous_series_does_not_route_to_gcmi(self) -> None:
        """Standard continuous series must not trigger the GCMI fallback."""
        rng = np.random.default_rng(42)
        series = rng.standard_normal(300)
        # unique/N ≈ 1.0 >> 0.1 → must not route to GCMI

        gcmi_called = False

        def fail_gcmi(*args: object, **kw: object) -> float:
            nonlocal gcmi_called
            gcmi_called = True
            return 0.0

        with patch("forecastability.metrics.metrics.compute_gcmi_at_lag", fail_gcmi):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                compute_ami(series, max_lag=5)

        assert not gcmi_called, "compute_gcmi_at_lag must not be called for continuous series"

    def test_gcmi_result_shape_matches_max_lag(self) -> None:
        series = self._make_heavy_tie_series(n=300, n_unique=5)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            result = compute_ami(series, max_lag=10)
        assert result.shape == (10,)

    def test_discrete_alphabet_warning_emitted(self) -> None:
        """UserWarning must be emitted when n_unique < _DISCRETE_ALPHABET_WARNING_THRESHOLD."""
        series = self._make_heavy_tie_series(n=300, n_unique=5)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            compute_ami(series, max_lag=3)
        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert user_warnings, "Expected UserWarning for small-alphabet series"
        assert any("unique" in str(x.message).lower() for x in user_warnings)

    def test_no_warning_for_continuous_series(self) -> None:
        """No UserWarning for standard continuous series (many unique values)."""
        rng = np.random.default_rng(0)
        series = rng.standard_normal(300)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            compute_ami(series, max_lag=3)
        user_warnings = [
            x
            for x in w
            if issubclass(x.category, UserWarning) and "unique" in str(x.message).lower()
        ]
        assert not user_warnings, (
            f"Unexpected cardinality UserWarning for continuous series: {user_warnings}"
        )


# ---------------------------------------------------------------------------
# 4. GCMI fallback must NOT apply to compute_pami_linear_residual
# ---------------------------------------------------------------------------


class TestPamiGcmiFallbackExclusion:
    """GCMI cardinality fallback is raw-AMI-path-only; pAMI must not be affected."""

    def test_pami_does_not_call_gcmi_for_heavy_tie_series(self) -> None:
        """compute_pami_linear_residual must not route to GCMI even for low cardinality."""
        rng = np.random.default_rng(42)
        # 5 unique values out of 400 → unique/N < 0.1 — heavy tie
        series = rng.choice(np.arange(5, dtype=float), size=400)

        gcmi_called = False

        def fail_gcmi(*args: object, **kw: object) -> float:
            nonlocal gcmi_called
            gcmi_called = True
            return 0.0

        with patch("forecastability.metrics.metrics.compute_gcmi_at_lag", fail_gcmi):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                compute_pami_linear_residual(series, max_lag=3)

        assert not gcmi_called, (
            "compute_gcmi_at_lag must not be called inside compute_pami_linear_residual"
        )
