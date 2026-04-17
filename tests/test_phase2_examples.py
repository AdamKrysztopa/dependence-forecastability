"""Lightweight tests for Phase-2 univariate example scripts (F3, F4, F6)."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import numpy as np


def _load_module(*, relative_path: str, module_name: str) -> ModuleType:
    """Load a module from a workspace-relative file path.

    Args:
        relative_path: Path relative to repository root.
        module_name: Temporary module name for import loading.

    Returns:
        Loaded module object.

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


def test_f3_generator_is_deterministic() -> None:
    """F3 AR(1) generator should be deterministic for a fixed seed."""
    module = _load_module(
        relative_path="examples/univariate/f3_predictive_info_learning_curve.py",
        module_name="f3_example",
    )

    series_a = module._generate_ar1(n_samples=300, phi=0.8, random_state=77)
    series_b = module._generate_ar1(n_samples=300, phi=0.8, random_state=77)

    assert series_a.shape == (300,)
    assert np.allclose(series_a, series_b)


def test_f3_small_sample_case_emits_reliability_warning() -> None:
    """F3 small-sample scenario should include at least one reliability warning."""
    module = _load_module(
        relative_path="examples/univariate/f3_predictive_info_learning_curve.py",
        module_name="f3_example_results",
    )

    results = module.build_example_results()
    small_case = [curve for label, curve in results if "Small-sample" in label]

    assert len(small_case) == 1
    assert small_case[0].reliability_warnings


def test_f4_example_returns_expected_signal_labels_and_score_ordering() -> None:
    """F4 example should include the planned signals with plausible score ordering."""
    module = _load_module(
        relative_path="examples/univariate/f4_spectral_predictability.py",
        module_name="f4_example",
    )

    results = module.build_example_results()
    labels = [label for label, _, _ in results]
    scores = {label: result.score for label, _, result in results}

    assert labels == [
        "White-noise-like signal",
        "Periodic sine signal",
        "Structured irregular signal",
    ]
    assert all(0.0 <= score <= 1.0 for score in scores.values())
    assert scores["Periodic sine signal"] > scores["White-noise-like signal"]


def test_f6_example_returns_entropy_metrics_in_unit_interval() -> None:
    """F6 example should provide bounded entropy metrics and valid band labels."""
    module = _load_module(
        relative_path="examples/univariate/f6_entropy_complexity.py",
        module_name="f6_example",
    )

    results = module.build_example_results()
    assert len(results) == 3

    for _label, _series, result in results:
        assert 0.0 <= result.permutation_entropy <= 1.0
        assert 0.0 <= result.spectral_entropy <= 1.0
        assert result.complexity_band in {"low", "medium", "high"}


def test_f6_periodic_and_noisy_cases_show_different_complexity_levels() -> None:
    """F6 periodic and noisy examples should not collapse to the same band."""
    module = _load_module(
        relative_path="examples/univariate/f6_entropy_complexity.py",
        module_name="f6_example_bands",
    )

    results = module.build_example_results()
    bands = {label: result.complexity_band for label, _, result in results}

    assert bands["Periodic signal"] != bands["Noisy signal"]
