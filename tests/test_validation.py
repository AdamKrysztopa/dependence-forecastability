"""Validation-layer tests."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.utils.validation import validate_time_series


def test_validate_time_series_passes_valid_array() -> None:
    series = np.array([1.0, 2.0, 3.0, 4.0])
    validated = validate_time_series(series, min_length=4)
    assert validated.shape == (4,)


def test_validate_time_series_rejects_short_series() -> None:
    with pytest.raises(ValueError, match="too short"):
        validate_time_series(np.array([1.0, 2.0]), min_length=3)


def test_validate_time_series_rejects_nan() -> None:
    with pytest.raises(ValueError, match="NaN or inf"):
        validate_time_series(np.array([1.0, np.nan, 2.0]), min_length=3)


def test_validate_time_series_rejects_inf() -> None:
    with pytest.raises(ValueError, match="NaN or inf"):
        validate_time_series(np.array([1.0, np.inf, 2.0]), min_length=3)


def test_validate_time_series_rejects_constant() -> None:
    with pytest.raises(ValueError, match="constant"):
        validate_time_series(np.array([5.0, 5.0, 5.0]), min_length=3)
