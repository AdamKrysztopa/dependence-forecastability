"""Tests for _TriageCache — RVH-F06 request-scoped memoization.

Verifies that:
1. _TriageCache.scale_series returns the same object on repeated calls (memoized).
2. _TriageCache.normalised_psd returns the same tuple on repeated calls.
3. _TriageCache.ami_curve returns the same array on repeated calls and the
   underlying compute_ami is invoked exactly once.
4. Each _TriageCache instance is independent (no shared state between instances).
5. run_triage constructs a fresh _TriageCache per call (no global state leakage).
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import numpy as np

from forecastability.use_cases.run_triage import _TriageCache

# Importing _TriageCache above ensures the module is registered in sys.modules.
# We bind to the actual module object here (not the re-exported function from the
# package __init__, which shadows the module attribute on the package namespace).
rt_module = sys.modules["forecastability.use_cases.run_triage"]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RNG = np.random.default_rng(42)
SERIES = RNG.standard_normal(300)


# ---------------------------------------------------------------------------
# Unit tests: _TriageCache
# ---------------------------------------------------------------------------


class TestTriageCacheScaleSeries:
    """_TriageCache.scale_series memoization."""

    def test_same_array_returns_identical_object(self) -> None:
        cache = _TriageCache()
        result1 = cache.scale_series(SERIES)
        result2 = cache.scale_series(SERIES)
        assert result1 is result2, "Expected the same object on the second call (memoized)"

    def test_different_arrays_are_cached_separately(self) -> None:
        cache = _TriageCache()
        arr1 = RNG.standard_normal(200)
        arr2 = RNG.standard_normal(200)
        r1 = cache.scale_series(arr1)
        r2 = cache.scale_series(arr2)
        # They must not be the same object
        assert r1 is not r2

    def test_values_are_correct(self) -> None:
        cache = _TriageCache()
        arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = cache.scale_series(arr)
        expected = (arr - arr.mean()) / arr.std()
        np.testing.assert_allclose(result, expected)

    def test_fresh_cache_per_instance(self) -> None:
        arr = RNG.standard_normal(100)
        cache_a = _TriageCache()
        cache_b = _TriageCache()
        r_a = cache_a.scale_series(arr)
        r_b = cache_b.scale_series(arr)
        # Different cache instances — may or may not share the same object
        # but must always return numerically identical results.
        np.testing.assert_array_equal(r_a, r_b)


class TestTriageCacheNormalisedPsd:
    """_TriageCache.normalised_psd memoization."""

    def test_same_call_returns_identical_objects(self) -> None:
        cache = _TriageCache()
        freqs1, p1 = cache.normalised_psd(SERIES)
        freqs2, p2 = cache.normalised_psd(SERIES)
        assert freqs1 is freqs2
        assert p1 is p2

    def test_different_nperseg_cached_separately(self) -> None:
        cache = _TriageCache()
        _, p1 = cache.normalised_psd(SERIES, nperseg=64)
        _, p2 = cache.normalised_psd(SERIES, nperseg=128)
        # Different nperseg → different entry; arrays not identical
        assert p1 is not p2

    def test_probabilities_sum_to_one(self) -> None:
        cache = _TriageCache()
        _, p = cache.normalised_psd(SERIES)
        assert abs(p.sum() - 1.0) < 1e-9

    def test_underlying_compute_called_once(self) -> None:
        from forecastability.diagnostics.spectral_utils import (
            compute_normalised_psd as real_psd,
        )

        call_count = 0

        def counting_psd(arr: np.ndarray, **kw: object) -> tuple[np.ndarray, np.ndarray]:
            nonlocal call_count
            call_count += 1
            return real_psd(arr, **kw)  # type: ignore[arg-type]

        cache = _TriageCache()
        with patch("forecastability.use_cases.run_triage.compute_normalised_psd", counting_psd):
            cache.normalised_psd(SERIES)
            cache.normalised_psd(SERIES)  # should hit cache

        assert call_count == 1, (
            f"Expected compute_normalised_psd to be called once, got {call_count}"
        )


class TestTriageCacheAmiCurve:
    """_TriageCache.ami_curve memoization."""

    def test_same_call_returns_identical_object(self) -> None:
        cache = _TriageCache()
        r1 = cache.ami_curve(SERIES, 10, random_state=0)
        r2 = cache.ami_curve(SERIES, 10, random_state=0)
        assert r1 is r2

    def test_different_max_lag_cached_separately(self) -> None:
        cache = _TriageCache()
        r1 = cache.ami_curve(SERIES, 5, random_state=0)
        r2 = cache.ami_curve(SERIES, 10, random_state=0)
        assert r1 is not r2

    def test_different_random_state_cached_separately(self) -> None:
        cache = _TriageCache()
        r1 = cache.ami_curve(SERIES, 5, random_state=0)
        r2 = cache.ami_curve(SERIES, 5, random_state=1)
        assert r1 is not r2

    def test_underlying_compute_ami_called_once(self) -> None:
        """compute_ami must be invoked exactly once for the same (arr, params)."""
        cache = _TriageCache()
        call_count = 0
        original_compute_ami = __import__(
            "forecastability.metrics.metrics",
            fromlist=["compute_ami"],
        ).compute_ami

        def counting_compute_ami(arr, max_lag, **kw):
            nonlocal call_count
            call_count += 1
            return original_compute_ami(arr, max_lag, **kw)

        with patch(
            "forecastability.use_cases.run_triage.compute_ami",
            side_effect=counting_compute_ami,
        ):
            cache.ami_curve(SERIES, 5, random_state=42)
            cache.ami_curve(SERIES, 5, random_state=42)  # should hit cache

        assert call_count == 1, f"Expected compute_ami to be called once, got {call_count}"

    def test_result_has_correct_shape(self) -> None:
        cache = _TriageCache()
        result = cache.ami_curve(SERIES, 8, random_state=42)
        assert result.shape == (8,), f"Expected shape (8,), got {result.shape}"

    def test_result_is_non_negative(self) -> None:
        cache = _TriageCache()
        result = cache.ami_curve(SERIES, 5, random_state=42)
        assert (result >= 0.0).all(), "AMI values must be non-negative"


class TestTriageCacheIsolation:
    """Each _TriageCache instance must be independent."""

    def test_two_instances_do_not_share_cache(self) -> None:
        arr = RNG.standard_normal(200)
        cache_a = _TriageCache()
        cache_b = _TriageCache()
        r_a = cache_a.scale_series(arr)
        r_b = cache_b.scale_series(arr)
        # Values must match
        np.testing.assert_array_equal(r_a, r_b)
        # But internal dicts are different objects
        assert cache_a._scale_cache is not cache_b._scale_cache


class TestRunTriageCacheLifetime:
    """run_triage must construct a fresh _TriageCache per call."""

    def test_each_run_triage_call_gets_fresh_cache(self) -> None:
        """Verify no state leaks between two successive run_triage calls.

        Strategy: patch _TriageCache with a counting wrapper that records every
        instance created, then assert two distinct instances are produced.
        """
        from forecastability.triage.models import TriageRequest

        rng = np.random.default_rng(7)
        series = rng.standard_normal(300)
        request = TriageRequest(series=series, max_lag=5, n_surrogates=99, random_state=42)

        instances: list[_TriageCache] = []

        class _CapturingCache(_TriageCache):
            def __init__(self) -> None:
                super().__init__()
                instances.append(self)

        with patch.object(rt_module, "_TriageCache", _CapturingCache):
            rt_module.run_triage(request)
            rt_module.run_triage(request)

        assert len(instances) == 2, (
            f"Expected 2 _TriageCache instances (one per call), got {len(instances)}"
        )
        assert instances[0] is not instances[1], (
            "Each run_triage call must produce a fresh _TriageCache instance"
        )
