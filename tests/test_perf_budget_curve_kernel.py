"""PBE-F29: KSG2CurveKernel.estimate_curve wall-clock budget.

Budget stored in tests/perf_budgets.yml under key PBE-F29.
Run with:
    uv run python -m pytest tests/test_perf_budget_curve_kernel.py -m perf_budget -s
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest
import yaml

from forecastability.kernels.ksg2_curve_kernel import KSG2CurveKernel


def _load_budget(tag: str) -> float:
    """Load budget_seconds for a given PBE tag from perf_budgets.yml.

    Args:
        tag: PBE identifier string (e.g. 'PBE-F29').

    Returns:
        Budget in seconds as a float.
    """
    path = Path(__file__).parent / "perf_budgets.yml"
    with open(path, encoding="utf-8") as f:
        budgets: dict[str, dict[str, object]] = yaml.safe_load(f)
    return float(budgets[tag]["budget_seconds"])


@pytest.mark.slow
@pytest.mark.perf_budget
def test_curve_kernel_within_budget() -> None:
    """PBE-F29: estimate_curve (N=2000, lag_range=40, k_list=(3,5,8)) <= budget.

    Generates 2000 samples of white noise and calls estimate_curve with the
    canonical k_list=(3,5,8) over 40 lags.  Asserts the wall-clock time is
    within the budget registered in perf_budgets.yml under PBE-F29.
    """
    rng = np.random.default_rng(42)
    series = rng.standard_normal(2000)
    kernel = KSG2CurveKernel(k_list=(3, 5, 8))

    budget = _load_budget("PBE-F29")

    t0 = time.perf_counter()
    result = kernel.estimate_curve(series, lag_range=40)
    elapsed = time.perf_counter() - t0

    print(f"\n[PBE-F29] estimate_curve elapsed: {elapsed:.3f}s  (budget: {budget}s)")
    assert result.shape == (40, 3), f"Unexpected result shape: {result.shape}"
    assert elapsed <= budget, (
        f"estimate_curve took {elapsed:.2f}s, exceeds budget {budget}s. "
        "If hardware has changed, re-measure and update perf_budgets.yml."
    )
