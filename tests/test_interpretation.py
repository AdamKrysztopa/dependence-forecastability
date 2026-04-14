"""Interpretation algorithm tests."""

from __future__ import annotations

import numpy as np

from forecastability.reporting.interpretation import interpret_canonical_result
from forecastability.utils.types import CanonicalExampleResult, MetricCurve


def _fake_result(*, ami_vals: np.ndarray, pami_vals: np.ndarray) -> CanonicalExampleResult:
    return CanonicalExampleResult(
        series_name="demo",
        series=np.sin(np.linspace(0.0, 4.0, 200)),
        ami=MetricCurve(
            values=ami_vals,
            lower_band=np.zeros_like(ami_vals),
            upper_band=np.full_like(ami_vals, 0.1),
            significant_lags=np.array([1, 2, 3]),
        ),
        pami=MetricCurve(
            values=pami_vals,
            lower_band=np.zeros_like(pami_vals),
            upper_band=np.full_like(pami_vals, 0.1),
            significant_lags=np.array([1, 2]),
        ),
        metadata={},
    )


def test_interpretation_class_values_are_valid() -> None:
    result = _fake_result(ami_vals=np.full(20, 0.9), pami_vals=np.full(20, 0.8))
    interpreted = interpret_canonical_result(result)
    assert interpreted.forecastability_class in {"high", "medium", "low"}
    assert interpreted.directness_class in {"high", "medium", "low", "arch_suspected"}


def test_directness_ratio_used_consistently() -> None:
    high_direct = _fake_result(ami_vals=np.full(20, 0.8), pami_vals=np.full(20, 0.75))
    low_direct = _fake_result(ami_vals=np.full(20, 0.8), pami_vals=np.full(20, 0.1))
    high_out = interpret_canonical_result(high_direct)
    low_out = interpret_canonical_result(low_direct)
    assert high_out.directness_class in {"high", "medium"}
    assert low_out.directness_class == "low"


def test_narrative_is_generated() -> None:
    result = _fake_result(ami_vals=np.full(20, 0.2), pami_vals=np.full(20, 0.05))
    interpreted = interpret_canonical_result(result)
    assert interpreted.narrative.strip()


def test_arch_suspected_directness_class() -> None:
    """directness_ratio > 1.5 must return 'arch_suspected' (ARCH/volatility edge case).

    Mirrors the crude_oil_returns anomaly: auc_ami=0.462, auc_pami=3.824,
    directness_ratio=8.276, n_sig_ami=11, n_sig_pami=78.
    """
    ami_vals = np.full(80, 0.022)
    pami_vals = np.full(80, 0.107)  # auc ratio ≈ 4.86, well above 1.5 threshold
    result = CanonicalExampleResult(
        series_name="crude_oil_returns",
        series=np.zeros(100),
        ami=MetricCurve(
            values=ami_vals,
            lower_band=np.zeros_like(ami_vals),
            upper_band=np.full_like(ami_vals, 0.05),
            significant_lags=np.arange(1, 12),  # n_sig_ami = 11
        ),
        pami=MetricCurve(
            values=pami_vals,
            lower_band=np.zeros_like(pami_vals),
            upper_band=np.full_like(pami_vals, 0.05),
            significant_lags=np.arange(1, 79),  # n_sig_pami = 78
        ),
        metadata={},
    )
    interpreted = interpret_canonical_result(result)
    assert interpreted.directness_class == "arch_suspected"
