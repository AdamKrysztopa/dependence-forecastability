"""Rolling-origin split construction."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from forecastability.utils.validation import validate_time_series


@dataclass(slots=True)
class RollingSplit:
    """Train-test split for one rolling origin."""

    origin_index: int
    train: np.ndarray
    test: np.ndarray


def build_expanding_window_splits(
    ts: np.ndarray,
    *,
    n_origins: int,
    horizon: int,
) -> list[RollingSplit]:
    """Build expanding-window rolling-origin splits."""
    if n_origins < 1:
        raise ValueError("n_origins must be >= 1")
    if horizon < 1:
        raise ValueError("horizon must be >= 1")

    arr = validate_time_series(ts, min_length=(n_origins * horizon) + 21)

    splits: list[RollingSplit] = []
    first_origin = arr.size - n_origins * horizon

    for index in range(n_origins):
        origin = first_origin + index * horizon
        train = arr[:origin]
        test = arr[origin : origin + horizon]
        splits.append(RollingSplit(origin_index=origin, train=train, test=test))

    return splits
