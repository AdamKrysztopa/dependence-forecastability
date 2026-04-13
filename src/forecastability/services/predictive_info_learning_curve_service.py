"""Application service that builds PredictiveInfoLearningCurve (F3).

Evaluates EvoRate(k) = I(X_{t-k:t}; X_{t+1}) for k = 1..effective_max_k
using the kNN mutual information estimator, detects a plateau/convergence
point, and recommends a minimal sufficient lookback length.
"""

from __future__ import annotations

import numpy as np
from sklearn.preprocessing import StandardScaler

from forecastability.triage.predictive_info_learning_curve import PredictiveInfoLearningCurve

_MAX_K_CAP: int = 8
_N_WARN_THRESHOLD: int = 1000
_N_NEIGHBORS: int = 8
_MIN_SAMPLES_FOR_ESTIMATION: int = 24


def _scale(arr: np.ndarray) -> np.ndarray:
    """Standardise a 1-D array to zero mean and unit variance.

    Args:
        arr: Input 1-D array.

    Returns:
        Standardised 1-D array of the same length.
    """
    return StandardScaler().fit_transform(arr.reshape(-1, 1)).ravel()


def _build_warnings(n: int, effective_max_k: int, *, max_k: int) -> list[str]:
    """Build reliability warnings based on series length and lookback cap.

    Args:
        n: Number of observations in the series.
        effective_max_k: Effective maximum lookback used.
        max_k: Original user-requested max_k (before cap).

    Returns:
        List of warning strings; empty when no concerns apply.
    """
    warnings: list[str] = []
    if n < _N_WARN_THRESHOLD:
        warnings.append(
            f"Series length {n} < {_N_WARN_THRESHOLD}: kNN MI estimates are unreliable for k > 3."
        )
    if max_k > _MAX_K_CAP:
        warnings.append(
            f"Lookback capped at k={_MAX_K_CAP} (max={_MAX_K_CAP}) "
            "to limit curse of dimensionality."
        )
    return warnings


def _estimate_evo_rate(
    arr: np.ndarray,
    k: int,
    *,
    n_neighbors: int,
    random_state: int,
) -> float:
    """Estimate EvoRate(k) = I(X_{t-k:t}; X_{t+1}) via kNN.

    Builds a past matrix of shape ``(n-k, k)`` where each row is a
    k-dimensional embedding window, and estimates MI against the one-step
    future target.

    Args:
        arr: Standardised 1-D time series array of length n.
        k: Lookback (embedding dimension).
        n_neighbors: Number of neighbours for the kNN estimator.
        random_state: Deterministic seed for the estimator.

    Returns:
        Non-negative MI estimate in nats; 0.0 when too few samples.
    """
    n = arr.size
    if n - k < _MIN_SAMPLES_FOR_ESTIMATION:
        return 0.0
    past = np.column_stack([arr[i : n - k + i] for i in range(k)])  # (n-k, k)
    future = arr[k:]  # (n-k,)
    return _estimate_joint_mi(past, future, n_neighbors=n_neighbors, random_state=random_state)


def _estimate_joint_mi(
    past: np.ndarray,
    future: np.ndarray,
    *,
    n_neighbors: int,
    random_state: int,
) -> float:
    """Estimate I(past_block; X_{t+1}) using the KSG estimator 1.

    Handles k-dimensional past and scalar future via the Chebyshev-metric
    joint-space kNN approach (Kraskov et al. 2004, estimator 1).

    Args:
        past: Shape (n, k) — each row is a k-dimensional past window.
        future: Shape (n,) — corresponding one-step-ahead values.
        n_neighbors: Number of nearest neighbours.
        random_state: Seed for tie-breaking jitter.

    Returns:
        Non-negative float MI estimate (nats).
    """
    from scipy.spatial import cKDTree  # type: ignore[attr-defined]
    from scipy.special import digamma

    n = past.shape[0]
    y = future.reshape(-1, 1)
    rng = np.random.default_rng(random_state)

    # Stack joint space [past | future], add tiny jitter for tie-breaking
    joint = np.hstack([past, y]).astype(float)
    joint += rng.standard_normal(joint.shape) * 1e-10

    # k-nearest in joint Chebyshev space (L∞ norm = max-norm, standard for KSG)
    kd_joint = cKDTree(joint)
    distances, _ = kd_joint.query(joint, k=n_neighbors + 1, p=np.inf, workers=1)
    radius = distances[:, n_neighbors]  # distance to k-th neighbor
    radius = np.nextafter(radius, 0.0)  # open ball (strict inequality)

    # Count neighbors in marginal spaces (consistent Chebyshev metric)
    kd_past = cKDTree(joint[:, :-1])  # past subspace
    kd_fut = cKDTree(joint[:, -1:])  # future subspace (1-D)

    nx = np.array(
        [len(nb) - 1 for nb in kd_past.query_ball_point(joint[:, :-1], r=radius, p=np.inf)]
    )
    ny = np.array(
        [len(nb) - 1 for nb in kd_fut.query_ball_point(joint[:, -1:], r=radius, p=np.inf)]
    )

    mi = float(digamma(n_neighbors) + digamma(n) - np.mean(digamma(nx + 1) + digamma(ny + 1)))
    return max(0.0, mi)


def _detect_plateau(
    values: list[float],
    *,
    plateau_tol: float,
    plateau_min_consecutive: int,
) -> tuple[bool, int]:
    """Detect whether the information curve has plateaued.

    A plateau is declared when the relative marginal gain
    ``(I(k) - I(k-1)) / I(k-1)`` falls below ``plateau_tol`` for at least
    ``plateau_min_consecutive`` consecutive steps.

    Args:
        values: Sequence of I_pred estimates for k=1, 2, ...
        plateau_tol: Relative-gain threshold below which a step is
            considered non-informative.
        plateau_min_consecutive: Minimum run length of sub-threshold steps
            required to declare a plateau.

    Returns:
        Tuple of ``(plateau_detected, convergence_index)`` where
        ``convergence_index`` is the 0-based index of the first step in
        the plateau run, or -1 when no plateau is found.
    """
    if len(values) < 2:
        return False, -1
    consecutive = 0
    for i in range(1, len(values)):
        prev = values[i - 1]
        gain = values[i] - prev
        if prev > 1e-9:
            relative_gain = gain / prev
        else:
            # Both prev and current are near zero → flat near-zero curve → plateau
            # But if gain is nonzero while prev≈0, the curve is still rising
            relative_gain = 0.0 if abs(gain) < 1e-9 else float("inf")
        if relative_gain < plateau_tol:
            consecutive += 1
            if consecutive >= plateau_min_consecutive:
                return True, i - plateau_min_consecutive + 1
        else:
            consecutive = 0
    return False, -1


def build_predictive_info_learning_curve(
    series: np.ndarray | list[float],
    *,
    max_k: int = 8,
    n_neighbors: int = _N_NEIGHBORS,
    random_state: int = 42,
    plateau_tol: float = 0.05,
    plateau_min_consecutive: int = 2,
) -> PredictiveInfoLearningCurve:
    """Build a predictive-information learning curve for ``series``.

    Evaluates EvoRate(k) = I(X_{t-k:t}; X_{t+1}) for k=1..effective_max_k,
    detects a plateau/convergence point, and recommends a minimal sufficient
    lookback length.

    Args:
        series: Univariate time series (array-like, at least 20 values).
        max_k: Maximum lookback length; hard-capped at 8 to limit the
            curse of dimensionality.
        n_neighbors: Number of neighbours for the kNN MI estimator.
        random_state: Deterministic seed.
        plateau_tol: Relative-gain threshold for plateau detection.
        plateau_min_consecutive: Consecutive sub-threshold steps needed to
            declare a plateau.

    Returns:
        A frozen
        :class:`~forecastability.triage.predictive_info_learning_curve.PredictiveInfoLearningCurve`.
    """
    arr = _scale(np.asarray(series, dtype=float).ravel())
    n = arr.size
    effective_max_k = min(max_k, _MAX_K_CAP)
    warnings = _build_warnings(n, effective_max_k, max_k=max_k)

    window_sizes: list[int] = []
    information_values: list[float] = []
    for k in range(1, effective_max_k + 1):
        if n - k < 24:
            break
        val = _estimate_evo_rate(
            arr,
            k,
            n_neighbors=n_neighbors,
            random_state=random_state + k,
        )
        window_sizes.append(k)
        information_values.append(val)

    plateau_detected, conv_idx = _detect_plateau(
        information_values,
        plateau_tol=plateau_tol,
        plateau_min_consecutive=plateau_min_consecutive,
    )
    if plateau_detected and conv_idx >= 0:
        recommended_lookback = window_sizes[conv_idx]
    else:
        recommended_lookback = window_sizes[-1] if window_sizes else 1

    return PredictiveInfoLearningCurve(
        window_sizes=window_sizes,
        information_values=information_values,
        convergence_index=conv_idx,
        recommended_lookback=recommended_lookback,
        plateau_detected=plateau_detected,
        reliability_warnings=warnings,
    )
