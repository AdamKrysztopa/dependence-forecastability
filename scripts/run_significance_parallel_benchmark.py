#!/usr/bin/env python
"""Benchmark: Serial vs parallel significance computation policies.

Measures wall-clock time for compute_significance_bands_generic with
n_jobs=1 (serial) vs n_jobs=-1 (parallel) across a range of n_surrogates
and series_length values.

Usage:
    uv run python scripts/run_significance_parallel_benchmark.py

Outputs:
    outputs/performance/significance_parallel_benchmark.json
"""

from __future__ import annotations

import importlib.metadata
import json
import time
from pathlib import Path

import numpy as np

from forecastability.metrics.scorers import ScorerInfo, default_registry
from forecastability.services.significance_service import compute_significance_bands_generic

_OUTPUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "outputs"
    / "performance"
    / "significance_parallel_benchmark.json"
)
_N_SURROGATES_GRID: list[int] = [99, 199]
_SERIES_LENGTH_GRID: list[int] = [200, 500, 1000]
_MAX_LAG: int = 10
_MIN_PAIRS: int = 30
_RANDOM_STATE: int = 42


def _time_significance_bands(
    series: np.ndarray,
    *,
    n_surrogates: int,
    n_jobs: int,
    info: ScorerInfo,
) -> float | str:
    """Time one significance-bands call and return elapsed seconds.

    Args:
        series: Input time series.
        n_surrogates: Number of phase-randomised surrogates.
        n_jobs: Worker count: 1 = serial, -1 = all CPUs.
        info: Scorer metadata from the registry.

    Returns:
        Elapsed wall-clock seconds, or ``"not_supported"`` when the function
        does not accept ``n_jobs``.
    """
    try:
        start = time.perf_counter()
        compute_significance_bands_generic(
            series,
            n_surrogates=n_surrogates,
            random_state=_RANDOM_STATE,
            max_lag=_MAX_LAG,
            info=info,
            which="raw",
            min_pairs=_MIN_PAIRS,
            n_jobs=n_jobs,
        )
        return time.perf_counter() - start
    except (ImportError, TypeError):
        return "not_supported"


def _run_benchmark() -> list[dict[str, object]]:
    """Run all n_surrogates × series_length × n_jobs combinations.

    Returns:
        List of result dicts with keys ``n_surrogates``, ``series_length``,
        ``n_jobs``, ``elapsed_s``.
    """
    mi_info = default_registry().get("mi")
    if mi_info is None:
        raise ValueError("No 'mi' scorer in default registry")
    rng = np.random.default_rng(_RANDOM_STATE)
    results: list[dict[str, object]] = []

    for series_length in _SERIES_LENGTH_GRID:
        series = rng.normal(size=series_length)
        for n_surrogates in _N_SURROGATES_GRID:
            for n_jobs in (1, -1):
                elapsed = _time_significance_bands(
                    series,
                    n_surrogates=n_surrogates,
                    n_jobs=n_jobs,
                    info=mi_info,
                )
                results.append(
                    {
                        "n_surrogates": n_surrogates,
                        "series_length": series_length,
                        "n_jobs": n_jobs,
                        "elapsed_s": elapsed,
                    }
                )
    return results


def _print_summary(results: list[dict[str, object]]) -> None:
    """Print a human-readable summary table to stdout.

    Args:
        results: List of benchmark result records.
    """
    header = f"{'n_surr':>7}  {'n_obs':>7}  {'n_jobs':>7}  {'elapsed_s':>10}"
    print(header)
    print("-" * len(header))
    for row in results:
        elapsed = row["elapsed_s"]
        elapsed_str = f"{elapsed:.4f}" if isinstance(elapsed, float) else str(elapsed)
        print(
            f"{row['n_surrogates']:>7}  {row['series_length']:>7}  "
            f"{row['n_jobs']:>7}  {elapsed_str:>10}"
        )


def main() -> None:
    """Run significance parallel-policy benchmark and write JSON artifact."""
    version = importlib.metadata.version("forecastability")
    results = _run_benchmark()
    artifact: dict[str, object] = {
        "schema_version": 1,
        "artifact_type": "significance_parallel_benchmark",
        "forecastability_version": version,
        "max_lag": _MAX_LAG,
        "min_pairs": _MIN_PAIRS,
        "random_state": _RANDOM_STATE,
        "results": results,
    }
    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT_PATH.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _print_summary(results)
    print(f"\nWrote {_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
