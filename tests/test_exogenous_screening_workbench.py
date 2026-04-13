"""Focused tests for exogenous screening workbench (backlog item #16)."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.config import ExogenousScreeningWorkbenchConfig
from forecastability.types import ExogenousBenchmarkResult
from forecastability.use_cases.run_exogenous_screening_workbench import (
    run_exogenous_screening_workbench,
)


def _config_with(
    *,
    pruning_enabled: bool,
    pruning_min_mean: float,
    pruning_min_peak: float,
    pruning_floor: float,
    pruning_min_horizons: int,
    keep_min_mean: float,
    keep_min_peak: float,
    review_min_mean: float,
    review_min_peak: float,
) -> ExogenousScreeningWorkbenchConfig:
    """Build one deterministic screening config for tests."""
    return ExogenousScreeningWorkbenchConfig.model_validate(
        {
            "horizons": [1, 2, 3, 4],
            "n_origins": 3,
            "random_state": 42,
            "n_surrogates": 99,
            "min_pairs_raw": 5,
            "min_pairs_partial": 5,
            "lag_windows": [
                {"name": "short", "start_horizon": 1, "end_horizon": 2},
                {"name": "long", "start_horizon": 3, "end_horizon": 4},
            ],
            "pruning": {
                "enabled": pruning_enabled,
                "min_mean_usefulness": pruning_min_mean,
                "min_peak_usefulness": pruning_min_peak,
                "horizon_usefulness_floor": pruning_floor,
                "min_horizons_above_floor": pruning_min_horizons,
            },
            "recommendation": {
                "keep_min_mean_usefulness": keep_min_mean,
                "keep_min_peak_usefulness": keep_min_peak,
                "review_min_mean_usefulness": review_min_mean,
                "review_min_peak_usefulness": review_min_peak,
            },
        }
    )


def _build_pair_evaluator(
    profile: dict[str, dict[int, tuple[float, float, float]]],
):
    """Build an injectable pair evaluator from a deterministic profile map."""

    def _evaluator(
        target: np.ndarray,
        exog: np.ndarray,
        *,
        case_id: str,
        target_name: str,
        exog_name: str,
        horizons: list[int],
        n_origins: int,
        random_state: int,
        n_surrogates: int,
        min_pairs_raw: int,
        min_pairs_partial: int,
        analysis_scope: str,
        project_extension: bool,
    ) -> ExogenousBenchmarkResult:
        del target
        del exog
        del n_origins
        del random_state
        del n_surrogates
        del min_pairs_raw
        del min_pairs_partial
        del analysis_scope
        del project_extension

        spec = profile[exog_name]
        warning_horizons = [h for h in horizons if spec[h][2] > 1.0]
        return ExogenousBenchmarkResult(
            case_id=case_id,
            target_name=target_name,
            exog_name=exog_name,
            horizons=horizons,
            raw_cross_mi_by_horizon={h: spec[h][0] for h in horizons},
            conditioned_cross_mi_by_horizon={h: spec[h][1] for h in horizons},
            directness_ratio_by_horizon={h: spec[h][2] for h in horizons},
            origins_used_by_horizon={h: 3 for h in horizons},
            warning_horizons=warning_horizons,
            metadata={"stub": 1},
        )

    return _evaluator


def _dummy_panel() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Build one target-plus-many-drivers panel for deterministic tests."""
    target = np.linspace(0.0, 1.0, 120)
    drivers = {
        "alpha": np.linspace(1.0, 2.0, 120),
        "beta": np.linspace(2.0, 3.0, 120),
        "gamma": np.linspace(3.0, 4.0, 120),
    }
    return target, drivers


def test_horizon_specific_ranking_orders_candidates_per_horizon() -> None:
    """Candidate drivers must be ranked independently at each horizon."""
    config = _config_with(
        pruning_enabled=False,
        pruning_min_mean=0.0,
        pruning_min_peak=0.0,
        pruning_floor=0.0,
        pruning_min_horizons=0,
        keep_min_mean=1.0,
        keep_min_peak=1.0,
        review_min_mean=0.0,
        review_min_peak=0.0,
    )

    profile = {
        "alpha": {
            1: (0.30, 0.24, 0.80),
            2: (0.28, 0.21, 0.80),
            3: (0.24, 0.15, 0.70),
            4: (0.20, 0.10, 0.70),
        },
        "beta": {
            1: (0.22, 0.12, 0.70),
            2: (0.21, 0.11, 0.70),
            3: (0.20, 0.09, 0.70),
            4: (0.20, 0.07, 0.70),
        },
        "gamma": {
            1: (0.12, 0.05, 0.80),
            2: (0.14, 0.06, 0.80),
            3: (0.25, 0.18, 0.80),
            4: (0.26, 0.20, 0.80),
        },
    }

    target, drivers = _dummy_panel()
    result = run_exogenous_screening_workbench(
        target,
        drivers,
        target_name="demo",
        config=config,
        pair_evaluator=_build_pair_evaluator(profile),
    )

    by_horizon = {
        horizon: [
            row.driver_name
            for row in sorted(
                [r for r in result.horizon_usefulness_rows if r.horizon == horizon],
                key=lambda r: r.horizon_rank,
            )
        ]
        for horizon in config.horizons
    }

    assert by_horizon[1] == ["alpha", "beta", "gamma"]
    assert by_horizon[3] == ["gamma", "alpha", "beta"]
    assert by_horizon[4] == ["gamma", "alpha", "beta"]


def test_pruning_flags_weak_driver_when_heuristics_enabled() -> None:
    """Weak drivers should be pruned when pruning heuristics are enabled."""
    config = _config_with(
        pruning_enabled=True,
        pruning_min_mean=0.09,
        pruning_min_peak=0.12,
        pruning_floor=0.08,
        pruning_min_horizons=2,
        keep_min_mean=0.2,
        keep_min_peak=0.2,
        review_min_mean=0.05,
        review_min_peak=0.08,
    )

    profile = {
        "alpha": {
            1: (0.18, 0.14, 1.00),
            2: (0.17, 0.13, 1.00),
            3: (0.16, 0.12, 1.00),
            4: (0.15, 0.11, 1.00),
        },
        "beta": {
            1: (0.09, 0.05, 1.00),
            2: (0.08, 0.04, 1.00),
            3: (0.07, 0.03, 1.00),
            4: (0.06, 0.02, 1.00),
        },
        "gamma": {
            1: (0.18, 0.14, 1.00),
            2: (0.17, 0.13, 1.00),
            3: (0.16, 0.12, 1.00),
            4: (0.15, 0.11, 1.00),
        },
    }

    target, drivers = _dummy_panel()
    result = run_exogenous_screening_workbench(
        target,
        drivers,
        target_name="demo",
        config=config,
        pair_evaluator=_build_pair_evaluator(profile),
    )

    summary = {row.driver_name: row for row in result.driver_summaries}

    assert summary["alpha"].pruned is False
    assert summary["beta"].pruned is True
    assert summary["beta"].recommendation == "reject"
    assert summary["beta"].prune_reason is not None
    assert "mean_usefulness_below_threshold" in summary["beta"].prune_reason


def test_lag_window_summaries_capture_window_means_and_peaks() -> None:
    """Lag-window summary generation must report deterministic mean and peak scores."""
    config = _config_with(
        pruning_enabled=False,
        pruning_min_mean=0.0,
        pruning_min_peak=0.0,
        pruning_floor=0.0,
        pruning_min_horizons=0,
        keep_min_mean=1.0,
        keep_min_peak=1.0,
        review_min_mean=0.0,
        review_min_peak=0.0,
    )

    profile = {
        "alpha": {
            1: (0.30, 0.20, 1.00),
            2: (0.20, 0.10, 1.00),
            3: (0.50, 0.40, 1.00),
            4: (0.40, 0.30, 1.00),
        },
        "beta": {
            1: (0.09, 0.05, 1.00),
            2: (0.08, 0.04, 1.00),
            3: (0.07, 0.03, 1.00),
            4: (0.06, 0.02, 1.00),
        },
        "gamma": {
            1: (0.09, 0.05, 1.00),
            2: (0.08, 0.04, 1.00),
            3: (0.07, 0.03, 1.00),
            4: (0.06, 0.02, 1.00),
        },
    }

    target, drivers = _dummy_panel()
    result = run_exogenous_screening_workbench(
        target,
        drivers,
        target_name="demo",
        config=config,
        pair_evaluator=_build_pair_evaluator(profile),
    )

    alpha_short = next(
        row
        for row in result.lag_window_summaries
        if row.driver_name == "alpha" and row.window_name == "short"
    )
    alpha_long = next(
        row
        for row in result.lag_window_summaries
        if row.driver_name == "alpha" and row.window_name == "long"
    )

    assert alpha_short.n_horizons_covered == 2
    assert alpha_short.mean_usefulness_score == pytest.approx(0.15)
    assert alpha_short.peak_usefulness_score == pytest.approx(0.2)

    assert alpha_long.n_horizons_covered == 2
    assert alpha_long.mean_usefulness_score == pytest.approx(0.35)
    assert alpha_long.peak_usefulness_score == pytest.approx(0.4)


def test_recommendation_mapping_outputs_keep_review_reject() -> None:
    """Recommendation layer must map drivers to keep/review/reject."""
    config = _config_with(
        pruning_enabled=False,
        pruning_min_mean=0.0,
        pruning_min_peak=0.0,
        pruning_floor=0.0,
        pruning_min_horizons=0,
        keep_min_mean=0.07,
        keep_min_peak=0.10,
        review_min_mean=0.03,
        review_min_peak=0.05,
    )

    profile = {
        "alpha": {
            1: (0.12, 0.11, 1.00),
            2: (0.11, 0.09, 1.00),
            3: (0.10, 0.08, 1.00),
            4: (0.09, 0.07, 1.00),
        },
        "beta": {
            1: (0.08, 0.06, 1.00),
            2: (0.06, 0.03, 1.00),
            3: (0.05, 0.02, 1.00),
            4: (0.04, 0.01, 1.00),
        },
        "gamma": {
            1: (0.04, 0.02, 1.00),
            2: (0.03, 0.015, 1.00),
            3: (0.02, 0.01, 1.00),
            4: (0.02, 0.01, 1.00),
        },
    }

    target, drivers = _dummy_panel()
    result = run_exogenous_screening_workbench(
        target,
        drivers,
        target_name="demo",
        config=config,
        pair_evaluator=_build_pair_evaluator(profile),
    )

    recommendation_by_driver = {
        row.driver_name: row.recommendation for row in result.driver_summaries
    }
    assert recommendation_by_driver["alpha"] == "keep"
    assert recommendation_by_driver["beta"] == "review"
    assert recommendation_by_driver["gamma"] == "reject"


def test_redundancy_alpha_zero_gives_same_ranking_as_default() -> None:
    base_config = _config_with(
        pruning_enabled=False,
        pruning_min_mean=0.0,
        pruning_min_peak=0.0,
        pruning_floor=0.0,
        pruning_min_horizons=0,
        keep_min_mean=1.0,
        keep_min_peak=1.0,
        review_min_mean=0.0,
        review_min_peak=0.0,
    )
    config_explicit = base_config.model_copy(update={"redundancy_alpha": 0.0})

    profile = {
        "alpha": {
            1: (0.30, 0.24, 0.80),
            2: (0.28, 0.21, 0.80),
            3: (0.12, 0.08, 0.80),
            4: (0.10, 0.06, 0.80),
        },
        "beta": {
            1: (0.15, 0.10, 0.80),
            2: (0.14, 0.09, 0.80),
            3: (0.18, 0.14, 0.80),
            4: (0.17, 0.12, 0.80),
        },
        "gamma": {
            1: (0.08, 0.04, 0.80),
            2: (0.07, 0.03, 0.80),
            3: (0.06, 0.02, 0.80),
            4: (0.05, 0.01, 0.80),
        },
    }

    target, drivers = _dummy_panel()
    evaluator = _build_pair_evaluator(profile)

    result_default = run_exogenous_screening_workbench(
        target, drivers, target_name="demo", config=base_config, pair_evaluator=evaluator
    )
    result_explicit = run_exogenous_screening_workbench(
        target, drivers, target_name="demo", config=config_explicit, pair_evaluator=evaluator
    )

    default_order = [
        row.driver_name
        for row in sorted(result_default.driver_summaries, key=lambda r: r.overall_rank)
    ]
    explicit_order = [
        row.driver_name
        for row in sorted(result_explicit.driver_summaries, key=lambda r: r.overall_rank)
    ]
    assert default_order == explicit_order

    for row in result_explicit.driver_summaries:
        assert row.redundancy_score is None


def test_redundancy_penalty_reduces_score_of_profile_similar_driver() -> None:
    base_config = _config_with(
        pruning_enabled=False,
        pruning_min_mean=0.0,
        pruning_min_peak=0.0,
        pruning_floor=0.0,
        pruning_min_horizons=0,
        keep_min_mean=0.0,
        keep_min_peak=0.0,
        review_min_mean=0.0,
        review_min_peak=0.0,
    )
    config = base_config.model_copy(update={"redundancy_alpha": 0.5})

    identical_profile_values = {
        1: (0.20, 0.15, 0.80),
        2: (0.18, 0.13, 0.80),
        3: (0.16, 0.11, 0.80),
        4: (0.14, 0.09, 0.80),
    }
    profile = {
        "alpha": identical_profile_values,
        "beta": identical_profile_values,
    }

    target = np.linspace(0.0, 1.0, 120)
    drivers = {
        "alpha": np.linspace(1.0, 2.0, 120),
        "beta": np.linspace(2.0, 3.0, 120),
    }
    result = run_exogenous_screening_workbench(
        target,
        drivers,
        target_name="demo",
        config=config,
        pair_evaluator=_build_pair_evaluator(profile),
    )

    ranked = sorted(result.driver_summaries, key=lambda r: r.overall_rank)
    first_selected = ranked[0]
    second_selected = next(row for row in ranked if row.driver_name != first_selected.driver_name)

    assert first_selected.redundancy_score is None
    assert second_selected.redundancy_score is not None
    assert second_selected.redundancy_score > 0.8


def test_bh_correction_marks_informative_driver_significant() -> None:
    base_config = _config_with(
        pruning_enabled=False,
        pruning_min_mean=0.0,
        pruning_min_peak=0.0,
        pruning_floor=0.0,
        pruning_min_horizons=0,
        keep_min_mean=0.0,
        keep_min_peak=0.0,
        review_min_mean=0.0,
        review_min_peak=0.0,
    )
    config = base_config.model_copy(update={"apply_bh_correction": True, "bh_fdr_alpha": 0.10})

    profile = {
        "strong": {
            1: (0.30, 0.24, 0.80),
            2: (0.28, 0.21, 0.80),
            3: (0.25, 0.18, 0.80),
            4: (0.22, 0.15, 0.80),
        },
        "noise": {
            1: (0.05, 0.02, 2.00),
            2: (0.04, 0.01, 2.00),
            3: (0.04, 0.01, 2.00),
            4: (0.03, 0.01, 2.00),
        },
    }

    target = np.linspace(0.0, 1.0, 120)
    drivers = {
        "strong": np.linspace(1.0, 2.0, 120),
        "noise": np.linspace(2.0, 3.0, 120),
    }
    result = run_exogenous_screening_workbench(
        target,
        drivers,
        target_name="demo",
        config=config,
        pair_evaluator=_build_pair_evaluator(profile),
    )

    summary = {row.driver_name: row for row in result.driver_summaries}
    assert summary["strong"].bh_significant is True
    assert summary["noise"].bh_significant is False


def test_bh_correction_false_by_default() -> None:
    config = _config_with(
        pruning_enabled=False,
        pruning_min_mean=0.0,
        pruning_min_peak=0.0,
        pruning_floor=0.0,
        pruning_min_horizons=0,
        keep_min_mean=0.0,
        keep_min_peak=0.0,
        review_min_mean=0.0,
        review_min_peak=0.0,
    )

    profile = {
        "alpha": {
            1: (0.20, 0.15, 0.80),
            2: (0.18, 0.13, 0.80),
            3: (0.16, 0.11, 0.80),
            4: (0.14, 0.09, 0.80),
        },
        "beta": {
            1: (0.10, 0.06, 0.80),
            2: (0.09, 0.05, 0.80),
            3: (0.08, 0.04, 0.80),
            4: (0.07, 0.03, 0.80),
        },
        "gamma": {
            1: (0.04, 0.01, 0.80),
            2: (0.03, 0.01, 0.80),
            3: (0.03, 0.01, 0.80),
            4: (0.02, 0.01, 0.80),
        },
    }

    target, drivers = _dummy_panel()
    result = run_exogenous_screening_workbench(
        target,
        drivers,
        target_name="demo",
        config=config,
        pair_evaluator=_build_pair_evaluator(profile),
    )

    for row in result.driver_summaries:
        assert row.bh_significant is False


def test_new_config_fields_have_correct_defaults() -> None:
    from forecastability.config import ExogenousScreeningWorkbenchConfig

    config = ExogenousScreeningWorkbenchConfig()
    assert config.redundancy_alpha == 0.0
    assert config.apply_bh_correction is False
    assert config.bh_fdr_alpha == pytest.approx(0.10)


def test_driver_summary_has_bh_significant_field() -> None:
    from forecastability.types import ExogenousDriverSummary

    summary = ExogenousDriverSummary(
        overall_rank=1,
        driver_name="driver_a",
        recommendation="keep",
        pruned=False,
        mean_usefulness_score=0.25,
        peak_usefulness_score=0.40,
        n_horizons_above_floor=4,
        warning_horizon_count=0,
    )
    assert hasattr(summary, "bh_significant")
    assert hasattr(summary, "redundancy_score")
    assert summary.bh_significant is False
    assert summary.redundancy_score is None


def test_driver_summary_table_columns_includes_new_fields() -> None:
    from forecastability.use_cases.run_exogenous_screening_workbench import (
        DRIVER_SUMMARY_TABLE_COLUMNS,
    )

    assert "bh_significant" in DRIVER_SUMMARY_TABLE_COLUMNS
    assert "redundancy_score" in DRIVER_SUMMARY_TABLE_COLUMNS
