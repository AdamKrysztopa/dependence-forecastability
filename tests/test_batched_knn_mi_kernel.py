"""Tests for PBE-F23: BatchedKnnMiKernel Protocol and PurePythonBatchedKnnMiKernel."""

from __future__ import annotations

import numpy as np
from sklearn.feature_selection import mutual_info_regression

from forecastability.kernels.batched_knn_mi import PurePythonBatchedKnnMiKernel
from forecastability.ports.kernels import BatchedKnnMiKernel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RNG = np.random.default_rng(0)


def _make_pair(n: int = 300, *, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    past = rng.standard_normal(n)
    future = 0.6 * past + rng.standard_normal(n) * 0.8
    return past.astype(np.float64), future.astype(np.float64)


def _scalar_mi(
    past: np.ndarray, future: np.ndarray, *, n_neighbors: int, random_state: int
) -> float:
    """Reference single-pair MI using the same estimator as the codebase."""
    return float(
        mutual_info_regression(
            past.reshape(-1, 1),
            future,
            n_neighbors=n_neighbors,
            discrete_features=False,
            random_state=random_state,
        )[0]
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_batched_knn_mi_protocol_conformance() -> None:
    """PurePythonBatchedKnnMiKernel must satisfy the BatchedKnnMiKernel Protocol."""
    assert isinstance(PurePythonBatchedKnnMiKernel(), BatchedKnnMiKernel)


def test_batched_knn_mi_parity_single_pair() -> None:
    """Batch result for a single pair must match the scalar MI path within atol=1e-9."""
    past, future = _make_pair(300, seed=1)
    kernel = PurePythonBatchedKnnMiKernel()

    batch_result = kernel.batched_knn_mi([(past, future)], n_neighbors=8, random_state=42)[0]
    scalar_result = _scalar_mi(past, future, n_neighbors=8, random_state=42)

    assert abs(batch_result - scalar_result) < 1e-9, (
        f"Parity violation: batch={batch_result}, scalar={scalar_result}"
    )


def test_batched_knn_mi_parity_multiple_pairs() -> None:
    """Batch result for 5 pairs must equal loop-applied scalar MI element-wise (atol=1e-9)."""
    pairs = [_make_pair(200, seed=i) for i in range(5)]
    kernel = PurePythonBatchedKnnMiKernel()

    batch_results = kernel.batched_knn_mi(pairs, n_neighbors=8, random_state=7)
    scalar_results = np.array(
        [_scalar_mi(p, f, n_neighbors=8, random_state=7) for p, f in pairs],
        dtype=np.float64,
    )

    np.testing.assert_allclose(batch_results, scalar_results, atol=1e-9, rtol=0)


def test_batched_knn_mi_non_negative() -> None:
    """All returned MI estimates must be >= 0, even for independent noise."""
    rng = np.random.default_rng(99)
    pairs = [(rng.standard_normal(150), rng.standard_normal(150)) for _ in range(10)]
    kernel = PurePythonBatchedKnnMiKernel()

    results = kernel.batched_knn_mi(pairs, n_neighbors=8, random_state=0)
    assert results.dtype == np.float64
    assert np.all(results >= 0.0), f"Negative MI values found: {results[results < 0]}"


def test_batched_knn_mi_empty_input() -> None:
    """Empty input must return an empty float64 array without error."""
    kernel = PurePythonBatchedKnnMiKernel()
    result = kernel.batched_knn_mi([], n_neighbors=8, random_state=0)

    assert isinstance(result, np.ndarray)
    assert result.shape == (0,)
    assert result.dtype == np.float64


def test_batched_knn_mi_deterministic() -> None:
    """Two calls with the same random_state must return identical results."""
    pairs = [_make_pair(250, seed=i) for i in range(4)]
    kernel = PurePythonBatchedKnnMiKernel()

    result_a = kernel.batched_knn_mi(pairs, n_neighbors=8, random_state=42)
    result_b = kernel.batched_knn_mi(pairs, n_neighbors=8, random_state=42)

    np.testing.assert_array_equal(result_a, result_b)
