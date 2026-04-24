"""Deterministic calendar feature generation for forecast-prep contracts."""

from __future__ import annotations

from collections.abc import Mapping
from importlib import import_module
from types import ModuleType
from typing import Protocol, cast

import pandas as pd


class _HolidaysModuleProtocol(Protocol):
    """Protocol for the optional holidays module methods used here."""

    def country_holidays(self, country: str) -> object:
        """Return mapping-like holiday container for a country code."""


try:  # pragma: no cover - exercised through behavior flags in tests.
    _HOLIDAYS_MODULE: ModuleType | None = import_module("holidays")

    _HOLIDAYS_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - depends on optional extra installation.
    _HOLIDAYS_MODULE = None
    _HOLIDAYS_AVAILABLE = False


def _datetime_series(datetime_index: pd.DatetimeIndex) -> pd.Series:
    """Return aligned datetime values as a pandas series."""
    return pd.Series(datetime_index, index=datetime_index)


def _normalized_dates(datetime_index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Return normalized dates preserving positional alignment."""
    values = _datetime_series(datetime_index).dt.date.to_list()
    return pd.DatetimeIndex(pd.to_datetime(values))


def _business_day_mask(*, datetime_index: pd.DatetimeIndex) -> pd.Series:
    """Return business-day mask derived from pandas business-date ranges."""
    normalized = _normalized_dates(datetime_index)
    business_dates = pd.bdate_range(normalized.min(), normalized.max())
    return pd.Series(normalized.isin(business_dates), index=datetime_index, dtype="bool")


def _holiday_mask(*, datetime_index: pd.DatetimeIndex, locale: str) -> pd.Series:
    """Return holiday mask for a locale using the optional holidays package."""
    if _HOLIDAYS_MODULE is None:
        raise RuntimeError("holidays package is unavailable")
    holidays_module = cast(_HolidaysModuleProtocol, _HOLIDAYS_MODULE)
    calendar = cast(Mapping[object, object], holidays_module.country_holidays(locale))
    normalized = _normalized_dates(datetime_index)
    values = [timestamp.date() in calendar for timestamp in normalized]
    return pd.Series(values, index=datetime_index, dtype="bool")


def generate_calendar_features(
    datetime_index: pd.DatetimeIndex,
    *,
    locale: str | None = None,
) -> pd.DataFrame:
    """Generate deterministic calendar features per plan v0.3.4 section 2.6.

    Always emits:
        _calendar__dayofweek (int8, 0=Monday)
        _calendar__month (int8, 1-12)
        _calendar__quarter (int8, 1-4)
        _calendar__is_weekend (bool)
        _calendar__is_business_day (bool)

    When ``locale`` is set and the optional ``holidays`` package is available,
    emits:
        _calendar__is_holiday (bool)

    Args:
        datetime_index: Aligned pandas DatetimeIndex.
        locale: Optional ISO country code (for example ``"US"``).

    Returns:
        DataFrame with deterministic column order and dtypes.
    """
    if not isinstance(datetime_index, pd.DatetimeIndex):
        raise ValueError("datetime_index must be a pandas.DatetimeIndex")
    if datetime_index.empty:
        raise ValueError("datetime_index must be non-empty")

    datetime_series = _datetime_series(datetime_index)
    features = pd.DataFrame(index=datetime_index)
    features["_calendar__dayofweek"] = pd.Series(
        datetime_series.dt.dayofweek.astype("int8"),
        index=datetime_index,
    )
    features["_calendar__month"] = pd.Series(
        datetime_series.dt.month.astype("int8"),
        index=datetime_index,
    )
    features["_calendar__quarter"] = pd.Series(
        datetime_series.dt.quarter.astype("int8"),
        index=datetime_index,
    )

    weekend = datetime_series.dt.dayofweek.isin([5, 6])
    features["_calendar__is_weekend"] = pd.Series(weekend, index=datetime_index, dtype="bool")
    features["_calendar__is_business_day"] = _business_day_mask(datetime_index=datetime_index)

    if locale is not None and locale.strip() and _HOLIDAYS_AVAILABLE:
        features["_calendar__is_holiday"] = _holiday_mask(
            datetime_index=datetime_index,
            locale=locale,
        )

    return features


__all__ = ["_HOLIDAYS_AVAILABLE", "generate_calendar_features"]
