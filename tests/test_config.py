"""Tests for structured config invariants."""

from __future__ import annotations

import pytest

from forecastability.utils.config import ExogenousBenchmarkConfig, PaperBaselineConfig


def test_paper_baseline_config_matches_goal_1_frequency_caps() -> None:
    baseline = PaperBaselineConfig()

    assert baseline.frequencies == [
        "Yearly",
        "Quarterly",
        "Monthly",
        "Weekly",
        "Daily",
        "Hourly",
    ]
    assert baseline.horizon_caps == {
        "Yearly": 6,
        "Quarterly": 8,
        "Monthly": 18,
        "Weekly": 13,
        "Daily": 14,
        "Hourly": 48,
    }


def test_paper_baseline_clamps_horizons_per_frequency() -> None:
    baseline = PaperBaselineConfig()
    requested = [1, 6, 8, 14, 18, 48]

    assert baseline.clamp_horizons("Yearly", requested) == [1, 6]
    assert baseline.clamp_horizons("monthly", requested) == [1, 6, 8, 14, 18]
    assert baseline.clamp_horizons("Hourly", requested) == requested


def test_paper_baseline_rejects_unsupported_frequency() -> None:
    baseline = PaperBaselineConfig()

    with pytest.raises(ValueError, match="Unsupported paper-baseline frequency"):
        baseline.horizon_cap_for("Minutely")


def test_exogenous_benchmark_config_defaults_cover_fixed_slice() -> None:
    cfg = ExogenousBenchmarkConfig()

    assert cfg.analysis_scope == "both"
    assert cfg.project_extension is True
    assert cfg.metric.n_surrogates == 99
    assert cfg.slice_case_ids == [
        "bike_cnt_temp",
        "bike_cnt_hum",
        "bike_cnt_noise",
        "aapl_spy",
        "aapl_noise",
        "btc_eth",
        "btc_noise",
    ]


def test_exogenous_benchmark_config_rejects_non_fixed_slice() -> None:
    with pytest.raises(ValueError, match="fixed benchmark exogenous slice"):
        ExogenousBenchmarkConfig(slice_case_ids=["bike_cnt_temp"])
