"""Behavior tests for the Phase 1 extended diagnostic services."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Literal, cast

import numpy as np
import pytest

from forecastability.services.classical_structure_service import compute_classical_structure
from forecastability.services.extended_fingerprint_service import (
    build_extended_forecastability_fingerprint,
)
from forecastability.services.memory_structure_service import compute_memory_structure
from forecastability.services.ordinal_complexity_service import compute_ordinal_complexity
from forecastability.services.spectral_forecastability_service import (
    compute_spectral_forecastability,
)
from forecastability.utils.datasets import generate_ar1, generate_henon_map, generate_white_noise
from forecastability.utils.synthetic import generate_seasonal_periodic


def _clean_sine_wave(*, n_samples: int = 512, period: int = 16) -> np.ndarray:
    """Return a deterministic clean sine wave with a known sample-space period."""
    time_index = np.arange(n_samples, dtype=float)
    return np.sin((2.0 * np.pi * time_index) / float(period))


def _linear_trend_series(*, n_samples: int = 400, random_state: int = 42) -> np.ndarray:
    """Return a deterministic linear trend plus light Gaussian noise."""
    rng = np.random.default_rng(random_state)
    time_index = np.arange(n_samples, dtype=float)
    return 0.08 * time_index + rng.normal(0.0, 0.4, size=n_samples)


def _seasonal_plus_noise(
    *,
    n_samples: int = 512,
    period: int = 16,
    random_state: int = 42,
) -> np.ndarray:
    """Return a moderate seasonal signal with additive noise."""
    rng = np.random.default_rng(random_state)
    return _clean_sine_wave(n_samples=n_samples, period=period) + rng.normal(
        0.0,
        0.45,
        size=n_samples,
    )


def test_spectral_forecastability_orders_sine_seasonal_and_white_noise() -> None:
    """Spectral predictability should rank periodic structure above white noise."""
    white_noise = generate_white_noise(n_samples=512, random_state=7)
    clean_sine = _clean_sine_wave()
    seasonal = _seasonal_plus_noise(random_state=7)

    white_result = compute_spectral_forecastability(white_noise)
    sine_result = compute_spectral_forecastability(clean_sine)
    seasonal_result = compute_spectral_forecastability(seasonal)

    assert sine_result.spectral_entropy < white_result.spectral_entropy
    assert seasonal_result.spectral_entropy < white_result.spectral_entropy
    assert sine_result.spectral_predictability > seasonal_result.spectral_predictability
    assert seasonal_result.spectral_predictability > white_result.spectral_predictability
    assert sine_result.periodicity_hint in {"moderate", "strong"}
    assert any(abs(period - 16) <= 1 for period in sine_result.dominant_periods)


def test_spectral_forecastability_handles_constant_and_short_inputs_with_notes() -> None:
    """Degenerate spectral inputs should return conservative outputs with explicit notes."""
    constant_result = compute_spectral_forecastability(np.ones(32, dtype=float))
    short_result = compute_spectral_forecastability(np.arange(6, dtype=float))

    assert constant_result.periodicity_hint == "none"
    assert any("constant series" in note for note in constant_result.notes)
    assert short_result.spectral_predictability == 0.0
    assert any("too short" in note for note in short_result.notes)


@pytest.mark.parametrize(
    "invoke",
    [
        lambda values: compute_spectral_forecastability(values),
        lambda values: compute_ordinal_complexity(values),
        lambda values: compute_classical_structure(values),
        lambda values: compute_memory_structure(values),
        lambda values: build_extended_forecastability_fingerprint(values),
    ],
)
def test_public_extended_services_reject_non_1d_inputs(
    invoke: Callable[[np.ndarray], object],
) -> None:
    """Public F01-F05 services should reject non-1D inputs instead of flattening them."""
    matrix = np.arange(12, dtype=float).reshape(3, 4)

    with pytest.raises(ValueError, match="values must be a one-dimensional series"):
        invoke(matrix)


def test_spectral_forecastability_rejects_unknown_detrend_mode() -> None:
    """The public spectral API should reject detrend modes outside the supported contract."""
    invalid_detrend = cast(Literal["none", "linear"], "constant")

    with pytest.raises(ValueError, match="detrend must be one of"):
        compute_spectral_forecastability(np.arange(64, dtype=float), detrend=invalid_detrend)


def test_ordinal_complexity_separates_periodic_nonlinear_and_noise_like_series() -> None:
    """Ordinal entropy should distinguish regular and nonlinear structure from white noise."""
    white_noise = generate_white_noise(n_samples=600, random_state=9)
    clean_sine = _clean_sine_wave(n_samples=600, period=12)
    henon = generate_henon_map(n_samples=600)

    white_result = compute_ordinal_complexity(white_noise)
    sine_result = compute_ordinal_complexity(clean_sine)
    henon_result = compute_ordinal_complexity(henon)

    assert white_result.complexity_class == "noise_like"
    assert sine_result.permutation_entropy < white_result.permutation_entropy
    assert sine_result.ordinal_redundancy > white_result.ordinal_redundancy
    assert sine_result.complexity_class != "noise_like"
    assert henon_result.complexity_class in {
        "structured_nonlinear",
        "complex_but_redundant",
    }
    assert henon_result.ordinal_redundancy > white_result.ordinal_redundancy


def test_ordinal_complexity_handles_degenerate_and_short_inputs() -> None:
    """Degenerate ordinal inputs should stay explicit and conservative."""
    constant_result = compute_ordinal_complexity(np.ones(32, dtype=float))
    short_result = compute_ordinal_complexity(
        np.arange(5, dtype=float),
        embedding_dimension=4,
    )

    assert constant_result.complexity_class == "degenerate"
    assert constant_result.ordinal_redundancy == 1.0
    assert any("constant series" in note for note in constant_result.notes)
    assert short_result.complexity_class == "unclear"
    assert any("too short" in note for note in short_result.notes)


def test_ordinal_complexity_rejects_embedding_dimension_below_two() -> None:
    """The ordinal service should reject invalid embedding dimensions at entry."""
    with pytest.raises(ValueError, match="embedding_dimension must be at least 2"):
        compute_ordinal_complexity(np.arange(16, dtype=float), embedding_dimension=1)


def test_ordinal_complexity_uses_explicit_tie_policy_for_discrete_inputs() -> None:
    """Rounded and binary noise should report tie-aware ordinal handling explicitly."""
    white_noise = generate_white_noise(n_samples=600, random_state=11)
    rounded_noise = np.round(white_noise, 0)
    binary_noise = np.where(
        generate_white_noise(n_samples=600, random_state=13) >= 0.0,
        1.0,
        0.0,
    )

    white_result = compute_ordinal_complexity(white_noise)
    rounded_result = compute_ordinal_complexity(rounded_noise)
    binary_result = compute_ordinal_complexity(binary_noise)

    assert not any("average-rank policy" in note for note in white_result.notes)
    assert any("average-rank policy" in note for note in rounded_result.notes)
    assert any("average-rank policy" in note for note in binary_result.notes)
    assert rounded_result.permutation_entropy < white_result.permutation_entropy
    assert binary_result.permutation_entropy < white_result.permutation_entropy
    assert binary_result.ordinal_redundancy > white_result.ordinal_redundancy


def test_classical_structure_detects_autocorrelation_trend_and_seasonality() -> None:
    """Classical summaries should highlight AR, trend, and seasonal archetypes."""
    ar1 = generate_ar1(n_samples=500, phi=0.8, random_state=5)
    white_noise = generate_white_noise(n_samples=500, random_state=5)
    trend = _linear_trend_series(n_samples=500, random_state=5)
    seasonal = generate_seasonal_periodic(n=500, period=12, seed=5)

    ar1_result = compute_classical_structure(ar1, max_lag=20)
    white_result = compute_classical_structure(white_noise, max_lag=20)
    trend_result = compute_classical_structure(trend, max_lag=20)
    trend_period_result = compute_classical_structure(trend, period=12, max_lag=20)
    seasonal_result = compute_classical_structure(seasonal, period=12, max_lag=20)
    no_period_result = compute_classical_structure(seasonal, period=None, max_lag=20)

    assert ar1_result.acf1 is not None and ar1_result.acf1 > 0.5
    assert white_result.acf1 is not None and abs(white_result.acf1) < 0.2
    assert (white_result.trend_strength or 0.0) < 0.1
    assert trend_result.trend_strength is not None and trend_result.trend_strength > 0.95
    assert trend_result.stationarity_hint == "trend_nonstationary"
    assert trend_period_result.seasonal_strength is not None
    assert trend_period_result.seasonal_strength < 0.2
    assert trend_period_result.stationarity_hint == "trend_nonstationary"
    assert seasonal_result.seasonal_strength is not None and seasonal_result.seasonal_strength > 0.4
    assert seasonal_result.stationarity_hint == "seasonal"
    assert no_period_result.seasonal_strength is None


def test_classical_structure_handles_constant_inputs_safely() -> None:
    """Constant series should not emit misleading classical structure values."""
    result = compute_classical_structure(np.ones(64, dtype=float), period=12)

    assert result.acf1 is None
    assert result.trend_strength is None
    assert result.residual_variance_ratio is None
    assert any("constant series" in note for note in result.notes)


def test_memory_structure_distinguishes_short_anti_and_persistent_regimes() -> None:
    """DFA should distinguish short memory, anti-persistence, and stronger persistence."""
    white_noise = generate_white_noise(n_samples=1024, random_state=12)
    anti_persistent = generate_ar1(n_samples=1024, phi=-0.8, random_state=12)
    persistent = generate_ar1(n_samples=1024, phi=0.88, random_state=12)

    white_result = compute_memory_structure(white_noise)
    anti_result = compute_memory_structure(anti_persistent)
    persistent_result = compute_memory_structure(persistent)

    assert white_result.memory_type in {"short_memory", "unclear"}
    assert anti_result.memory_type == "anti_persistent"
    assert persistent_result.memory_type in {"persistent", "long_memory_candidate"}
    assert persistent_result.dfa_alpha is not None
    assert white_result.dfa_alpha is not None
    assert persistent_result.dfa_alpha > white_result.dfa_alpha


def test_memory_structure_warns_when_alpha_exceeds_one() -> None:
    """Highly nonstationary inputs should emit an explicit high-alpha warning."""
    random_walk = np.cumsum(generate_white_noise(n_samples=1024, random_state=24))
    result = compute_memory_structure(random_walk)

    assert result.dfa_alpha is not None and result.dfa_alpha > 1.0
    assert result.memory_type == "unclear"
    assert any("exceeds 1.0" in note for note in result.notes)
    assert result.hurst_proxy is None


def test_memory_structure_near_unit_root_stays_conservative() -> None:
    """Near-unit-root alpha above one should not be routed as long memory."""
    near_unit_root = generate_ar1(n_samples=1024, phi=0.92, random_state=2)
    result = compute_memory_structure(near_unit_root)

    assert result.dfa_alpha is not None and result.dfa_alpha > 1.0
    assert result.memory_type == "unclear"
    assert any("exceeds 1.0" in note for note in result.notes)
    assert result.hurst_proxy is None


def test_memory_structure_handles_too_short_inputs() -> None:
    """Short memory inputs should return an unclear result with notes."""
    result = compute_memory_structure(np.arange(12, dtype=float))

    assert result.memory_type == "unclear"
    assert result.scale_range is None
    assert any("too short" in note for note in result.notes)


def test_extended_fingerprint_composes_enabled_services_and_preserves_disabled_none() -> None:
    """The composite fingerprint should include enabled blocks and keep disabled ones as None."""
    seasonal = generate_seasonal_periodic(n=240, period=12, seed=19)
    fingerprint = build_extended_forecastability_fingerprint(
        seasonal,
        max_lag=24,
        period=12,
    )
    partial = build_extended_forecastability_fingerprint(
        seasonal,
        max_lag=24,
        period=None,
        include_ami_geometry=False,
        include_memory=False,
    )

    assert fingerprint.information_geometry is not None
    assert fingerprint.spectral is not None
    assert fingerprint.ordinal is not None
    assert fingerprint.classical is not None
    assert fingerprint.memory is not None
    assert fingerprint.classical.seasonal_strength is not None

    payload = json.loads(partial.model_dump_json())
    assert payload["information_geometry"] is None
    assert payload["memory"] is None
    assert payload["classical"]["seasonal_strength"] is None


def test_extended_fingerprint_degrades_gracefully_when_ami_geometry_is_infeasible() -> None:
    """Short or degenerate inputs should still return the non-AMI diagnostic blocks."""
    short_series = _clean_sine_wave(n_samples=48, period=12)
    fingerprint = build_extended_forecastability_fingerprint(short_series, max_lag=24, period=12)

    assert fingerprint.information_geometry is None
    assert fingerprint.spectral is not None
    assert fingerprint.ordinal is not None
    assert fingerprint.classical is not None
    assert fingerprint.memory is not None


def test_extended_fingerprint_omits_ami_geometry_for_constant_series() -> None:
    """Constant inputs should omit AMI geometry without depending on exception text."""
    constant_series = np.ones(96, dtype=float)
    fingerprint = build_extended_forecastability_fingerprint(constant_series, max_lag=24, period=12)

    assert fingerprint.information_geometry is None
    assert fingerprint.spectral is not None
    assert fingerprint.ordinal is not None
    assert fingerprint.classical is not None
    assert fingerprint.memory is not None


def test_extended_fingerprint_validates_max_lag_before_optional_block_selection() -> None:
    """Shared lag validation should run even when the lag-aware blocks are disabled."""
    with pytest.raises(ValueError, match="max_lag must be positive"):
        build_extended_forecastability_fingerprint(
            np.arange(64, dtype=float),
            max_lag=0,
            include_ami_geometry=False,
            include_classical=False,
        )


def test_extended_fingerprint_validates_period_before_optional_block_selection() -> None:
    """Shared period validation should run even when the classical block is disabled."""
    with pytest.raises(ValueError, match="period must be greater than 1 when provided"):
        build_extended_forecastability_fingerprint(
            np.arange(64, dtype=float),
            period=1,
            include_classical=False,
        )
