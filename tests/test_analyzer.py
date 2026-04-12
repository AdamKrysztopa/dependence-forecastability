"""Regression tests for the ForecastabilityAnalyzer API."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.analyzer import ForecastabilityAnalyzer, ForecastabilityAnalyzerExog

# ------------------------------------------------------------------
# Legacy backward-compat tests (updated field names)
# ------------------------------------------------------------------


def test_forecastability_analyzer_runs_end_to_end() -> None:
    ts = np.sin(np.linspace(0.0, 24.0, 320))
    analyzer = ForecastabilityAnalyzer(n_surrogates=99, random_state=7)

    result = analyzer.analyze(ts, max_lag=16)

    assert result.raw.shape == (16,)
    assert result.partial.shape == (8,)
    assert result.sig_raw_lags.ndim == 1
    assert result.sig_partial_lags.ndim == 1
    assert result.method == "mi"


def test_forecastability_analyzer_rejects_low_surrogate_count() -> None:
    with pytest.raises(ValueError, match=">= 99"):
        ForecastabilityAnalyzer(n_surrogates=98)


# ------------------------------------------------------------------
# New scorer-based tests
# ------------------------------------------------------------------


def test_analyzer_mi_method() -> None:
    """Explicit method='mi' uses the scorer registry and produces valid output."""
    ts = np.sin(np.linspace(0.0, 24.0, 320))
    analyzer = ForecastabilityAnalyzer(n_surrogates=99, random_state=7)
    result = analyzer.analyze(ts, max_lag=16, method="mi")

    assert result.raw.shape == (16,)
    assert result.partial.shape == (8,)
    assert result.method == "mi"
    assert np.all(result.raw >= 0.0)


def test_analyzer_pearson_method() -> None:
    """method='pearson' runs end-to-end and returns values in [0, 1]."""
    ts = np.sin(np.linspace(0.0, 24.0, 320))
    analyzer = ForecastabilityAnalyzer(n_surrogates=99, random_state=7)
    result = analyzer.analyze(ts, max_lag=16, method="pearson")

    assert result.raw.shape == (16,)
    assert result.partial.shape == (8,)
    assert result.method == "pearson"
    assert np.all(result.raw >= 0.0)
    assert np.all(result.raw <= 1.0 + 1e-9)


def test_analyzer_custom_scorer_registration() -> None:
    """Register a custom scorer and use it in analyze()."""
    analyzer = ForecastabilityAnalyzer(n_surrogates=99, random_state=7)

    def constant_scorer(past: np.ndarray, future: np.ndarray, *, random_state: int = 42) -> float:
        del past, future, random_state
        return 0.5

    analyzer.register_scorer(
        "constant",
        constant_scorer,
        family="linear",
        description="Always returns 0.5",
    )

    ts = np.sin(np.linspace(0.0, 24.0, 320))
    result = analyzer.analyze(ts, max_lag=16, method="constant")
    assert result.method == "constant"
    assert np.allclose(result.raw, 0.5)


def test_analyzer_list_scorers() -> None:
    """Verify all 7 default scorers are listed (5 bivariate + 2 univariate)."""
    analyzer = ForecastabilityAnalyzer(n_surrogates=99)
    scorers = analyzer.list_scorers()
    names = {s.name for s in scorers}
    assert names == {
        "mi", "pearson", "spearman", "kendall", "distance",
        "permutation_entropy", "spectral_entropy",
    }


def test_analyzer_unknown_method_raises() -> None:
    """Verify KeyError for an unknown method name."""
    ts = np.sin(np.linspace(0.0, 24.0, 320))
    analyzer = ForecastabilityAnalyzer(n_surrogates=99, random_state=7)
    with pytest.raises(KeyError, match="no_such_scorer"):
        analyzer.analyze(ts, max_lag=16, method="no_such_scorer")


def test_exog_analyzer_cross_mode_runs_end_to_end() -> None:
    ts = np.sin(np.linspace(0.0, 20.0, 320))
    exog = np.cos(np.linspace(0.0, 20.0, 320))
    analyzer = ForecastabilityAnalyzerExog(n_surrogates=99, random_state=7)

    result = analyzer.analyze(ts, max_lag=12, method="pearson", exog=exog)

    assert result.raw.shape == (12,)
    assert result.partial.shape == (6,)
    assert result.method == "pearson"
    assert "exogenous" in result.recommendation.lower()


def test_exog_analyzer_requires_matching_length() -> None:
    ts = np.sin(np.linspace(0.0, 24.0, 320))
    exog = np.cos(np.linspace(0.0, 24.0, 321))
    analyzer = ForecastabilityAnalyzerExog(n_surrogates=99, random_state=7)

    with pytest.raises(ValueError, match="must exactly match target length"):
        analyzer.compute_raw(ts, max_lag=16, method="mi", exog=exog)


def test_exog_analyzer_legacy_methods_reject_exog() -> None:
    ts = np.sin(np.linspace(0.0, 24.0, 320))
    exog = np.cos(np.linspace(0.0, 24.0, 320))
    analyzer = ForecastabilityAnalyzerExog(n_surrogates=99, random_state=7)

    with pytest.raises(ValueError, match="does not support exogenous variables"):
        analyzer.compute_ami(ts, max_lag=8, exog=exog)
    with pytest.raises(ValueError, match="does not support exogenous variables"):
        analyzer.compute_pami(ts, max_lag=8, exog=exog)
    with pytest.raises(ValueError, match="does not support exogenous variables"):
        analyzer.compute_significance("ami", max_lag=8, exog=exog)
