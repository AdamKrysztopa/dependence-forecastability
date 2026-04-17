"""Lightweight tests for Phase-1 univariate example scripts."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import numpy as np


def _load_module(*, relative_path: str, module_name: str) -> ModuleType:
    """Load a module from a workspace-relative file path.

    Args:
        relative_path: Path relative to repository root.
        module_name: Temporary module name for loading.

    Returns:
        Loaded Python module.

    Raises:
        RuntimeError: If module spec cannot be created.
    """
    repo_root = Path(__file__).resolve().parents[1]
    file_path = repo_root / relative_path
    spec = spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec for {file_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_f1_synthetic_generator_is_deterministic() -> None:
    """Seasonal synthetic generator should be deterministic for a fixed seed."""
    module = _load_module(
        relative_path="examples/univariate/f1_forecastability_profile_synthetic.py",
        module_name="f1_synth_example",
    )

    series_a = module._generate_non_monotone_seasonal(random_state=42, n_samples=256)
    series_b = module._generate_non_monotone_seasonal(random_state=42, n_samples=256)

    assert series_a.shape == (256,)
    assert np.allclose(series_a, series_b)


def test_f2_block_aggregation_matches_expected_means() -> None:
    """Block aggregation should reduce length and return block means."""
    module = _load_module(
        relative_path="examples/univariate/f2_information_limits_synthetic.py",
        module_name="f2_example",
    )

    source = np.arange(12, dtype=float)
    aggregated = module._aggregate_blocks(source, block_size=4)

    assert aggregated.shape == (3,)
    assert np.allclose(aggregated, np.array([1.5, 5.5, 9.5]))


def test_f2_achieved_performance_table_has_required_columns() -> None:
    """Achieved-performance helper should return finite diagnostics columns."""
    module = _load_module(
        relative_path="examples/univariate/f2_information_limits_synthetic.py",
        module_name="f2_example_for_perf",
    )

    series = module._generate_source_signal(random_state=9, n_samples=320)
    achieved = module._evaluate_achieved_performance(series=series, max_horizon=3, n_origins=4)

    assert list(achieved.columns) == [
        "horizon",
        "naive_smape",
        "linear_smape",
        "realized_gain_pct",
    ]
    assert achieved.shape[0] == 3
    assert np.isfinite(
        achieved[["naive_smape", "linear_smape", "realized_gain_pct"]].to_numpy()
    ).all()
