"""Sparse lag selection service for lagged exogenous triage.

The ``xami_sparse`` selector is a deterministic, greedy lag-pruning layer for
predictive lags (``k >= 1``). It is designed for feature triage, not causal
identification.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LinearRegression

from forecastability.metrics import _scale_series
from forecastability.metrics.scorers import DependenceScorer
from forecastability.utils.types import LaggedExogSelectionRow, LagSelectorLabel
from forecastability.utils.validation import validate_time_series


@dataclass(frozen=True, slots=True)
class SparseLagSelectionConfig:
    """Versioned thresholds for the ``xami_sparse`` selector.

    Attributes:
        selector_name: Stable selector identifier.
        max_selected_per_driver: Maximum number of selected lags per driver.
        score_threshold: Absolute score threshold for candidate admission.
        relative_threshold: Relative threshold as fraction of baseline best score.
        min_lag: Minimum candidate lag considered by the selector.
    """

    selector_name: LagSelectorLabel = "xami_sparse"
    max_selected_per_driver: int = 3
    score_threshold: float = 0.02
    relative_threshold: float = 0.20
    min_lag: int = 1

    def __post_init__(self) -> None:
        """Validate selector configuration invariants."""
        if self.selector_name != "xami_sparse":
            raise ValueError(
                "SparseLagSelectionConfig.selector_name must be 'xami_sparse', "
                f"got {self.selector_name!r}"
            )
        if self.max_selected_per_driver < 1:
            raise ValueError("max_selected_per_driver must be >= 1")
        if self.score_threshold < 0.0:
            raise ValueError("score_threshold must be >= 0")
        if not (0.0 <= self.relative_threshold <= 1.0):
            raise ValueError("relative_threshold must be in [0, 1]")
        if self.min_lag < 1:
            raise ValueError("min_lag must be >= 1")


_DEFAULT_SPARSE_LAG_SELECTION_CONFIG = SparseLagSelectionConfig()


def _build_aligned_pair(
    target: np.ndarray,
    driver: np.ndarray,
    *,
    lag: int,
    selected_lags: tuple[int, ...],
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Build aligned candidate pair and optional conditioning matrix.

    Args:
        target: Scaled target series.
        driver: Scaled driver series.
        lag: Candidate lag ``k``.
        selected_lags: Already selected lags for the same driver.

    Returns:
        Tuple ``(x_candidate, y_target, z_conditioning_or_none)``.
    """
    anchor = max((lag, *selected_lags), default=lag)
    y = target[anchor:]
    x = driver[anchor - lag : driver.size - lag]

    if len(selected_lags) == 0:
        return x, y, None

    z_cols = [driver[anchor - s : driver.size - s] for s in selected_lags]
    z = np.column_stack(z_cols)
    return x, y, z


def _residualize_against_selected(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Residualize candidate and target on selected-lag conditioning matrix."""
    if z is None or z.shape[1] == 0:
        return x, y
    model_x = LinearRegression().fit(z, x)
    model_y = LinearRegression().fit(z, y)
    return x - model_x.predict(z), y - model_y.predict(z)


def _is_insufficient_pairs_error(exc: ValueError) -> bool:
    """Return whether *exc* reflects an expected sample-size scoring failure."""
    message = str(exc).lower()
    if len(message) == 0:
        return False
    return any(
        token in message
        for token in (
            "insufficient",
            "too few",
            "not enough",
            "min_pairs",
            "n_samples",
            "sample",
            "pair",
            "row",
        )
    )


def _score_candidate(
    target: np.ndarray,
    driver: np.ndarray,
    *,
    lag: int,
    selected_lags: tuple[int, ...],
    scorer: DependenceScorer,
    random_state: int,
) -> float:
    """Score one candidate lag under current selected-lag conditioning."""
    x, y, z = _build_aligned_pair(target, driver, lag=lag, selected_lags=selected_lags)
    if x.size < 30:
        return 0.0

    res_x, res_y = _residualize_against_selected(x, y, z)
    try:
        value = float(scorer(res_x, res_y, random_state=random_state))
    except ValueError as exc:
        if _is_insufficient_pairs_error(exc):
            return 0.0
        raise
    if not np.isfinite(value):
        return 0.0
    return max(value, 0.0)


def _passes_selection_thresholds(
    score: float,
    *,
    baseline_best: float,
    config: SparseLagSelectionConfig,
) -> bool:
    """Check absolute and relative admission thresholds for one candidate."""
    if score < config.score_threshold:
        return False
    relative_floor = config.relative_threshold * baseline_best
    return score >= relative_floor


def select_sparse_lags(
    target: np.ndarray,
    driver: np.ndarray,
    *,
    max_lag: int,
    scorer: DependenceScorer,
    config: SparseLagSelectionConfig = _DEFAULT_SPARSE_LAG_SELECTION_CONFIG,
    random_state: int = 42,
    target_name: str = "target",
    driver_name: str = "driver",
) -> list[LaggedExogSelectionRow]:
    """Select sparse predictive lags with greedy redundancy-aware pruning.

    The selector evaluates only predictive lags and never emits ``lag=0`` rows.
    It starts from the strongest candidate, then greedily adds additional lags
    only when they pass both absolute and relative thresholds.

    Args:
        target: Target univariate time series.
        driver: Exogenous driver series aligned with *target*.
        max_lag: Maximum lag considered for selection.
        scorer: Dependence scorer used for candidate ranking.
        config: Selector configuration and thresholds.
        random_state: Base random seed for scorer evaluation.
        target_name: Label used in output rows.
        driver_name: Label used in output rows.

    Returns:
        One :class:`LaggedExogSelectionRow` per evaluated candidate lag.

    Raises:
        ValueError: If series shapes mismatch.
    """
    if max_lag < 1:
        raise ValueError(f"max_lag must be >= 1, got {max_lag}")

    validated_target = validate_time_series(target, min_length=max_lag + 2)
    validated_driver = validate_time_series(driver, min_length=max_lag + 2)
    if validated_target.shape != validated_driver.shape:
        raise ValueError("driver and target must have identical lengths")

    scaled_target = _scale_series(validated_target)
    scaled_driver = _scale_series(validated_driver)

    candidate_lags = list(range(max(1, config.min_lag), max_lag + 1))
    if len(candidate_lags) == 0:
        return []

    base_scores: dict[int, float] = {
        lag: _score_candidate(
            scaled_target,
            scaled_driver,
            lag=lag,
            selected_lags=(),
            scorer=scorer,
            random_state=random_state + lag,
        )
        for lag in candidate_lags
    }

    baseline_best = max(base_scores.values())
    last_scores = dict(base_scores)

    strongest_lag, _ = min(base_scores.items(), key=lambda item: (-item[1], item[0]))
    selected_lags: list[int] = [strongest_lag]
    remaining_lags = [lag for lag in candidate_lags if lag != strongest_lag]

    while remaining_lags and len(selected_lags) < config.max_selected_per_driver:
        candidate_scores: dict[int, float] = {}
        for lag in remaining_lags:
            score = _score_candidate(
                scaled_target,
                scaled_driver,
                lag=lag,
                selected_lags=tuple(selected_lags),
                scorer=scorer,
                random_state=random_state + lag + 1000 * len(selected_lags),
            )
            candidate_scores[lag] = score
            last_scores[lag] = score

        best_lag, best_score = min(candidate_scores.items(), key=lambda item: (-item[1], item[0]))
        if not _passes_selection_thresholds(best_score, baseline_best=baseline_best, config=config):
            break

        selected_lags.append(best_lag)
        remaining_lags.remove(best_lag)

    selection_order_map = {lag: index for index, lag in enumerate(selected_lags, start=1)}
    selected_lag_set = set(selected_lags)

    return [
        LaggedExogSelectionRow(
            target=target_name,
            driver=driver_name,
            lag=lag,
            selected_for_tensor=lag in selected_lag_set,
            selection_order=selection_order_map.get(lag),
            selector_name=config.selector_name,
            score=float(last_scores[lag]),
            tensor_role="predictive",
        )
        for lag in candidate_lags
    ]
