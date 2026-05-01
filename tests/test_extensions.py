"""Tests for extension helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import forecastability.extensions as extensions
from forecastability import TargetBaselineCurves, compute_target_baseline_by_horizon
from forecastability.adapters.causal_rivers import (
    evaluate_causal_rivers_pair,
    extract_aligned_station_pair,
    load_causal_rivers_config,
)
from forecastability.extensions import (
    bootstrap_descriptor_uncertainty,
    compute_k_sensitivity,
)
from forecastability.pipeline import run_canonical_example
from forecastability.pipeline.rolling_origin import build_expanding_window_splits
from forecastability.utils.datasets import generate_sine_wave


def test_target_baseline_symbols_are_reexported_from_package_root() -> None:
    assert TargetBaselineCurves.__name__ == "TargetBaselineCurves"
    assert compute_target_baseline_by_horizon is extensions.compute_target_baseline_by_horizon


def test_compute_target_baseline_by_horizon_aggregates_train_windows_only() -> None:
    """Diagnostics must use train windows only.

    Uses n_origins=1 and a single horizon per check so the train/holdout
    boundary is unambiguous.  Perturbing only the holdout (everything after
    origin_index) must leave AMI/pAMI diagnostics unchanged.
    """
    n = 200
    target_clean = np.sin(np.linspace(0.0, 20.0, n))
    n_origins = 1

    for h in [1, 3]:
        splits = build_expanding_window_splits(target_clean, n_origins=n_origins, horizon=h)
        holdout_start = splits[0].origin_index

        # Perturb only the holdout (deterministic: constant large value).
        target_perturbed = target_clean.copy()
        target_perturbed[holdout_start:] = 1000.0

        result_clean = compute_target_baseline_by_horizon(
            series_name="demo_target",
            target=target_clean,
            horizons=[h],
            n_origins=n_origins,
            random_state=7,
            min_pairs_raw=30,
            min_pairs_partial=50,
            n_surrogates=99,
        )
        result_perturbed = compute_target_baseline_by_horizon(
            series_name="demo_target",
            target=target_perturbed,
            horizons=[h],
            n_origins=n_origins,
            random_state=7,
            min_pairs_raw=30,
            min_pairs_partial=50,
            n_surrogates=99,
        )

        assert isinstance(result_clean, TargetBaselineCurves)
        assert result_clean.series_name == "demo_target"
        assert h in result_clean.ami_by_horizon
        assert h in result_clean.pami_by_horizon
        assert result_clean.ami_by_horizon[h] == result_perturbed.ami_by_horizon[h], (
            f"horizon={h}: AMI changed after holdout perturbation"
        )
        assert result_clean.pami_by_horizon[h] == result_perturbed.pami_by_horizon[h], (
            f"horizon={h}: pAMI changed after holdout perturbation"
        )


def test_extract_aligned_station_pair_uses_shared_timestamps_after_fill() -> None:
    frame = pd.DataFrame(
        {
            978: [1.0, 2.0, np.nan, np.nan, np.nan, np.nan, np.nan],
            67: [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0],
        },
        index=pd.date_range("2024-01-01", periods=7, freq="6h"),
    )

    target, driver = extract_aligned_station_pair(frame, 978, 67)

    np.testing.assert_array_equal(target, np.array([1.0, 2.0, 2.0, 2.0, 2.0, 2.0]))
    np.testing.assert_array_equal(driver, np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0]))


def test_evaluate_causal_rivers_pair_rejects_misaligned_arrays() -> None:
    config = load_causal_rivers_config(
        Path(__file__).resolve().parents[1] / "configs/causal_rivers_analysis.yaml"
    )

    with pytest.raises(ValueError, match="aligned to shared timestamps"):
        evaluate_causal_rivers_pair(
            config=config,
            target=np.arange(6, dtype=float),
            driver=np.arange(7, dtype=float),
            station_id=67,
            role="negative",
        )


def test_compute_k_sensitivity_returns_all_k_values() -> None:
    ts = generate_sine_wave(n_samples=220, random_state=5)
    table = compute_k_sensitivity(
        series_name="sine_wave",
        ts=ts,
        k_values=[4, 8, 12],
        max_lag_ami=20,
        max_lag_pami=14,
        n_surrogates=99,
        alpha=0.05,
        random_state=42,
    )
    assert sorted(table["k"].tolist()) == [4, 8, 12]
    assert set(table.columns) >= {"directness_ratio", "auc_ami", "auc_pami"}


def test_bootstrap_uncertainty_contains_expected_metrics() -> None:
    ts = generate_sine_wave(n_samples=220, random_state=5)
    result = run_canonical_example(
        "sine_wave",
        ts,
        max_lag_ami=20,
        max_lag_pami=14,
        n_neighbors=8,
        n_surrogates=99,
        alpha=0.05,
        random_state=42,
    )
    uncertainty = bootstrap_descriptor_uncertainty(
        result,
        n_bootstrap=80,
        ci_level=0.95,
        random_state=11,
    )
    assert set(uncertainty["metric"].tolist()) == {"auc_ami", "auc_pami", "directness_ratio"}
