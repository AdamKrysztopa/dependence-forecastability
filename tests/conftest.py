"""Shared deterministic triage fixtures for contract and parity tests."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.datasets import generate_ar1
from forecastability.triage.models import TriageRequest, TriageResult
from forecastability.triage.run_triage import run_triage

_TRIAGE_AR1_PHI = 0.85
_TRIAGE_MAX_LAG = 20
_TRIAGE_N_SURROGATES = 99
_TRIAGE_RANDOM_STATE = 42
_TRIAGE_SERIES_LENGTH = 120
_BLOCKED_SERIES_LENGTH = 30
_BLOCKED_MAX_LAG = 40


@pytest.fixture(scope="session")
def deterministic_triage_series() -> list[float]:
    """Return a deterministic AR(1) series used across interface tests."""
    series = generate_ar1(
        n_samples=_TRIAGE_SERIES_LENGTH,
        phi=_TRIAGE_AR1_PHI,
        random_state=_TRIAGE_RANDOM_STATE,
    )
    return series.astype(np.float64).tolist()


@pytest.fixture(scope="session")
def deterministic_blocked_series() -> list[float]:
    """Return a deterministic short series that is blocked by readiness checks."""
    series = generate_ar1(
        n_samples=_BLOCKED_SERIES_LENGTH,
        phi=_TRIAGE_AR1_PHI,
        random_state=_TRIAGE_RANDOM_STATE,
    )
    return series.astype(np.float64).tolist()


@pytest.fixture(scope="session")
def deterministic_triage_request(
    deterministic_triage_series: list[float],
) -> TriageRequest:
    """Return a shared univariate triage request."""
    return TriageRequest(
        series=np.asarray(deterministic_triage_series, dtype=np.float64),
        max_lag=_TRIAGE_MAX_LAG,
        n_surrogates=_TRIAGE_N_SURROGATES,
        random_state=_TRIAGE_RANDOM_STATE,
    )


@pytest.fixture(scope="session")
def deterministic_blocked_request(
    deterministic_blocked_series: list[float],
) -> TriageRequest:
    """Return a shared request that always short-circuits as blocked."""
    return TriageRequest(
        series=np.asarray(deterministic_blocked_series, dtype=np.float64),
        max_lag=_BLOCKED_MAX_LAG,
        n_surrogates=_TRIAGE_N_SURROGATES,
        random_state=_TRIAGE_RANDOM_STATE,
    )


@pytest.fixture(scope="session")
def deterministic_triage_result(
    deterministic_triage_request: TriageRequest,
) -> TriageResult:
    """Return the deterministic triage result for shared parity assertions."""
    return run_triage(deterministic_triage_request)
