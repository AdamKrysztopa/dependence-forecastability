"""Unit tests for the optional live fingerprint agent (V3_1-F05.2)."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import numpy as np
import pytest

from forecastability.adapters.llm.fingerprint_agent import (
    FingerprintDeps,
    FingerprintExplanation,
    _strict_explanation,
    create_fingerprint_agent,
    run_fingerprint_agent,
)
from forecastability.adapters.settings import InfraSettings
from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.utils.synthetic import (
    generate_ar1_monotonic,
    generate_white_noise,
)


@pytest.fixture()
def ar1_series() -> np.ndarray:
    """Return a deterministic AR(1) series for fingerprint tests."""
    return generate_ar1_monotonic(n=300, phi=0.85, seed=42)


@pytest.fixture()
def white_noise_series() -> np.ndarray:
    """Return a deterministic white-noise series for fingerprint tests."""
    return generate_white_noise(n=300, seed=42)


class TestCreateFingerprintAgent:
    """Test the agent factory raises ImportError when pydantic-ai is absent."""

    def test_raises_import_error_when_pydantic_ai_unavailable(self) -> None:
        with patch(
            "forecastability.adapters.llm.fingerprint_agent._PYDANTIC_AI_AVAILABLE",
            False,
        ):
            with pytest.raises(ImportError, match="pydantic-ai"):
                create_fingerprint_agent()


class TestStrictExplanation:
    """Test the deterministic fallback path (_strict_explanation)."""

    def test_strict_explanation_returns_correct_type(self, ar1_series: np.ndarray) -> None:
        bundle = run_forecastability_fingerprint(
            ar1_series, max_lag=12, n_surrogates=99, random_state=42
        )
        explanation = _strict_explanation(bundle)

        assert isinstance(explanation, FingerprintExplanation)

    def test_strict_explanation_target_name_propagated(self, ar1_series: np.ndarray) -> None:
        bundle = run_forecastability_fingerprint(
            ar1_series, target_name="ar1_test", max_lag=12, n_surrogates=99, random_state=42
        )
        explanation = _strict_explanation(bundle)

        assert explanation.target_name == "ar1_test"

    def test_strict_explanation_four_catt_metrics(self, ar1_series: np.ndarray) -> None:
        bundle = run_forecastability_fingerprint(
            ar1_series, max_lag=12, n_surrogates=99, random_state=42
        )
        explanation = _strict_explanation(bundle)

        assert isinstance(explanation.geometry_method, str)
        assert isinstance(explanation.signal_to_noise, float)
        assert isinstance(explanation.geometry_information_horizon, int)
        assert isinstance(explanation.geometry_information_structure, str)
        assert isinstance(explanation.information_mass, float)
        assert isinstance(explanation.information_horizon, int)
        assert isinstance(explanation.information_structure, str)
        assert isinstance(explanation.nonlinear_share, float)

    def test_strict_explanation_narrative_is_nonempty(self, ar1_series: np.ndarray) -> None:
        bundle = run_forecastability_fingerprint(
            ar1_series, max_lag=12, n_surrogates=99, random_state=42
        )
        explanation = _strict_explanation(bundle)

        assert isinstance(explanation.narrative, str)
        assert len(explanation.narrative) > 0

    def test_strict_explanation_primary_families_nonempty(self, ar1_series: np.ndarray) -> None:
        bundle = run_forecastability_fingerprint(
            ar1_series, max_lag=12, n_surrogates=99, random_state=42
        )
        explanation = _strict_explanation(bundle)

        assert len(explanation.primary_families) > 0

    def test_strict_explanation_white_noise_none_structure(
        self, white_noise_series: np.ndarray
    ) -> None:
        bundle = run_forecastability_fingerprint(
            white_noise_series, max_lag=12, n_surrogates=99, random_state=42
        )
        explanation = _strict_explanation(bundle)

        # White noise may produce none or low-mass; narrative must still be present.
        assert isinstance(explanation.narrative, str)
        assert len(explanation.narrative) > 0


class TestRunFingerprintAgentStrictMode:
    """Test that strict=True always returns a deterministic explanation."""

    def test_strict_mode_skips_live_agent(self, ar1_series: np.ndarray) -> None:
        explanation = asyncio.run(
            run_fingerprint_agent(
                ar1_series,
                target_name="strict_test",
                max_lag=12,
                n_surrogates=99,
                random_state=42,
                strict=True,
            )
        )

        assert isinstance(explanation, FingerprintExplanation)
        assert explanation.target_name == "strict_test"

    def test_strict_mode_when_pydantic_ai_unavailable(
        self, ar1_series: np.ndarray
    ) -> None:
        with patch(
            "forecastability.adapters.llm.fingerprint_agent._PYDANTIC_AI_AVAILABLE",
            False,
        ):
            explanation = asyncio.run(
                run_fingerprint_agent(
                    ar1_series,
                    max_lag=12,
                    n_surrogates=99,
                    random_state=42,
                )
            )

        assert isinstance(explanation, FingerprintExplanation)

    def test_strict_mode_fields_are_deterministic(self, ar1_series: np.ndarray) -> None:
        """Running strict mode twice with the same seed must produce identical outputs."""
        e1 = asyncio.run(
            run_fingerprint_agent(ar1_series, max_lag=12, n_surrogates=99,
                                   random_state=42, strict=True)
        )
        e2 = asyncio.run(
            run_fingerprint_agent(ar1_series, max_lag=12, n_surrogates=99,
                                   random_state=42, strict=True)
        )

        assert e1.information_mass == e2.information_mass
        assert e1.information_horizon == e2.information_horizon
        assert e1.information_structure == e2.information_structure
        assert e1.nonlinear_share == e2.nonlinear_share
        assert e1.signal_to_noise == e2.signal_to_noise
        assert e1.primary_families == e2.primary_families


class TestFingerprintDepsDataclass:
    """Test the FingerprintDeps dependency container."""

    def test_fingerprint_deps_defaults(self) -> None:
        settings = InfraSettings(_env_file=None)  # type: ignore[call-arg]
        series = np.zeros(100)
        deps = FingerprintDeps(settings=settings, series=series)

        assert deps.target_name == "series"
        assert deps.max_lag == 24
        assert deps.n_surrogates == 99
        assert deps.random_state == 42
        assert deps.ami_floor == 0.01
        assert deps._bundle is None

    def test_fingerprint_deps_custom_values(self) -> None:
        settings = InfraSettings(_env_file=None)  # type: ignore[call-arg]
        series = np.ones(200)
        deps = FingerprintDeps(
            settings=settings,
            series=series,
            target_name="custom",
            max_lag=18,
            n_surrogates=199,
            random_state=7,
            ami_floor=0.02,
        )

        assert deps.target_name == "custom"
        assert deps.max_lag == 18
        assert deps.n_surrogates == 199
        assert deps.random_state == 7
        assert deps.ami_floor == 0.02
