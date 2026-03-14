# 17. Rolling-Origin Evaluation

- [x] Follow paper logic exactly:
  - [ ] expanding window
  - [ ] `10` origins by default
  - [ ] AMI computed pre-origin on training-only history
  - [ ] forecast error computed post-origin on held-out future
  - [ ] local models re-fit at each origin
  - [ ] no leakage

```python
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


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
    """Build expanding-window rolling-origin splits.

    Args:
        ts: Full time series.
        n_origins: Number of origins.
        horizon: Forecast horizon.

    Returns:
        list[RollingSplit]: Rolling splits.

    Raises:
        ValueError: If the series is too short.
    """
    arr = np.asarray(ts, dtype=float).reshape(-1)
    required = n_origins * horizon + 20
    if arr.size <= required:
        raise ValueError("Series too short for requested rolling-origin configuration.")

    splits: list[RollingSplit] = []
    first_origin = arr.size - n_origins * horizon

    for i in range(n_origins):
        origin = first_origin + i * horizon
        train = arr[:origin]
        test = arr[origin:origin + horizon]
        splits.append(RollingSplit(origin_index=origin, train=train, test=test))

    return splits
```
