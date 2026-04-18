"""Directional transfer-entropy diagnostics built on the CMI backend."""

from __future__ import annotations

from typing import Literal

import numpy as np

from forecastability.diagnostics.cmi import (
    CMIBackendName,
    compute_conditional_mi_with_backend,
)
from forecastability.utils.validation import validate_time_series

_CONDITIONAL_MIN_PAIRS_FLOOR = 50


def _resolve_history(*, lag: int, history: int | None) -> int:
    """Return validated target-history depth for TE conditioning.

    The canonical TE formulation at lag ``L`` conditions on
    ``Y_{t-1}, ..., Y_{t-L+1}``, which has depth ``L - 1``.
    """
    if lag < 1:
        raise ValueError(f"lag must be >= 1; got {lag}")
    if history is None:
        return lag - 1
    if history < 0:
        raise ValueError(f"history must be >= 0; got {history}")
    if history > lag - 1:
        raise ValueError(
            "history must be <= lag - 1 to preserve causal ordering in "
            f"TE(X->Y | lag={lag}); got history={history}"
        )
    return history


def _build_target_history_matrix(
    target: np.ndarray,
    *,
    lag: int,
    history: int,
) -> np.ndarray:
    """Build aligned target-history matrix for TE conditioning."""
    n_rows = target.size - lag
    if history == 0:
        return np.empty((n_rows, 0), dtype=float)
    cols = [target[lag - h : target.size - h] for h in range(1, history + 1)]
    return np.column_stack(cols)


def _validate_directional_pair(
    source: np.ndarray,
    target: np.ndarray,
    *,
    lag: int,
    min_pairs: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Validate source/target series for directional TE estimation."""
    min_length = lag + min_pairs
    source_validated = validate_time_series(source, min_length=min_length)
    target_validated = validate_time_series(target, min_length=min_length)
    if source_validated.size != target_validated.size:
        raise ValueError(
            "source and target must have identical lengths; "
            f"got {source_validated.size} and {target_validated.size}"
        )
    return source_validated, target_validated


def _validate_conditional_te_sample_size(
    *,
    n_rows: int,
    history: int,
    min_pairs: int,
) -> None:
    """Validate robust sample-size safeguards for conditional TE estimation."""
    if min_pairs < _CONDITIONAL_MIN_PAIRS_FLOOR:
        raise ValueError(f"min_pairs must be >= 50 for conditional estimators; got {min_pairs}")
    if history > 0 and n_rows < 2 * min_pairs:
        raise ValueError(
            "TE with non-empty history requires at least 2 * min_pairs aligned rows; "
            f"got rows={n_rows}, min_pairs={min_pairs}"
        )


def compute_transfer_entropy(
    source: np.ndarray,
    target: np.ndarray,
    *,
    lag: int,
    history: int | None = None,
    backend: CMIBackendName = "linear_residual",
    rf_estimators: int = 200,
    rf_max_depth: int | None = 8,
    et_estimators: int = 300,
    et_max_depth: int | None = 10,
    n_neighbors: int = 8,
    min_pairs: int = 50,
    random_state: int = 42,
) -> float:
    r"""Compute directional transfer entropy $TE(X \to Y \mid \text{lag})$.

    Implements the conditional-MI formulation:

    ``TE(X -> Y | lag) = I(Y_t ; X_{t-lag} | Y_{t-1}, ..., Y_{t-lag+1})``.

    Args:
        source: Source series ``X``.
        target: Target series ``Y``.
        lag: Source lag in the directional relation ``X_{t-lag} -> Y_t``.
        history: Number of target-history lags to condition on. ``None`` uses
            the canonical ``lag - 1`` depth.
        backend: Residualization backend for CMI estimation.
        rf_estimators: Number of trees for RF backend.
        rf_max_depth: Optional max depth for RF backend.
        et_estimators: Number of trees for extra-trees backend.
        et_max_depth: Optional max depth for extra-trees backend.
        n_neighbors: Number of neighbors for kNN MI estimation.
        min_pairs: Minimum aligned sample pairs after lagging.
        random_state: Deterministic seed.

    Returns:
        Non-negative TE estimate.

    Raises:
        ValueError: If lag/history constraints or sample-length constraints fail.
    """
    resolved_history = _resolve_history(lag=lag, history=history)
    source_validated, target_validated = _validate_directional_pair(
        source,
        target,
        lag=lag,
        min_pairs=min_pairs,
    )
    _validate_conditional_te_sample_size(
        n_rows=target_validated.size - lag,
        history=resolved_history,
        min_pairs=min_pairs,
    )

    source_lagged = source_validated[:-lag]
    target_future = target_validated[lag:]
    conditioning = _build_target_history_matrix(
        target_validated,
        lag=lag,
        history=resolved_history,
    )

    return compute_conditional_mi_with_backend(
        source_lagged,
        target_future,
        conditioning=conditioning,
        backend=backend,
        rf_estimators=rf_estimators,
        rf_max_depth=rf_max_depth,
        et_estimators=et_estimators,
        et_max_depth=et_max_depth,
        n_neighbors=n_neighbors,
        min_pairs=min_pairs,
        random_state=random_state,
    )


def compute_transfer_entropy_curve(
    source: np.ndarray,
    target: np.ndarray,
    *,
    max_lag: int,
    history_mode: Literal["canonical", "fixed"] = "canonical",
    fixed_history: int | None = None,
    backend: CMIBackendName = "linear_residual",
    rf_estimators: int = 200,
    rf_max_depth: int | None = 8,
    et_estimators: int = 300,
    et_max_depth: int | None = 10,
    n_neighbors: int = 8,
    min_pairs: int = 50,
    random_state: int = 42,
) -> np.ndarray:
    """Compute directional TE for lags ``1..max_lag``.

    Args:
        source: Source series ``X``.
        target: Target series ``Y``.
        max_lag: Maximum lag to evaluate.
        history_mode: ``"canonical"`` uses ``history=lag-1`` per lag,
            ``"fixed"`` uses ``fixed_history`` for every lag.
        fixed_history: Fixed target-history depth when ``history_mode="fixed"``.
        backend: Residualization backend for CMI estimation.
        rf_estimators: Number of trees for RF backend.
        rf_max_depth: Optional max depth for RF backend.
        et_estimators: Number of trees for extra-trees backend.
        et_max_depth: Optional max depth for extra-trees backend.
        n_neighbors: Number of neighbors for kNN MI estimation.
        min_pairs: Minimum aligned sample pairs after lagging.
        random_state: Deterministic seed.

    Returns:
        1-D array of shape ``(max_lag,)`` with TE per lag.
    """
    if max_lag < 1:
        raise ValueError(f"max_lag must be >= 1; got {max_lag}")
    if history_mode not in {"canonical", "fixed"}:
        raise ValueError("history_mode must be one of {'canonical', 'fixed'}")

    curve = np.zeros(max_lag, dtype=float)
    for lag in range(1, max_lag + 1):
        history = None if history_mode == "canonical" else fixed_history
        curve[lag - 1] = compute_transfer_entropy(
            source,
            target,
            lag=lag,
            history=history,
            backend=backend,
            rf_estimators=rf_estimators,
            rf_max_depth=rf_max_depth,
            et_estimators=et_estimators,
            et_max_depth=et_max_depth,
            n_neighbors=n_neighbors,
            min_pairs=min_pairs,
            random_state=random_state + lag,
        )
    return curve
