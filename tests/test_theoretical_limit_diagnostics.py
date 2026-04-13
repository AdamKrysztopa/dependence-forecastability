"""Tests for TheoreticalLimitDiagnostics model and build service."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from forecastability.services.theoretical_limit_diagnostics_service import (
    build_theoretical_limit_diagnostics,
)
from forecastability.triage.models import TriageRequest
from forecastability.triage.run_triage import run_triage
from forecastability.triage.theoretical_limit_diagnostics import TheoreticalLimitDiagnostics


def test_build_returns_model() -> None:
    curve = np.array([0.1, 0.05, 0.02])
    result = build_theoretical_limit_diagnostics(curve)
    assert isinstance(result, TheoreticalLimitDiagnostics)
    assert result.exploitation_ratio_supported is False
    assert len(result.forecastability_ceiling_by_horizon) == 3


def test_ceiling_equals_ami_curve() -> None:
    curve = np.array([0.1, 0.05, 0.02])
    result = build_theoretical_limit_diagnostics(curve)
    np.testing.assert_array_equal(result.forecastability_ceiling_by_horizon, curve)


def test_ceiling_summary_nonempty() -> None:
    curve = np.array([0.1, 0.05, 0.02])
    result = build_theoretical_limit_diagnostics(curve)
    assert isinstance(result.ceiling_summary, str)
    assert len(result.ceiling_summary) > 0


def test_no_warnings_by_default() -> None:
    curve = np.array([0.1, 0.05, 0.02])
    result = build_theoretical_limit_diagnostics(curve)
    assert result.compression_warning is None
    assert result.dpi_warning is None


def test_compression_warning_populated() -> None:
    curve = np.array([0.1, 0.05, 0.02])
    result = build_theoretical_limit_diagnostics(curve, compression_suspected=True)
    assert result.compression_warning is not None
    assert len(result.compression_warning) > 0


def test_dpi_warning_populated() -> None:
    curve = np.array([0.1, 0.05, 0.02])
    result = build_theoretical_limit_diagnostics(curve, dpi_suspected=True)
    assert result.dpi_warning is not None
    assert len(result.dpi_warning) > 0


def test_zero_curve_summary() -> None:
    curve = np.zeros(5)
    result = build_theoretical_limit_diagnostics(curve)
    summary_lower = result.ceiling_summary.lower()
    # Must contain at least one word indicating absence/flatness
    assert any(word in summary_lower for word in ("no", "zero", "flat", "negligible"))


def test_single_horizon() -> None:
    curve = np.array([0.3])
    result = build_theoretical_limit_diagnostics(curve)
    assert isinstance(result, TheoreticalLimitDiagnostics)
    assert len(result.forecastability_ceiling_by_horizon) == 1


def test_immutable_model() -> None:
    curve = np.array([0.1, 0.05])
    result = build_theoretical_limit_diagnostics(curve)
    with pytest.raises(ValidationError):
        result.exploitation_ratio_supported = True  # type: ignore[misc]


def test_integrated_in_triage_result() -> None:
    rng = np.random.default_rng(42)
    series = rng.normal(0, 1, 200)
    request = TriageRequest(series=series, max_lag=5, n_surrogates=99, random_state=42)
    result = run_triage(request)
    assert result.theoretical_limit_diagnostics is not None
    assert isinstance(result.theoretical_limit_diagnostics, TheoreticalLimitDiagnostics)


def test_blocked_triage_returns_none() -> None:
    series = np.array([1.0, 2.0, 3.0])
    request = TriageRequest(series=series, max_lag=5, n_surrogates=9, random_state=42)
    result = run_triage(request)
    assert result.blocked is True
    assert result.theoretical_limit_diagnostics is None
