"""Deterministic ordinal-complexity summaries for the extended fingerprint."""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike

from forecastability.services._extended_diagnostic_validation import (
    coerce_univariate_values,
    validate_embedding_dimension,
)
from forecastability.triage.extended_forecastability import OrdinalComplexityResult

_DEGENERATE_NOTE = "constant series; ordinal complexity is degenerate"
_SHORT_SERIES_NOTE = "series is too short for the requested ordinal embedding"
_UNSTABLE_SAMPLE_NOTE = (
    "ordinal pattern counts are sparse for this embedding; interpret conservatively"
)
_TIE_POLICY_NOTE = "ordinal ties use an average-rank policy with tie-aware normalization"


def _build_embeddings(values: np.ndarray, *, embedding_dimension: int, delay: int) -> np.ndarray:
    """Construct the ordinal embedding matrix."""
    n_vectors = values.size - (embedding_dimension - 1) * delay
    if n_vectors <= 0:
        return np.empty((0, embedding_dimension), dtype=float)
    starts = np.arange(n_vectors, dtype=int)[:, None]
    offsets = (np.arange(embedding_dimension, dtype=int) * delay)[None, :]
    return values[starts + offsets]


def _normalized_entropy(probabilities: np.ndarray, *, cardinality: int, eps: float) -> float:
    """Compute a unit-scale entropy from discrete probabilities."""
    if probabilities.size == 0 or cardinality <= 1:
        return 0.0
    safe_probabilities = np.clip(probabilities.astype(float), a_min=eps, a_max=None)
    safe_probabilities = safe_probabilities / safe_probabilities.sum()
    entropy = -float(np.sum(safe_probabilities * np.log(safe_probabilities)))
    return float(np.clip(entropy / max(math.log(float(cardinality)), eps), 0.0, 1.0))


def _ordinal_state_cardinality(
    embedding_dimension: int,
    *,
    includes_ties: bool,
) -> int:
    """Return the deterministic ordinal state count for the chosen tie policy."""
    if not includes_ties:
        return math.factorial(embedding_dimension)

    stirling = [[0] * (embedding_dimension + 1) for _ in range(embedding_dimension + 1)]
    stirling[0][0] = 1
    for n_observations in range(1, embedding_dimension + 1):
        for n_groups in range(1, n_observations + 1):
            stirling[n_observations][n_groups] = (
                stirling[n_observations - 1][n_groups - 1]
                + n_groups * stirling[n_observations - 1][n_groups]
            )
    return sum(
        math.factorial(n_groups) * stirling[embedding_dimension][n_groups]
        for n_groups in range(1, embedding_dimension + 1)
    )


def _encode_tie_aware_patterns(
    embeddings: np.ndarray,
    *,
    eps: float,
) -> tuple[np.ndarray, int]:
    """Encode ordinal patterns with equal values sharing the same average rank."""
    patterns = np.empty_like(embeddings, dtype=float)
    tie_rows = 0
    for row_index, row in enumerate(embeddings):
        order = np.argsort(row, kind="mergesort")
        sorted_row = row[order]
        row_pattern = np.empty(row.size, dtype=float)
        start = 0
        row_has_tie = False
        while start < row.size:
            end = start + 1
            while end < row.size and abs(float(sorted_row[end] - sorted_row[start])) <= eps:
                end += 1
            average_rank = 0.5 * float(start + end - 1)
            row_pattern[order[start:end]] = average_rank
            if end - start > 1:
                row_has_tie = True
            start = end
        if row_has_tie:
            tie_rows += 1
        patterns[row_index] = row_pattern
    return patterns, tie_rows


def _classify_complexity(
    *,
    permutation_entropy: float,
    weighted_permutation_entropy: float | None,
    ordinal_redundancy: float,
    degenerate: bool,
) -> Literal[
    "degenerate",
    "regular",
    "structured_nonlinear",
    "complex_but_redundant",
    "noise_like",
    "unclear",
]:
    """Map entropy summaries to a deterministic complexity class."""
    if degenerate:
        return "degenerate"
    if permutation_entropy <= 0.55:
        return "regular"
    if permutation_entropy >= 0.9 and (
        weighted_permutation_entropy is None or weighted_permutation_entropy >= 0.85
    ):
        return "noise_like"
    if (
        weighted_permutation_entropy is not None
        and (permutation_entropy - weighted_permutation_entropy) >= 0.05
        and ordinal_redundancy >= 0.08
    ):
        return "complex_but_redundant"
    if (
        weighted_permutation_entropy is not None
        and permutation_entropy >= 0.75
        and weighted_permutation_entropy <= 0.7
        and ordinal_redundancy >= 0.1
    ):
        return "complex_but_redundant"
    if (
        weighted_permutation_entropy is not None
        and weighted_permutation_entropy <= 0.75
        and ordinal_redundancy >= 0.2
    ):
        return "structured_nonlinear"
    if ordinal_redundancy >= 0.3:
        return "structured_nonlinear"
    return "unclear"


def compute_ordinal_complexity(
    values: ArrayLike,
    *,
    embedding_dimension: int = 3,
    delay: int = 1,
    include_weighted: bool = True,
    eps: float = 1e-12,
) -> OrdinalComplexityResult:
    """Compute permutation-entropy-based ordinal complexity diagnostics.

    Args:
        values: Univariate series values to analyze.
        embedding_dimension: Ordinal embedding dimension.
        delay: Delay between successive embedding coordinates.
        include_weighted: Whether the weighted entropy variant should be computed.
        eps: Small numerical floor for safe normalization.

    Returns:
        Ordinal complexity result with normalized entropy summaries.
    """
    validate_embedding_dimension(embedding_dimension)
    arr = coerce_univariate_values(values)
    if delay <= 0:
        raise ValueError("delay must be positive")
    if float(np.ptp(arr)) <= eps:
        return OrdinalComplexityResult(
            permutation_entropy=0.0,
            weighted_permutation_entropy=0.0 if include_weighted else None,
            ordinal_redundancy=1.0,
            embedding_dimension=embedding_dimension,
            delay=delay,
            complexity_class="degenerate",
            notes=[_DEGENERATE_NOTE],
        )

    embeddings = _build_embeddings(
        arr,
        embedding_dimension=embedding_dimension,
        delay=delay,
    )
    if embeddings.shape[0] == 0:
        return OrdinalComplexityResult(
            permutation_entropy=1.0,
            weighted_permutation_entropy=1.0 if include_weighted else None,
            ordinal_redundancy=0.0,
            embedding_dimension=embedding_dimension,
            delay=delay,
            complexity_class="unclear",
            notes=[_SHORT_SERIES_NOTE],
        )

    patterns, tie_rows = _encode_tie_aware_patterns(embeddings, eps=eps)
    _, inverse, counts = np.unique(
        patterns,
        axis=0,
        return_inverse=True,
        return_counts=True,
    )
    probabilities = counts.astype(float) / float(counts.sum())
    cardinality = _ordinal_state_cardinality(
        embedding_dimension,
        includes_ties=tie_rows > 0,
    )
    permutation_entropy = _normalized_entropy(
        probabilities,
        cardinality=cardinality,
        eps=eps,
    )
    ordinal_redundancy = float(np.clip(1.0 - permutation_entropy, 0.0, 1.0))

    weighted_permutation_entropy: float | None = None
    if include_weighted:
        weights = np.var(embeddings, axis=1)
        total_weight = float(np.sum(weights))
        if total_weight <= eps:
            weighted_permutation_entropy = 0.0
        else:
            weighted_counts = np.bincount(inverse, weights=weights, minlength=counts.size)
            weighted_probabilities = weighted_counts / total_weight
            weighted_permutation_entropy = _normalized_entropy(
                weighted_probabilities,
                cardinality=cardinality,
                eps=eps,
            )

    notes: list[str] = []
    if tie_rows > 0:
        notes.append(_TIE_POLICY_NOTE)
    sparse_embedding = embeddings.shape[0] < max(cardinality, 10)
    if sparse_embedding:
        if embeddings.shape[0] < cardinality:
            notes.append(_SHORT_SERIES_NOTE)
        notes.append(_UNSTABLE_SAMPLE_NOTE)

    complexity_class = (
        "unclear"
        if sparse_embedding
        else _classify_complexity(
            permutation_entropy=permutation_entropy,
            weighted_permutation_entropy=weighted_permutation_entropy,
            ordinal_redundancy=ordinal_redundancy,
            degenerate=False,
        )
    )
    return OrdinalComplexityResult(
        permutation_entropy=permutation_entropy,
        weighted_permutation_entropy=weighted_permutation_entropy,
        ordinal_redundancy=ordinal_redundancy,
        embedding_dimension=embedding_dimension,
        delay=delay,
        complexity_class=complexity_class,
        notes=notes,
    )
