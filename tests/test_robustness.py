"""Tests for the pAMI robustness study module."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.config import RobustnessStudyConfig
from forecastability.robustness import (
    run_backend_comparison,
    run_robustness_study,
    run_sample_size_stress,
)
from forecastability.types import (
    BackendComparisonResult,
    RobustnessStudyResult,
    SampleSizeStressResult,
)


def _sine_series(*, n: int = 200, random_state: int = 42) -> np.ndarray:
    """Generate a simple sine wave for tests."""
    rng = np.random.default_rng(random_state)
    t = np.linspace(0, 4 * np.pi, n)
    return np.sin(t) + 0.1 * rng.standard_normal(n)


class TestBackendComparison:
    """Tests for run_backend_comparison."""

    def test_returns_correct_structure(self) -> None:
        ts = _sine_series(n=200)
        result = run_backend_comparison(
            series_name="test_sine",
            ts=ts,
            max_lag_ami=10,
            max_lag_pami=8,
            backends=["linear_residual", "rf_residual"],
            n_neighbors=8,
            n_surrogates=99,
            alpha=0.05,
            random_state=42,
        )
        assert isinstance(result, BackendComparisonResult)
        assert len(result.entries) >= 2
        assert result.series_name == "test_sine"
        for entry in result.entries:
            assert entry.backend in ("linear_residual", "rf_residual")
            assert len(entry.pami_values) > 0

    def test_directness_ratio_warning_flagged(self) -> None:
        ts = _sine_series(n=200)
        result = run_backend_comparison(
            series_name="test_sine",
            ts=ts,
            max_lag_ami=10,
            max_lag_pami=8,
            backends=["linear_residual", "rf_residual"],
            n_neighbors=8,
            n_surrogates=99,
            alpha=0.05,
            random_state=42,
        )
        for entry in result.entries:
            if entry.directness_ratio > 1.0:
                assert entry.directness_ratio_warning is True
            else:
                assert entry.directness_ratio_warning is False

    def test_stability_flags_computed(self) -> None:
        ts = _sine_series(n=200)
        result = run_backend_comparison(
            series_name="test_sine",
            ts=ts,
            max_lag_ami=10,
            max_lag_pami=8,
            backends=["linear_residual", "rf_residual"],
            n_neighbors=8,
            n_surrogates=99,
            alpha=0.05,
            random_state=42,
        )
        assert isinstance(result.lag_ranking_stable, bool)
        assert isinstance(result.directness_ratio_stable, bool)
        assert isinstance(result.rank_correlation, float)
        assert isinstance(result.directness_ratio_range, float)


class TestSampleSizeStress:
    """Tests for run_sample_size_stress."""

    def test_returns_entries_per_fraction(self) -> None:
        ts = _sine_series(n=300)
        fractions = [0.5, 0.75, 1.0]
        result = run_sample_size_stress(
            series_name="test_sine",
            ts=ts,
            fractions=fractions,
            max_lag_ami=10,
            max_lag_pami=8,
            n_neighbors=8,
            n_surrogates=99,
            alpha=0.05,
            random_state=42,
            min_series_length=100,
        )
        assert isinstance(result, SampleSizeStressResult)
        assert len(result.entries) == len(fractions)
        for entry, frac in zip(result.entries, sorted(fractions), strict=True):
            assert entry.fraction == frac
            assert entry.n_observations == int(len(ts) * frac)

    def test_short_fractions_skipped(self) -> None:
        ts = _sine_series(n=150)
        result = run_sample_size_stress(
            series_name="test_short",
            ts=ts,
            fractions=[0.5, 1.0],
            max_lag_ami=10,
            max_lag_pami=8,
            n_neighbors=8,
            n_surrogates=99,
            alpha=0.05,
            random_state=42,
            min_series_length=100,
        )
        # fraction=0.5 → 75 obs < 100 → skipped
        assert len(result.entries) == 1
        assert result.entries[0].fraction == 1.0
        assert len(result.warnings) == 1

    def test_directness_ratio_stable_flag(self) -> None:
        ts = _sine_series(n=300)
        result = run_sample_size_stress(
            series_name="test_sine",
            ts=ts,
            fractions=[0.75, 1.0],
            max_lag_ami=10,
            max_lag_pami=8,
            n_neighbors=8,
            n_surrogates=99,
            alpha=0.05,
            random_state=42,
            min_series_length=100,
        )
        assert isinstance(result.directness_ratio_stable, bool)


class TestRobustnessStudy:
    """Tests for run_robustness_study."""

    def test_produces_non_empty_result(self) -> None:
        ts = _sine_series(n=200)
        config = RobustnessStudyConfig(
            backends=["linear_residual", "rf_residual"],
            sample_fractions=[0.75, 1.0],
            max_lag_ami=10,
            max_lag_pami=8,
            n_surrogates=99,
            min_series_length=100,
        )
        result = run_robustness_study(
            [("test_sine", ts)],
            config=config,
        )
        assert isinstance(result, RobustnessStudyResult)
        assert len(result.backend_comparisons) == 1
        assert len(result.sample_size_tests) == 1
        assert isinstance(result.overall_stable, bool)
        assert len(result.summary_narrative) > 0

    def test_excluded_series_populated(self) -> None:
        short_ts = np.sin(np.linspace(0, 2, 30))
        config = RobustnessStudyConfig(
            backends=["linear_residual", "rf_residual"],
            sample_fractions=[1.0],
            max_lag_ami=10,
            max_lag_pami=8,
            n_surrogates=99,
            min_series_length=100,
        )
        result = run_robustness_study(
            [("too_short", short_ts)],
            config=config,
        )
        assert "too_short" in result.excluded_series
        assert len(result.backend_comparisons) == 0

    def test_multiple_datasets(self) -> None:
        ts1 = _sine_series(n=200, random_state=1)
        ts2 = _sine_series(n=200, random_state=2)
        config = RobustnessStudyConfig(
            backends=["linear_residual", "rf_residual"],
            sample_fractions=[1.0],
            max_lag_ami=10,
            max_lag_pami=8,
            n_surrogates=99,
            min_series_length=100,
        )
        result = run_robustness_study(
            [("series_a", ts1), ("series_b", ts2)],
            config=config,
        )
        assert len(result.backend_comparisons) == 2
        assert len(result.sample_size_tests) == 2


class TestConfigValidation:
    """Tests for RobustnessStudyConfig validation."""

    def test_requires_at_least_two_backends(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            RobustnessStudyConfig(backends=["linear_residual"])

    def test_rejects_empty_fractions(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            RobustnessStudyConfig(sample_fractions=[])

    def test_rejects_invalid_fractions(self) -> None:
        with pytest.raises(ValueError, match="in \\(0, 1\\]"):
            RobustnessStudyConfig(sample_fractions=[0.0, 0.5])

    def test_valid_config(self) -> None:
        config = RobustnessStudyConfig()
        assert len(config.backends) == 2
        assert config.n_surrogates >= 99
