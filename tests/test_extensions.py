"""Tests for extension helpers."""

from __future__ import annotations

import numpy as np

import forecastability.extensions as extensions
from forecastability.extensions import (
    TargetBaselineCurves,
    compute_target_baseline_by_horizon,
)


class _Split:
    def __init__(self, train: np.ndarray, test: np.ndarray) -> None:
        self.train = train
        self.test = test


class _AnalyzerStub:
    def __init__(self, n_surrogates: int, random_state: int) -> None:
        assert n_surrogates == 99
        self.random_state = random_state

    def compute_raw(
        self,
        train_target: np.ndarray,
        *,
        max_lag: int,
        method: str,
        min_pairs: int,
        exog: np.ndarray | None = None,
    ) -> np.ndarray:
        del max_lag, method, min_pairs, exog
        return np.full(train_target.size, float(train_target.size))

    def compute_partial(
        self,
        train_target: np.ndarray,
        *,
        max_lag: int,
        method: str,
        min_pairs: int,
        exog: np.ndarray | None = None,
    ) -> np.ndarray:
        del max_lag, method, min_pairs, exog
        return np.full(train_target.size, float(train_target.size) / 10.0)


def test_compute_target_baseline_by_horizon_aggregates_train_windows_only(
    monkeypatch,
) -> None:
    seen_horizons: list[int] = []
    seen_train_sizes: list[int] = []

    def _fake_build_splits(
        target: np.ndarray,
        *,
        n_origins: int,
        horizon: int,
    ) -> list[_Split]:
        del target, n_origins
        seen_horizons.append(horizon)
        train = np.arange(10 + horizon, dtype=float)
        seen_train_sizes.append(train.size)
        return [_Split(train=train, test=np.arange(horizon, dtype=float))]

    monkeypatch.setattr(extensions, "build_expanding_window_splits", _fake_build_splits)
    monkeypatch.setattr(extensions, "ForecastabilityAnalyzerExog", _AnalyzerStub)

    result = compute_target_baseline_by_horizon(
        series_name="demo_target",
        target=np.arange(32, dtype=float),
        horizons=[1, 3],
        n_origins=4,
        random_state=7,
        min_pairs_raw=30,
        min_pairs_partial=50,
        n_surrogates=99,
    )

    assert isinstance(result, TargetBaselineCurves)
    assert result.series_name == "demo_target"
    assert seen_horizons == [1, 3]
    assert seen_train_sizes == [11, 13]
    assert result.ami_by_horizon == {1: 11.0, 3: 13.0}
    assert result.pami_by_horizon == {1: 1.1, 3: 1.3}
