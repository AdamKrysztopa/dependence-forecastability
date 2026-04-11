"""Tests that verify every public symbol in forecastability.__all__ is importable
and that key API entry-points are instantiable / callable without heavy computation.
"""

from __future__ import annotations

import dataclasses

import forecastability

# ---------------------------------------------------------------------------
# __all__ completeness
# ---------------------------------------------------------------------------


def test_all_exports_importable() -> None:
    """Every name in __all__ must be importable from the top-level package."""
    for name in forecastability.__all__:
        obj = getattr(forecastability, name, None)
        assert obj is not None, f"forecastability.{name} is None or missing"


# ---------------------------------------------------------------------------
# Analyzer instantiation
# ---------------------------------------------------------------------------


def test_forecastability_analyzer_instantiation() -> None:
    from forecastability import ForecastabilityAnalyzer

    fa = ForecastabilityAnalyzer(n_surrogates=99, random_state=42, method="mi")
    assert fa.n_surrogates == 99
    assert fa.random_state == 42


def test_forecastability_analyzer_exog_instantiation() -> None:
    from forecastability import ForecastabilityAnalyzerExog

    fa = ForecastabilityAnalyzerExog(n_surrogates=99, random_state=42, method="mi")
    assert fa.n_surrogates == 99
    assert fa.random_state == 42


# ---------------------------------------------------------------------------
# AnalyzeResult structure
# ---------------------------------------------------------------------------


def test_analyze_result_is_dataclass() -> None:
    from forecastability import AnalyzeResult

    assert dataclasses.is_dataclass(AnalyzeResult)


def test_analyze_result_fields() -> None:
    from forecastability import AnalyzeResult

    field_names = {f.name for f in dataclasses.fields(AnalyzeResult)}
    required = {"raw", "partial", "sig_raw_lags", "sig_partial_lags", "recommendation", "method"}
    assert required <= field_names, f"Missing AnalyzeResult fields: {required - field_names}"


# ---------------------------------------------------------------------------
# pipeline imports
# ---------------------------------------------------------------------------


def test_run_rolling_origin_evaluation_importable() -> None:
    from forecastability.pipeline import run_rolling_origin_evaluation

    assert callable(run_rolling_origin_evaluation)


def test_run_exogenous_rolling_origin_evaluation_importable() -> None:
    from forecastability.pipeline import run_exogenous_rolling_origin_evaluation

    assert callable(run_exogenous_rolling_origin_evaluation)


# ---------------------------------------------------------------------------
# ScorerRegistry / default_registry
# ---------------------------------------------------------------------------


def test_scorer_registry_importable() -> None:
    from forecastability import ScorerRegistry

    assert ScorerRegistry is not None


def test_default_registry_returns_scorer_registry() -> None:
    from forecastability import ScorerRegistry, default_registry

    registry = default_registry()
    assert isinstance(registry, ScorerRegistry)


# ---------------------------------------------------------------------------
# validate_time_series
# ---------------------------------------------------------------------------


def test_validate_time_series_importable_and_callable() -> None:
    from forecastability import validate_time_series

    assert callable(validate_time_series)
