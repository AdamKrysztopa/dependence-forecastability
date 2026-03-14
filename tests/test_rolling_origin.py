"""Rolling-origin split tests."""

from __future__ import annotations

import numpy as np

from forecastability.rolling_origin import build_expanding_window_splits


def test_build_expanding_window_splits_properties() -> None:
    ts = np.linspace(0.0, 1.0, 200)
    horizon = 5
    splits = build_expanding_window_splits(ts, n_origins=10, horizon=horizon)

    assert len(splits) == 10
    for split in splits:
        assert split.train.size > 0
        assert split.test.size == horizon
        assert split.origin_index == split.train.size
        assert split.origin_index + horizon <= ts.size


def test_train_strictly_precedes_test_and_no_leakage() -> None:
    ts = np.arange(240, dtype=float)
    splits = build_expanding_window_splits(ts, n_origins=10, horizon=6)

    for split in splits:
        assert split.train[-1] < split.test[0]
        assert split.train.max() < split.test.min()
