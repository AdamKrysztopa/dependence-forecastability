"""Tests for optional model integrations with graceful fallback."""

from __future__ import annotations

import numpy as np

from forecastability.models import forecast_lightgbm_autoreg, forecast_nbeats


def test_optional_lightgbm_fallback_shape() -> None:
    train = np.sin(np.linspace(0.0, 40.0, 300))
    pred = forecast_lightgbm_autoreg(train, horizon=8, n_lags=24)
    assert pred.shape == (8,)


def test_optional_nbeats_fallback_shape() -> None:
    train = np.sin(np.linspace(0.0, 40.0, 300))
    pred = forecast_nbeats(train, horizon=6, input_size=24)
    assert pred.shape == (6,)
