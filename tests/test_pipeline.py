"""Pipeline behavioral and integration tests."""

from __future__ import annotations

import numpy as np

import forecastability.pipeline.pipeline as _pipeline_impl
from forecastability.pipeline import (
    run_canonical_example,
    run_exogenous_rolling_origin_evaluation,
    run_rolling_origin_evaluation,
)
from forecastability.pipeline.rolling_origin import build_expanding_window_splits
from forecastability.utils.datasets import generate_simulated_stock_returns, generate_sine_wave


def test_sine_wave_has_stronger_ami_than_simulated_stock_returns() -> None:
    sine = generate_sine_wave(n_samples=320, random_state=4)
    stock = generate_simulated_stock_returns(n_samples=320, random_state=4)

    sine_result = run_canonical_example(
        "sine_wave",
        sine,
        max_lag_ami=16,
        max_lag_pami=12,
        n_neighbors=8,
        n_surrogates=99,
        alpha=0.05,
        random_state=10,
    )
    stock_result = run_canonical_example(
        "simulated_stock_returns",
        stock,
        max_lag_ami=16,
        max_lag_pami=12,
        n_neighbors=8,
        n_surrogates=99,
        alpha=0.05,
        random_state=10,
    )

    assert float(np.mean(sine_result.ami.values[:10])) > float(
        np.mean(stock_result.ami.values[:10])
    )


def test_pami_significant_lag_count_not_exceed_ami_for_structured_example() -> None:
    sine = generate_sine_wave(n_samples=320, random_state=21)
    result = run_canonical_example(
        "sine_wave",
        sine,
        max_lag_ami=20,
        max_lag_pami=14,
        n_neighbors=8,
        n_surrogates=99,
        alpha=0.05,
        random_state=10,
    )
    assert result.pami.significant_lags is not None
    assert result.ami.significant_lags is not None
    assert result.pami.significant_lags.size <= result.ami.significant_lags.size


def test_run_canonical_example_dispatches_selected_backend(monkeypatch) -> None:
    sine = generate_sine_wave(n_samples=320, random_state=21)
    seen_backend: dict[str, str] = {}

    def _stub_compute_pami_with_backend(
        ts: np.ndarray,
        max_lag: int,
        *,
        backend: str = "linear_residual",
        rf_estimators: int = 200,
        rf_max_depth: int | None = 8,
        et_estimators: int = 300,
        et_max_depth: int | None = 10,
        n_neighbors: int = 8,
        min_pairs: int = 50,
        random_state: int = 42,
    ) -> np.ndarray:
        del ts
        del rf_estimators, rf_max_depth, et_estimators, et_max_depth
        del n_neighbors, min_pairs, random_state
        seen_backend["name"] = backend
        return np.full(max_lag, 0.05)

    monkeypatch.setattr(
        _pipeline_impl,
        "compute_pami_with_backend",
        _stub_compute_pami_with_backend,
    )

    result = run_canonical_example(
        "sine_wave",
        sine,
        max_lag_ami=20,
        max_lag_pami=14,
        n_neighbors=8,
        n_surrogates=99,
        alpha=0.05,
        random_state=10,
        pami_backend="extra_trees_residual",
        skip_bands=True,
    )
    assert seen_backend["name"] == "extra_trees_residual"
    assert result.metadata["pami_backend"] == "extra_trees_residual"


def test_rolling_origin_pipeline_is_train_only_for_diagnostics() -> None:
    ts = np.sin(np.linspace(0.0, 30.0, 360)) + np.linspace(0.0, 2.0, 360)
    horizons = [1, 3, 6]
    result = run_rolling_origin_evaluation(
        ts,
        series_id="demo",
        frequency="monthly",
        horizons=horizons,
        n_origins=10,
        seasonal_period=12,
        random_state=42,
    )
    assert result.metadata["train_only_diagnostics"] == 1
    assert result.metadata["holdout_only_scoring"] == 1

    splits = build_expanding_window_splits(ts, n_origins=10, horizon=6)
    for split in splits:
        assert split.origin_index == split.train.size
        assert split.test.size == 6


def test_rolling_origin_pipeline_optional_models_run() -> None:
    ts = np.sin(np.linspace(0.0, 30.0, 360)) + np.linspace(0.0, 2.0, 360)
    result = run_rolling_origin_evaluation(
        ts,
        series_id="demo_opt",
        frequency="monthly",
        horizons=[1, 3],
        n_origins=10,
        seasonal_period=12,
        random_state=42,
        include_lightgbm_autoreg=True,
        include_nbeats=True,
    )
    model_names = {item.model_name for item in result.forecast_results}
    assert "lightgbm_autoreg" in model_names
    assert "nbeats" in model_names


def test_exogenous_rolling_origin_pipeline_is_train_only_for_diagnostics() -> None:
    """Diagnostics must be computed on train windows only.

    Uses n_origins=1 so the train/holdout boundary is unambiguous: the single
    split's train window ends at origin_index, and everything after is holdout.
    Perturbing only the holdout must leave cross-MI diagnostics unchanged.
    """
    n = 200
    ts_clean = np.sin(np.linspace(0.0, 20.0, n))
    exog_clean = np.cos(np.linspace(0.0, 20.0, n))

    H = 3
    n_origins = 1
    horizons = [H]

    splits = build_expanding_window_splits(ts_clean, n_origins=n_origins, horizon=H)
    holdout_start = splits[0].origin_index

    # Perturb only the holdout portion (deterministic).
    ts_perturbed = ts_clean.copy()
    exog_perturbed = exog_clean.copy()
    ts_perturbed[holdout_start:] = 1000.0
    exog_perturbed[holdout_start:] = 1000.0

    result_clean = run_exogenous_rolling_origin_evaluation(
        ts_clean,
        exog_clean,
        case_id="demo",
        target_name="target",
        exog_name="driver",
        horizons=horizons,
        n_origins=n_origins,
        random_state=42,
    )
    result_perturbed = run_exogenous_rolling_origin_evaluation(
        ts_perturbed,
        exog_perturbed,
        case_id="demo",
        target_name="target",
        exog_name="driver",
        horizons=horizons,
        n_origins=n_origins,
        random_state=42,
    )

    # Metadata constants must be set regardless of computation path.
    assert result_clean.metadata["train_only_diagnostics"] == 1
    assert result_clean.metadata["holdout_only_scoring"] == 1

    # Train-only diagnostics must be identical: holdout perturbation must not
    # leak into the MI estimates.
    assert (
        result_clean.raw_cross_mi_by_horizon[H]
        == result_perturbed.raw_cross_mi_by_horizon[H]
    )
    assert (
        result_clean.conditioned_cross_mi_by_horizon[H]
        == result_perturbed.conditioned_cross_mi_by_horizon[H]
    )


def test_exogenous_rolling_origin_pipeline_requires_matching_shapes() -> None:
    ts = np.ones(100)
    exog = np.ones(101)

    with np.testing.assert_raises_regex(ValueError, "matching shape"):
        run_exogenous_rolling_origin_evaluation(
            ts,
            exog,
            case_id="bad",
            target_name="target",
            exog_name="driver",
            horizons=[1],
            n_origins=3,
            random_state=42,
        )


def test_rolling_origin_pipeline_skips_horizon_when_no_valid_split_survives() -> None:
    ts = np.sin(np.linspace(0.0, 20.0, 90))

    result = run_rolling_origin_evaluation(
        ts,
        series_id="short",
        frequency="monthly",
        horizons=[20],
        n_origins=3,
        seasonal_period=12,
        random_state=7,
    )

    assert result.ami_by_horizon == {}
    assert result.pami_by_horizon == {}
    assert all(not forecast.smape_by_horizon for forecast in result.forecast_results)


def test_rolling_origin_pipeline_skips_undersized_splits_and_is_deterministic() -> None:
    ts = np.sin(np.linspace(0.0, 30.0, 130))

    first = run_rolling_origin_evaluation(
        ts,
        series_id="mixed",
        frequency="monthly",
        horizons=[20],
        n_origins=4,
        seasonal_period=12,
        random_state=21,
    )
    second = run_rolling_origin_evaluation(
        ts,
        series_id="mixed",
        frequency="monthly",
        horizons=[20],
        n_origins=4,
        seasonal_period=12,
        random_state=21,
    )

    assert 20 in first.ami_by_horizon
    assert 20 in first.pami_by_horizon
    assert first.ami_by_horizon[20] == second.ami_by_horizon[20]
    assert first.pami_by_horizon[20] == second.pami_by_horizon[20]
