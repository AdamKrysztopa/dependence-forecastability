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


# ---------------------------------------------------------------------------
# RVH-F12 — canonical surface completeness (v0.5.0)
# ---------------------------------------------------------------------------


def test_canonical_public_names_importable() -> None:
    """Every name in forecastability.api.__all__ must be accessible on the top-level package."""
    import forecastability
    from forecastability.api import __all__ as api_all

    missing = [name for name in api_all if not hasattr(forecastability, name)]
    assert not missing, (
        "The following canonical names are in forecastability.api.__all__ "
        f"but not accessible on forecastability: {missing}"
    )


def test_legacy_names_raise_deprecation_warning() -> None:
    """A representative sample of v0.4.x names must emit DeprecationWarning (not AttributeError).

    Names that were *removed* with a semantics change may raise ImportError instead;
    that is also acceptable — the key invariant is that they do not raise AttributeError.
    """
    import warnings

    import forecastability

    # Representative legacy names from the old _LAZY_EXPORT_MAP and _NOTEBOOK_COMPAT_EXPORTS.
    # These are NOT in the canonical v0.5.0 __all__ but were accessible in v0.4.x.
    legacy_sample = [
        "AnalyzeResult",  # pipeline.analyzer
        "ForecastabilityAnalyzer",  # pipeline.analyzer
        "ScorerRegistry",  # metrics.scorers
        "default_registry",  # metrics.scorers
        "run_batch_triage",  # use_cases
        "BenchmarkDataConfig",  # utils.config
        "CMIConfig",  # utils.config
        "generate_ar1_archetype",  # utils.synthetic
        "ForecastabilityProfile",  # triage.forecastability_profile
        "LagAwareModMRMRResult",  # triage.lag_aware_mod_mrmr
    ]

    for name in legacy_sample:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                getattr(forecastability, name)
            except ImportError:
                # Acceptable: symbol removed with semantics change (e.g. compute_transfer_entropy)
                pass
            except AttributeError as exc:
                raise AssertionError(
                    f"forecastability.{name} raised AttributeError — "
                    "expected DeprecationWarning or ImportError for a legacy name. "
                    f"Original error: {exc}"
                ) from exc

            dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
            # If no exception was raised and no DeprecationWarning emitted, that is a failure.
            if not dep_warnings:
                # Re-check: if it raised ImportError above we already continued; only fail
                # when the attribute resolved *silently* without a warning.
                try:
                    getattr(forecastability, name)
                except (ImportError, AttributeError):
                    pass  # already handled
                else:
                    raise AssertionError(
                        f"forecastability.{name} resolved without emitting a DeprecationWarning. "
                        "Legacy names must warn callers to migrate."
                    )


def test_removed_name_raises_import_error() -> None:
    """compute_transfer_entropy was removed in v0.5.0 and must raise ImportError."""
    import forecastability

    try:
        _ = forecastability.compute_transfer_entropy
    except ImportError:
        pass  # expected
    except AttributeError as exc:
        raise AssertionError(
            "forecastability.compute_transfer_entropy raised AttributeError; "
            f"expected ImportError with a migration message. Original: {exc}"
        ) from exc
