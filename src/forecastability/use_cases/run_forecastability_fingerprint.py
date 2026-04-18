"""Forecastability fingerprint orchestration use case (V3_1-F04).

Composes domain services to produce a :class:`FingerprintBundle` from a raw
time series.  Contains no LLM adapters, rendering adapters, or provider SDKs.
"""

from __future__ import annotations

import numpy as np

from forecastability.pipeline.analyzer import AnalyzeResult, ForecastabilityAnalyzer
from forecastability.services.fingerprint_service import build_fingerprint
from forecastability.services.routing_policy_service import (
    RoutingPolicyConfig,
    route_fingerprint,
)
from forecastability.utils.types import FingerprintBundle
from forecastability.utils.validation import validate_time_series


def run_forecastability_fingerprint(
    series: np.ndarray,
    *,
    target_name: str = "series",
    max_lag: int = 24,
    n_surrogates: int = 99,
    random_state: int = 42,
    ami_floor: float = 0.01,
    routing_config: RoutingPolicyConfig | None = None,
) -> FingerprintBundle:
    """Compute forecastability fingerprint and routing recommendation for a series.

    Validates the series, runs AMI analysis, builds a structural fingerprint,
    and maps it to model-family routing guidance.

    Args:
        series: Univariate time series as a 1-D numpy array.
        target_name: Human-readable label stored in the bundle.
        max_lag: Maximum horizon H to analyse (horizons 1 … max_lag).
        n_surrogates: Number of phase-randomised surrogates for significance.
        random_state: Seed for reproducible surrogate generation.
        ami_floor: Minimum AMI value to count a horizon as informative.
        routing_config: Optional custom :class:`RoutingPolicyConfig`; uses
            defaults when ``None``.

    Returns:
        :class:`FingerprintBundle` containing the fingerprint, recommendation,
        and a lightweight profile summary.

    Raises:
        ValueError: If ``series`` is too short, non-finite, or constant.
    """
    validated = validate_time_series(series, min_length=max_lag + 10)
    result = _run_analyzer(
        validated, max_lag=max_lag, n_surrogates=n_surrogates, random_state=random_state
    )
    sig_horizons = _to_one_based(result.sig_raw_lags)
    fingerprint = build_fingerprint(
        result.raw.tolist(),
        horizons=list(range(1, max_lag + 1)),
        significant_horizons=sig_horizons,
        series=validated,
        ami_floor=ami_floor,
    )
    recommendation = route_fingerprint(fingerprint, config=routing_config)
    profile_summary = _build_profile_summary(
        result, max_lag=max_lag, n_surrogates=n_surrogates, sig_horizons=sig_horizons
    )
    return FingerprintBundle(
        target_name=target_name,
        fingerprint=fingerprint,
        recommendation=recommendation,
        profile_summary=profile_summary,
    )


def _run_analyzer(
    series: np.ndarray,
    *,
    max_lag: int,
    n_surrogates: int,
    random_state: int,
) -> AnalyzeResult:
    """Instantiate analyzer and return the AMI result.

    Args:
        series: Validated series array.
        max_lag: Maximum lag / horizon.
        n_surrogates: Surrogate count.
        random_state: RNG seed.

    Returns:
        :class:`AnalyzeResult` from :class:`ForecastabilityAnalyzer`.
    """
    analyzer = ForecastabilityAnalyzer(
        n_surrogates=n_surrogates,
        random_state=random_state,
        method="mi",
    )
    return analyzer.analyze(series, max_lag, compute_surrogates=True)


def _to_one_based(zero_based_lags: np.ndarray) -> list[int]:
    """Convert 0-based lag indices to 1-based horizon list.

    Args:
        zero_based_lags: Array of 0-based significant lag indices.

    Returns:
        Sorted list of 1-based horizon integers.
    """
    return (zero_based_lags + 1).tolist()


def _build_profile_summary(
    result: AnalyzeResult,
    *,
    max_lag: int,
    n_surrogates: int,
    sig_horizons: list[int],
) -> dict[str, str | int | float]:
    """Assemble a lightweight profile summary from analysis results.

    Args:
        result: :class:`AnalyzeResult` from the analyzer.
        max_lag: Maximum lag used in the analysis.
        n_surrogates: Surrogate count used.
        sig_horizons: 1-based list of significant horizons.

    Returns:
        Dict of scalar summary statistics.
    """
    peak_ami = float(np.max(result.raw)) if result.raw.size > 0 else 0.0
    return {
        "max_lag": max_lag,
        "n_surrogates": n_surrogates,
        "sig_horizons_count": len(sig_horizons),
        "peak_ami": peak_ami,
        "analyzer_recommendation": result.recommendation,
    }
