"""PBE-F28: KSG2CurveKernel.estimate_surrogate_band wall-clock budget.

Budget stored in tests/perf_budgets.yml under key PBE-F28.
Run with:
    uv run python -m pytest tests/test_perf_budget_surrogate_band.py -m perf_budget -s
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
        tag: PBE identifier string (e.g. 'PBE-F28').

    Returns:
        Budget in seconds as a float.
    """
    path = Path(__file__).parent / "perf_budgets.yml"
    with open(path, encoding="utf-8") as f:
        budgets: dict[str, dict[str, object]] = yaml.safe_load(f)
    return float(budgets[tag]["budget_seconds"])


@pytest.mark.slow
@pytest.mark.perf_budget
def test_surrogate_band_within_budget() -> None:
    """PBE-F28: estimate_surrogate_band (N=2000, lag_range=40, n_surrogates=99) <= budget.

    Generates 2000 samples of white noise and calls estimate_surrogate_band with
    n_surrogates=99 (the minimum enforced by the kernel) over 40 lags.
    Asserts the wall-clock time is within the budget registered in
    perf_budgets.yml under PBE-F28.
    """
    rng = np.random.default_rng(42)
    series = rng.standard_normal(2000)
    kernel = KSG2CurveKernel(k_list=(3, 5, 8))

    budget = _load_budget("PBE-F28")

    t0 = time.perf_counter()
    result = kernel.estimate_surrogate_band(series, lag_range=40, n_surrogates=99)
    elapsed = time.perf_counter() - t0

    print(f"\n[PBE-F28] estimate_surrogate_band elapsed: {elapsed:.3f}s  (budget: {budget}s)")
    assert result.shape == (99, 40, 3), f"Unexpected result shape: {result.shape}"
    assert elapsed <= budget, (
        f"estimate_surrogate_band took {elapsed:.2f}s, exceeds budget {budget}s. "
        "If hardware has changed, re-measure and update perf_budgets.yml."
    )
