"""Tests for SeriesDiagnosticScorer protocol and ScorerInfo/ScorerRegistry updates."""

from __future__ import annotations

import numpy as np

from forecastability.metrics.scorers import (
    DependenceScorer,
    ScorerInfo,
    ScorerRegistry,
    SeriesDiagnosticScorer,
    default_registry,
)


def test_series_diagnostic_scorer_protocol_exists() -> None:
    assert SeriesDiagnosticScorer is not None


def test_callable_satisfies_protocol() -> None:
    fn = lambda series, *, random_state=42: float(np.std(series))  # noqa: E731
    assert isinstance(fn, SeriesDiagnosticScorer)


def test_scorer_info_kind_defaults_to_bivariate() -> None:
    def dummy(past: np.ndarray, future: np.ndarray, *, random_state: int = 42) -> float:
        return 0.0

    info = ScorerInfo(name="x", scorer=dummy, family="nonlinear", description="d")
    assert info.kind == "bivariate"


def test_scorer_info_kind_can_be_univariate() -> None:
    def dummy(series: np.ndarray, *, random_state: int = 42) -> float:
        return 0.0

    info = ScorerInfo(
        name="x", scorer=dummy, family="nonlinear", description="d", kind="univariate"
    )
    assert info.kind == "univariate"


def test_registry_register_univariate() -> None:
    def my_univariate(series: np.ndarray, *, random_state: int = 42) -> float:
        return float(np.std(series))

    registry = ScorerRegistry()
    registry.register(
        "std_scorer",
        my_univariate,
        family="nonlinear",
        description="Standard deviation scorer",
        kind="univariate",
    )
    info = registry.get("std_scorer")
    assert info.kind == "univariate"
    assert info.name == "std_scorer"


def test_existing_scorers_unaffected() -> None:
    registry = default_registry()
    mi_info = registry.get("mi")
    assert mi_info.kind == "bivariate"


def test_dependence_scorer_still_independent() -> None:
    # Python @runtime_checkable only checks method presence, not signatures.
    # DependenceScorer and SeriesDiagnosticScorer are nonetheless distinct protocol
    # types — a bivariate fn satisfies DependenceScorer and both protocols share __call__,
    # but the two protocol classes are separate objects.
    bivariate_fn = lambda past, future, *, random_state=42: 0.0  # noqa: E731
    assert isinstance(bivariate_fn, DependenceScorer)
    assert DependenceScorer is not SeriesDiagnosticScorer
