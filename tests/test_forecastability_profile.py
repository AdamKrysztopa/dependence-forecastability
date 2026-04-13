"""Tests for ForecastabilityProfile model and build_forecastability_profile service."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from forecastability.services.forecastability_profile_service import build_forecastability_profile

# ---------------------------------------------------------------------------
# Group 1 — build_forecastability_profile unit tests
# ---------------------------------------------------------------------------


def test_monotone_decay_profile() -> None:
    raw = np.array([0.30, 0.20, 0.15, 0.10, 0.05])
    profile = build_forecastability_profile(raw, default_epsilon=0.05)

    assert profile.horizons == [1, 2, 3, 4, 5]
    assert profile.peak_horizon == 1
    assert not profile.is_non_monotone
    assert profile.informative_horizons == [1, 2, 3, 4, 5]
    assert profile.avoid_horizons == []


def test_seasonal_non_monotone_profile() -> None:
    raw = np.array([0.10, 0.05, 0.02, 0.08, 0.06, 0.01])
    profile = build_forecastability_profile(raw, default_epsilon=0.04)

    assert profile.is_non_monotone
    assert 4 in profile.informative_horizons  # 0.08 >= 0.04
    assert 3 not in profile.informative_horizons  # 0.02 < 0.04


def test_profile_with_surrogates() -> None:
    raw = np.array([0.30, 0.20, 0.10, 0.05, 0.02])
    sig_lags = np.array([0, 1])  # 0-based → horizons 1 and 2
    profile = build_forecastability_profile(raw, sig_raw_lags=sig_lags)

    assert profile.epsilon == pytest.approx(0.20)
    assert profile.informative_horizons == [1, 2]
    assert profile.avoid_horizons == [3, 4, 5]


def test_no_significant_lags() -> None:
    raw = np.array([0.03, 0.02, 0.01])
    sig_lags = np.array([], dtype=int)
    profile = build_forecastability_profile(raw, sig_raw_lags=sig_lags)

    assert profile.informative_horizons == []
    assert profile.avoid_horizons == [1, 2, 3]
    assert "NONE" in profile.model_now


def test_single_element_curve() -> None:
    raw = np.array([0.5])
    profile = build_forecastability_profile(raw)

    assert profile.horizons == [1]
    assert profile.peak_horizon == 1


def test_all_zero_curve() -> None:
    raw = np.zeros(5)
    profile = build_forecastability_profile(raw, default_epsilon=0.05)

    assert profile.informative_horizons == []
    assert "NONE" in profile.model_now


def test_high_signal_model_now() -> None:
    raw = np.array([0.50, 0.40, 0.30])
    profile = build_forecastability_profile(raw, default_epsilon=0.05)

    assert "HIGH" in profile.model_now


def test_medium_signal_model_now() -> None:
    raw = np.array([0.10, 0.08, 0.06])
    profile = build_forecastability_profile(raw, default_epsilon=0.05)

    assert "MEDIUM" in profile.model_now


def test_profile_is_frozen() -> None:
    raw = np.array([0.1, 0.2])
    profile = build_forecastability_profile(raw)

    with pytest.raises(ValidationError):
        profile.epsilon = 0.99


# ---------------------------------------------------------------------------
# Group 2 — run_triage integration tests
# ---------------------------------------------------------------------------


def test_run_triage_attaches_profile_with_surrogates() -> None:
    from forecastability.datasets import generate_ar1
    from forecastability.triage import run_triage
    from forecastability.triage.models import TriageRequest

    series = generate_ar1(n_samples=300, phi=0.7, random_state=0)
    request = TriageRequest(series=series, n_surrogates=99, random_state=42, max_lag=20)
    result = run_triage(request)

    assert result.forecastability_profile is not None
    profile = result.forecastability_profile
    assert len(profile.horizons) == 20
    assert profile.peak_horizon >= 1
    assert profile.summary


def test_run_triage_white_noise_profile_structure() -> None:
    from forecastability.datasets import generate_white_noise
    from forecastability.triage import run_triage
    from forecastability.triage.models import TriageRequest

    series = generate_white_noise(n_samples=300, random_state=42)
    request = TriageRequest(series=series, n_surrogates=99, random_state=42, max_lag=20)
    result = run_triage(request)

    assert result.forecastability_profile is not None
    profile = result.forecastability_profile
    assert profile.horizons == list(range(1, 21))
    assert len(profile.informative_horizons) + len(profile.avoid_horizons) == 20
    assert profile.peak_horizon in range(1, 21)
    assert profile.summary


def test_run_triage_blocked_result_profile_is_none() -> None:
    from forecastability.triage import run_triage
    from forecastability.triage.models import TriageRequest

    short_series = np.array([1.0, 2.0, 3.0])
    result = run_triage(TriageRequest(series=short_series, max_lag=40))

    if result.blocked:
        assert result.forecastability_profile is None
