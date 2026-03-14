"""Tests for k-sensitivity and bootstrap uncertainty extensions."""

from __future__ import annotations

from forecastability.datasets import generate_sine_wave
from forecastability.extensions import (
    bootstrap_descriptor_uncertainty,
    compute_k_sensitivity,
)
from forecastability.pipeline import run_canonical_example


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
