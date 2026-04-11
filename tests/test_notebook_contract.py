"""Tests that verify the notebook-facing import surface is intact.

These tests mirror the exact import patterns used in
``notebooks/01_canonical_forecastability.ipynb`` and
``notebooks/02_exogenous_analysis.ipynb``.  They must pass without
executing any heavy computation.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Top-level package imports used directly in notebooks
# ---------------------------------------------------------------------------


def test_import_forecastability_analyzer() -> None:
    from forecastability import ForecastabilityAnalyzer  # noqa: F401

    assert ForecastabilityAnalyzer is not None


def test_import_forecastability_analyzer_exog() -> None:
    from forecastability import ForecastabilityAnalyzerExog  # noqa: F401

    assert ForecastabilityAnalyzerExog is not None


def test_import_generate_ar1_generate_white_noise() -> None:
    from forecastability import generate_ar1, generate_white_noise  # noqa: F401

    assert callable(generate_ar1)
    assert callable(generate_white_noise)


def test_import_canonical_example_result() -> None:
    from forecastability import CanonicalExampleResult  # noqa: F401

    assert CanonicalExampleResult is not None


def test_import_series_evaluation_result() -> None:
    from forecastability import SeriesEvaluationResult  # noqa: F401

    assert SeriesEvaluationResult is not None


# ---------------------------------------------------------------------------
# pipeline module
# ---------------------------------------------------------------------------


def test_import_run_canonical_example() -> None:
    from forecastability.pipeline import run_canonical_example  # noqa: F401

    assert callable(run_canonical_example)


def test_import_run_rolling_origin_evaluation() -> None:
    from forecastability.pipeline import run_rolling_origin_evaluation  # noqa: F401

    assert callable(run_rolling_origin_evaluation)


def test_import_run_exogenous_rolling_origin_evaluation() -> None:
    from forecastability.pipeline import run_exogenous_rolling_origin_evaluation  # noqa: F401

    assert callable(run_exogenous_rolling_origin_evaluation)


# ---------------------------------------------------------------------------
# config module
# ---------------------------------------------------------------------------


def test_import_metric_config() -> None:
    from forecastability.config import MetricConfig  # noqa: F401

    assert MetricConfig is not None


def test_import_rolling_origin_config() -> None:
    from forecastability.config import RollingOriginConfig  # noqa: F401

    assert RollingOriginConfig is not None


# ---------------------------------------------------------------------------
# datasets module
# ---------------------------------------------------------------------------


def test_import_generate_ar1_from_datasets() -> None:
    from forecastability.datasets import generate_ar1  # noqa: F401

    assert callable(generate_ar1)
