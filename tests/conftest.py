"""Shared deterministic triage fixtures for contract and parity tests."""

from __future__ import annotations

from collections.abc import Generator

import numpy as np
import pytest

from forecastability.triage.models import TriageRequest, TriageResult
from forecastability.use_cases.run_triage import run_triage
from forecastability.utils.datasets import generate_ar1

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


@pytest.fixture(autouse=True)
def _teardown_loky_executor() -> Generator[None, None, None]:
    """Shut down any reusable joblib/loky executor after each test.

    pytest-xdist workers may hang at teardown if a joblib ReusableExecutor
    spawned by a test (via ``n_jobs > 1``) is still alive when the worker
    exits.  Shutting it down eagerly after every test keeps workers clean.
    ``wait=True`` ensures loky child processes are fully dead (not just
    signalled) before the xdist worker proceeds to the next test or exits.
    """
    yield
    try:
        from joblib.externals.loky import get_reusable_executor  # type: ignore[import-untyped]

        get_reusable_executor().shutdown(wait=True, kill_workers=True)
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture(scope="session", autouse=True)
def _teardown_loky_executor_session() -> Generator[None, None, None]:
    """Session-level loky cleanup run once at the end of each xdist worker.

    Belt-and-suspenders companion to ``_teardown_loky_executor``: ensures
    that even if a test creates a fresh executor after the last
    function-scoped teardown, the session-level fixture still shuts it down
    before the worker process exits.
    """
    yield
    try:
        from joblib.externals.loky import get_reusable_executor  # type: ignore[import-untyped]

        get_reusable_executor().shutdown(wait=True, kill_workers=True)
    except Exception:  # noqa: BLE001
        pass
