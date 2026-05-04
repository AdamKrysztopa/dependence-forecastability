"""Focused tests for the public extended forecastability use case."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import typing
from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest
from numpy.typing import ArrayLike

import forecastability
import forecastability.triage as triage
from forecastability.triage import ExtendedForecastabilityAnalysisResult
from forecastability.use_cases import run_extended_forecastability_analysis


def _seasonal_signal(*, n_samples: int = 256, period: int = 12) -> np.ndarray:
    """Return a deterministic seasonal signal with light noise."""
    rng = np.random.default_rng(21)
    time_index = np.arange(n_samples, dtype=float)
    signal = np.sin((2.0 * np.pi * time_index) / float(period))
    return signal + rng.normal(0.0, 0.1, size=n_samples)


def _run_lazy_import_probe() -> dict[str, bool]:
    """Measure stable-root import behavior in a fresh Python process."""
    probe = textwrap.dedent(
        """
        import json
        import sys

        module_name = "forecastability.use_cases.run_extended_forecastability_analysis"

        import forecastability
        import forecastability.triage
        import forecastability.use_cases

        payload = {
            "loaded_after_roots": module_name in sys.modules,
        }
        resolved = forecastability.run_extended_forecastability_analysis
        payload["loaded_after_attr"] = module_name in sys.modules
        resolved([0.0] * 64, max_lag=12, period=12, include_ami_geometry=False)
        payload["loaded_after_call"] = module_name in sys.modules
        print(json.dumps(payload))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    return {key: bool(value) for key, value in payload.items()}


@pytest.mark.parametrize(
    "series",
    [
        _seasonal_signal(),
        _seasonal_signal().tolist(),
        pd.Series(_seasonal_signal()),
    ],
)
def test_run_extended_forecastability_analysis_accepts_supported_arraylikes(
    series: np.ndarray | list[float] | pd.Series,
) -> None:
    """The public use case should accept ndarray, list-like, and pandas Series inputs."""
    result = run_extended_forecastability_analysis(series, max_lag=24, period=12)

    assert isinstance(result, ExtendedForecastabilityAnalysisResult)
    assert result.n_observations == 256
    assert result.profile.predictability_sources[0] in {
        "lag_dependence",
        "spectral_concentration",
    }
    payload = json.loads(result.model_dump_json())
    assert payload["profile"]["recommended_model_families"]


def test_run_extended_forecastability_analysis_does_not_mutate_input() -> None:
    """The public use case should leave caller-owned arrays unchanged."""
    series = _seasonal_signal()
    original = series.copy()

    run_extended_forecastability_analysis(series, max_lag=24, period=12)

    np.testing.assert_allclose(series, original)


def test_run_extended_forecastability_analysis_is_descriptive_only_when_ami_is_disabled() -> None:
    """Disabling AMI geometry should preserve diagnostics but suppress routing recommendations."""
    result = run_extended_forecastability_analysis(
        _seasonal_signal(),
        max_lag=24,
        period=12,
        include_ami_geometry=False,
    )

    assert result.fingerprint.information_geometry is None
    assert result.routing_metadata["include_ami_geometry"] is False
    assert result.routing_metadata["ami_geometry_requested"] is False
    assert result.routing_metadata["descriptive_only"] is True
    assert result.profile.recommended_model_families == []
    assert result.profile.avoid_model_families == []
    assert result.profile.model_now.startswith("DIAGNOSTIC ONLY")
    assert "intentionally disabled" in result.profile.summary
    assert "intentionally disabled" in result.profile.explanation[0]
    assert "unavailable" not in result.profile.summary


def test_run_extended_analysis_is_descriptive_only_when_ami_is_unavailable() -> None:
    """Unavailable AMI geometry should suppress routing recommendations just like disabled AMI."""
    time_index = np.arange(18, dtype=float)
    result = run_extended_forecastability_analysis(
        np.sin((2.0 * np.pi * time_index) / 4.0),
        max_lag=20,
        period=4,
    )

    assert result.fingerprint.information_geometry is None
    assert result.routing_metadata["ami_geometry_requested"] is True
    assert result.routing_metadata["ami_geometry_available"] is False
    assert result.routing_metadata["descriptive_only"] is True
    assert result.profile.recommended_model_families == []
    assert result.profile.avoid_model_families == []
    assert result.profile.model_now.startswith("DIAGNOSTIC ONLY")
    assert "unavailable" in result.profile.summary
    assert "unavailable" in result.profile.explanation[0]
    assert "intentionally disabled" not in result.profile.summary


@pytest.mark.parametrize(
    ("invoke", "message"),
    [
        (
            lambda: run_extended_forecastability_analysis(_seasonal_signal(), max_lag=0),
            "max_lag must be positive",
        ),
        (
            lambda: run_extended_forecastability_analysis(_seasonal_signal(), period=1),
            "period must be greater than 1 when provided",
        ),
        (
            lambda: run_extended_forecastability_analysis(
                _seasonal_signal(),
                ordinal_embedding_dimension=1,
            ),
            "embedding_dimension must be at least 2",
        ),
        (
            lambda: run_extended_forecastability_analysis(_seasonal_signal(), ordinal_delay=0),
            "ordinal_delay must be positive",
        ),
        (
            lambda: run_extended_forecastability_analysis(_seasonal_signal(), memory_min_scale=3),
            "memory_min_scale must be at least 4",
        ),
        (
            lambda: run_extended_forecastability_analysis(
                _seasonal_signal(),
                memory_min_scale=8,
                memory_max_scale=8,
            ),
            "memory_max_scale must be greater than memory_min_scale",
        ),
    ],
)
def test_run_extended_forecastability_analysis_validates_public_parameters(
    invoke: Callable[[], ExtendedForecastabilityAnalysisResult],
    message: str,
) -> None:
    """The public use case should validate its explicit Phase 2 controls."""
    with pytest.raises(ValueError, match=message):
        invoke()


def test_extended_use_case_is_reexported_from_stable_import_roots() -> None:
    """The Phase 2 public entry point should resolve from both stable namespaces."""
    assert (
        forecastability.run_extended_forecastability_analysis
        is run_extended_forecastability_analysis
    )
    assert triage.run_extended_forecastability_analysis is run_extended_forecastability_analysis


def test_public_root_imports_do_not_eagerly_load_extended_use_case_module() -> None:
    """Stable-root imports should keep the extended use-case submodule cold in a fresh process."""
    payload = _run_lazy_import_probe()

    assert payload == {
        "loaded_after_roots": False,
        "loaded_after_attr": False,
        "loaded_after_call": True,
    }


def test_public_export_preserves_runtime_resolvable_type_hints() -> None:
    """The stable public export should keep runtime-resolvable annotations."""
    hints = typing.get_type_hints(forecastability.run_extended_forecastability_analysis)

    assert hints["series"] == ArrayLike
    assert hints["return"] is ExtendedForecastabilityAnalysisResult
