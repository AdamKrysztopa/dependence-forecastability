"""Regression tests for the ForecastabilityAnalyzer API."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.diagnostics.surrogates import phase_surrogates
from forecastability.pipeline.analyzer import ForecastabilityAnalyzer, ForecastabilityAnalyzerExog
from forecastability.services.transfer_entropy_service import compute_transfer_entropy_curve

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
    """Verify all default scorers are listed, including directional TE."""
    analyzer = ForecastabilityAnalyzer(n_surrogates=99)
    scorers = analyzer.list_scorers()
    names = {s.name for s in scorers}
    assert names == {
        "mi",
        "pearson",
        "spearman",
        "kendall",
        "distance",
        "te",
        "permutation_entropy",
        "spectral_entropy",
        "spectral_predictability",
        "largest_lyapunov_exponent",
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


def _generate_exog_te_pair(
    n: int = 900,
    *,
    seed: int = 12,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a directional exogenous pair with x_{t-1} -> y_t influence."""
    rng = np.random.default_rng(seed)
    source = np.zeros(n, dtype=float)
    target = np.zeros(n, dtype=float)
    for idx in range(1, n):
        source[idx] = 0.8 * source[idx - 1] + rng.normal(scale=0.7)
        target[idx] = 0.6 * target[idx - 1] + 0.7 * source[idx - 1] + rng.normal(scale=0.7)
    return source, target


def _generate_lag2_driver_pair(
    n: int = 1200,
    *,
    seed: int = 31,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a pair where the dominant directional effect occurs at lag 2."""
    rng = np.random.default_rng(seed)
    source = np.zeros(n, dtype=float)
    target = np.zeros(n, dtype=float)
    for idx in range(1, n):
        source[idx] = 0.85 * source[idx - 1] + rng.normal(scale=0.6)
    for idx in range(2, n):
        target[idx] = 0.3 * target[idx - 1] + 1.1 * source[idx - 2] + rng.normal(scale=0.35)
    return source, target


def test_analyzer_te_horizon_semantics_match_direct_curve_multi_lag() -> None:
    """Analyzer TE at lag h must equal direct full-series TE at lag h."""
    source, target = _generate_exog_te_pair(seed=22)
    analyzer = ForecastabilityAnalyzerExog(n_surrogates=99, random_state=19)

    raw = analyzer.compute_raw(target, max_lag=5, method="te", exog=source, min_pairs=50)
    direct = compute_transfer_entropy_curve(
        source,
        target,
        max_lag=5,
        min_pairs=50,
        random_state=19,
    )

    np.testing.assert_allclose(raw, direct, rtol=1e-12, atol=1e-12)


def test_analyzer_te_significance_uses_same_estimand() -> None:
    """TE surrogate bands must be computed from the same TE curve estimand."""
    source, target = _generate_exog_te_pair(n=700, seed=5)
    analyzer = ForecastabilityAnalyzerExog(n_surrogates=99, random_state=13)
    analyzer.compute_raw(target, max_lag=4, method="te", exog=source, min_pairs=50)

    lower, upper = analyzer.compute_significance_generic(
        "raw",
        4,
        method="te",
        exog=source,
        min_pairs=50,
        n_jobs=1,
    )

    surrogates = phase_surrogates(target, n_surrogates=99, random_state=13)
    expected_curves = np.vstack(
        [
            compute_transfer_entropy_curve(
                source,
                surrogates[idx],
                max_lag=4,
                min_pairs=50,
                random_state=13 + idx + 1,
            )
            for idx in range(surrogates.shape[0])
        ]
    )
    expected_lower = np.percentile(expected_curves, 2.5, axis=0)
    expected_upper = np.percentile(expected_curves, 97.5, axis=0)

    np.testing.assert_allclose(lower, expected_lower, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(upper, expected_upper, rtol=1e-12, atol=1e-12)


def test_analyzer_te_regression_guard_for_off_by_one_lag_bug() -> None:
    """Directional lag-2 driver must peak at lag 2 (not lag 1 or lag 3)."""
    source, target = _generate_lag2_driver_pair(seed=17)
    analyzer = ForecastabilityAnalyzerExog(n_surrogates=99, random_state=41)

    raw = analyzer.compute_raw(target, max_lag=5, method="te", exog=source, min_pairs=50)
    direct = compute_transfer_entropy_curve(
        source,
        target,
        max_lag=5,
        min_pairs=50,
        random_state=41,
    )

    peak_lag = int(np.argmax(raw)) + 1
    assert peak_lag == 2
    assert raw[1] > raw[0]
    np.testing.assert_allclose(raw, direct, rtol=1e-12, atol=1e-12)


def test_analyzer_partial_te_path_is_explicitly_blocked() -> None:
    """Partial TE is disabled until a formally valid estimand is implemented."""
    ts = np.sin(np.linspace(0.0, 24.0, 360))
    analyzer = ForecastabilityAnalyzer(n_surrogates=99, random_state=7)
    analyzer.compute_raw(ts, max_lag=6, method="te", min_pairs=50)

    with pytest.raises(ValueError, match="method='te' is not supported for partial curves"):
        analyzer.compute_partial(ts, max_lag=4, method="te")
    with pytest.raises(ValueError, match="method='te' is not supported for partial curves"):
        analyzer.compute_significance_generic("partial", 4, method="te", min_pairs=50)
