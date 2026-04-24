"""Tests for deterministic calendar feature generation service."""

from __future__ import annotations

import pandas as pd
import pytest

from forecastability.services import calendar_feature_service
from forecastability.services.calendar_feature_service import generate_calendar_features


def test_generate_calendar_features_emits_default_columns_with_expected_dtypes() -> None:
    """Default calendar features should follow deterministic names and dtypes."""
    index = pd.date_range("2024-01-01", periods=7, freq="D")
    features = generate_calendar_features(index)

    assert features.index.equals(index)
    assert list(features.columns) == [
        "_calendar__dayofweek",
        "_calendar__month",
        "_calendar__quarter",
        "_calendar__is_weekend",
        "_calendar__is_business_day",
    ]
    assert str(features["_calendar__dayofweek"].dtype) == "int8"
    assert str(features["_calendar__month"].dtype) == "int8"
    assert str(features["_calendar__quarter"].dtype) == "int8"
    assert str(features["_calendar__is_weekend"].dtype) == "bool"
    assert str(features["_calendar__is_business_day"].dtype) == "bool"


def test_locale_without_holidays_package_skips_holiday_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Locale input should not force holiday column when optional dependency is absent."""
    monkeypatch.setattr(calendar_feature_service, "_HOLIDAYS_AVAILABLE", False)

    index = pd.date_range("2024-01-01", periods=5, freq="D")
    features = generate_calendar_features(index, locale="US")

    assert "_calendar__is_holiday" not in features.columns


@pytest.mark.skipif(
    not calendar_feature_service._HOLIDAYS_AVAILABLE,
    reason="holidays optional dependency unavailable",
)
def test_locale_with_holidays_package_emits_holiday_column() -> None:
    """Locale with holidays integration should emit boolean holiday indicator."""
    index = pd.date_range("2024-01-01", periods=14, freq="D")
    features = generate_calendar_features(index, locale="US")

    assert "_calendar__is_holiday" in features.columns
    assert str(features["_calendar__is_holiday"].dtype) == "bool"
