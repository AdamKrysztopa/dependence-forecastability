"""Focused tests for the deterministic extended forecastability router."""

from __future__ import annotations

import numpy as np

from forecastability.services.extended_fingerprint_service import (
    build_extended_forecastability_fingerprint,
)
from forecastability.services.extended_forecastability_profile_service import (
    build_extended_forecastability_profile,
)
from forecastability.triage import (
    ExtendedForecastabilityFingerprint,
    MemoryStructureResult,
    OrdinalComplexityResult,
    SpectralForecastabilityResult,
)
from forecastability.utils.datasets import generate_ar1, generate_white_noise


def _clean_sine_wave(*, n_samples: int = 512, period: int = 16) -> np.ndarray:
    """Return a deterministic clean sine wave with a known period."""
    time_index = np.arange(n_samples, dtype=float)
    return np.sin((2.0 * np.pi * time_index) / float(period))


def _linear_trend_series(*, n_samples: int = 400, random_state: int = 42) -> np.ndarray:
    """Return a deterministic linear trend with light Gaussian noise."""
    rng = np.random.default_rng(random_state)
    time_index = np.arange(n_samples, dtype=float)
    return 0.08 * time_index + rng.normal(0.0, 0.4, size=n_samples)


def _mixed_signal_series(*, n_samples: int = 512, period: int = 16) -> np.ndarray:
    """Return a deterministic mixed signal with AR, seasonal, and trend structure."""
    seasonal = _clean_sine_wave(n_samples=n_samples, period=period)
    ar_component = generate_ar1(n_samples=n_samples, phi=0.75, random_state=9)
    trend = np.linspace(0.0, 4.0, num=n_samples, dtype=float)
    return 0.8 * seasonal + 0.4 * ar_component + 0.2 * trend


def _diagnostic_only_fingerprint(
    *,
    spectral: SpectralForecastabilityResult | None = None,
    ordinal: OrdinalComplexityResult | None = None,
    memory: MemoryStructureResult | None = None,
) -> ExtendedForecastabilityFingerprint:
    """Build a minimal fingerprint for routing-rule regression tests."""
    return ExtendedForecastabilityFingerprint(
        information_geometry=None,
        spectral=spectral,
        ordinal=ordinal,
        classical=None,
        memory=memory,
    )


def test_sine_wave_routes_to_spectral_and_seasonal_candidates() -> None:
    """A clean sine wave should route through the spectral and seasonal arms."""
    fingerprint = build_extended_forecastability_fingerprint(
        _clean_sine_wave(period=16),
        max_lag=24,
        period=16,
    )
    decision = build_extended_forecastability_profile(fingerprint)

    assert "spectral_concentration" in decision.profile.predictability_sources
    assert "seasonality" in decision.profile.predictability_sources
    assert "harmonic_regression" in decision.profile.recommended_model_families
    assert "tbats" in decision.profile.recommended_model_families
    assert decision.profile.explanation[0].startswith("AMI-first view:")


def test_ar1_routes_to_lag_driven_candidates() -> None:
    """A strong AR(1) signal should route to autoregressive families."""
    fingerprint = build_extended_forecastability_fingerprint(
        generate_ar1(n_samples=512, phi=0.85, random_state=7),
        max_lag=24,
    )
    decision = build_extended_forecastability_profile(fingerprint)

    assert decision.profile.predictability_sources[0] == "lag_dependence"
    assert decision.profile.signal_strength in {"medium", "high"}
    assert decision.profile.recommended_model_families[:3] == [
        "arima",
        "ets",
        "linear_state_space",
    ]
    assert "tree_on_lags" in decision.profile.avoid_model_families


def test_trend_signal_routes_to_trend_and_differencing_candidates() -> None:
    """A trend-dominated signal should prefer trend-aware baselines first."""
    fingerprint = build_extended_forecastability_fingerprint(
        _linear_trend_series(),
        max_lag=24,
    )
    decision = build_extended_forecastability_profile(fingerprint)

    assert "trend" in decision.profile.predictability_sources
    assert "differenced_arima" in decision.profile.recommended_model_families
    assert any("Trend strength" in line for line in decision.profile.explanation)


def test_white_noise_routes_to_naive_and_warns_against_expensive_search() -> None:
    """A noise-like signal should stay conservative and avoid expensive search."""
    fingerprint = build_extended_forecastability_fingerprint(
        generate_white_noise(n_samples=512, random_state=13),
        max_lag=24,
    )
    decision = build_extended_forecastability_profile(fingerprint)

    assert decision.profile.predictability_sources == ()
    assert decision.profile.signal_strength == "low"
    assert decision.profile.noise_risk in {"medium", "high"}
    assert decision.profile.recommended_model_families == [
        "naive",
        "seasonal_naive",
        "downscope",
    ]
    assert "tree_on_lags" in decision.profile.avoid_model_families
    assert any("avoid expensive black-box search" in line for line in decision.profile.explanation)


def test_mixed_signal_routes_to_multiple_predictability_sources() -> None:
    """A mixed signal should accumulate multiple deterministic sources."""
    fingerprint = build_extended_forecastability_fingerprint(
        _mixed_signal_series(),
        max_lag=24,
        period=16,
    )
    decision = build_extended_forecastability_profile(fingerprint)

    assert decision.profile.predictability_sources[0] == "lag_dependence"
    assert "seasonality" in decision.profile.predictability_sources
    assert len(decision.profile.predictability_sources) >= 2
    assert "long_memory" not in decision.profile.predictability_sources
    assert decision.metadata["predictability_source_count"] == len(
        decision.profile.predictability_sources
    )


def test_long_memory_is_suppressed_when_spectral_concentration_is_present() -> None:
    """Long-memory routing should not fire when spectral concentration already
    explains structure."""
    fingerprint = _diagnostic_only_fingerprint(
        spectral=SpectralForecastabilityResult(
            spectral_entropy=0.20,
            spectral_predictability=0.80,
            dominant_periods=[12],
            spectral_concentration=0.78,
            periodicity_hint="strong",
            notes=[],
        ),
        memory=MemoryStructureResult(
            dfa_alpha=0.92,
            hurst_proxy=0.92,
            memory_type="long_memory_candidate",
            scale_range=(4, 32),
            notes=[],
        ),
    )

    decision = build_extended_forecastability_profile(fingerprint)

    assert "spectral_concentration" in decision.profile.predictability_sources
    assert "long_memory" not in decision.profile.predictability_sources


def test_long_memory_is_suppressed_when_memory_fit_notes_are_unstable() -> None:
    """Unstable DFA notes should keep long-memory routing from firing."""
    fingerprint = _diagnostic_only_fingerprint(
        memory=MemoryStructureResult(
            dfa_alpha=0.93,
            hurst_proxy=0.93,
            memory_type="long_memory_candidate",
            scale_range=(4, 24),
            notes=["limited scale coverage makes the DFA fit unstable"],
        )
    )

    decision = build_extended_forecastability_profile(fingerprint)

    assert "long_memory" not in decision.profile.predictability_sources


def test_ordinal_redundancy_without_lag_support_stays_descriptive() -> None:
    """Ordinal redundancy without AMI geometry should remain descriptive-only."""
    fingerprint = _diagnostic_only_fingerprint(
        ordinal=OrdinalComplexityResult(
            permutation_entropy=0.35,
            weighted_permutation_entropy=0.33,
            ordinal_redundancy=0.65,
            embedding_dimension=3,
            delay=1,
            complexity_class="structured_nonlinear",
            notes=[],
        )
    )

    decision = build_extended_forecastability_profile(fingerprint)

    assert decision.profile.predictability_sources == ("ordinal_redundancy",)
    assert "tree_on_lags" not in decision.profile.recommended_model_families
    assert decision.profile.avoid_model_families == []
    assert decision.metadata["descriptive_only"] is True
    assert "unavailable" in decision.profile.summary
    assert decision.metadata["has_nonlinear_followup"] is False
    assert any(
        "without sufficient AMI/lag support" in line for line in decision.profile.explanation
    )
