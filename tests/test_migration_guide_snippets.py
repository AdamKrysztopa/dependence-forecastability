"""Tests that exercise the runnable code snippets from docs/migration/v0.4.x_to_v0.5.0.md.

Each test corresponds to a numbered section of the migration guide.
"Before" snippets that use removed names are NOT executed here — they are
commented-out documentation only.  Only "after" snippets that represent valid
v0.5.0 usage are exercised.

Acceptance criterion 10 from the v0.5.0 plan requires this file to exist and
pass.  Do not remove or skip tests without a plan entry.
"""

from __future__ import annotations

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ar1_series(n: int = 300, phi: float = 0.7, seed: int = 42) -> np.ndarray:
    """Return a short AR(1) series for snippet tests."""
    from forecastability import generate_ar1

    return generate_ar1(n_samples=n, phi=phi, random_state=seed)


# ---------------------------------------------------------------------------
# Section 1 — Default AMI estimator changed to KSG-II
# ---------------------------------------------------------------------------


def test_section1_ksg2_default_runs() -> None:
    """compute_ami returns a curve using the new KSG-II default."""
    from forecastability import compute_ami

    series = _ar1_series()
    ami_curve = compute_ami(series, max_lag=10)
    assert ami_curve is not None
    assert hasattr(ami_curve, "__len__") or hasattr(ami_curve, "shape")


def test_section1_ksg1_sklearn_compat_runs() -> None:
    """compute_ami with estimator='ksg1_sklearn' completes without error."""
    from forecastability import compute_ami

    series = _ar1_series()
    ami_curve = compute_ami(series, max_lag=10, estimator="ksg1_sklearn")
    assert ami_curve is not None


# ---------------------------------------------------------------------------
# Section 2 — compute_transfer_entropy removed
# ---------------------------------------------------------------------------


def test_section2_compute_transfer_entropy_raises_import_error() -> None:
    """Importing compute_transfer_entropy from the public API raises ImportError."""
    with pytest.raises((ImportError, AttributeError)):
        from forecastability import compute_transfer_entropy  # noqa: F401


def test_section2_compute_transfer_entropy_ksg_runs() -> None:
    """compute_transfer_entropy_ksg runs on two random series."""
    from forecastability import compute_transfer_entropy_ksg

    rng = np.random.default_rng(42)
    source = rng.standard_normal(300)
    target = rng.standard_normal(300)
    result = compute_transfer_entropy_ksg(source, target, lag=3)
    assert result.status in {
        "computed",
        "blocked_sample_size",
        "blocked_low_cardinality",
        "blocked_constant_input",
    }
    assert result.quality_warning in {"ok", "marginal", "unreliable"}


def test_section2_compute_predictive_information_gain_runs() -> None:
    """compute_predictive_information_gain runs with keyword-only lag."""
    from forecastability import compute_predictive_information_gain

    rng = np.random.default_rng(42)
    source = rng.standard_normal(300)
    target = rng.standard_normal(300)
    result = compute_predictive_information_gain(source, target, lag=3)
    assert result.status in {"computed", "blocked"}


# ---------------------------------------------------------------------------
# Section 3 — Significance correction now defaults to Romano-Wolf
# ---------------------------------------------------------------------------


def test_section3_run_triage_applies_romano_wolf_internally() -> None:
    """run_triage applies Romano-Wolf correction internally; call site is unchanged."""
    from forecastability import TriageRequest, run_triage

    series = _ar1_series(n=200)
    result = run_triage(
        TriageRequest(
            series=series,
            max_lag=10,
            n_surrogates=99,
            random_state=42,
        )
    )
    assert result is not None


def test_section3_significance_correction_service_none_instantiates() -> None:
    """SignificanceCorrectionService(correction='none') instantiates correctly."""
    from forecastability.services.significance_correction_service import (
        SignificanceCorrectionService,
    )

    svc = SignificanceCorrectionService(correction="none", alpha=0.05)
    assert svc is not None


def test_section3_significance_correction_service_romano_wolf_instantiates() -> None:
    """SignificanceCorrectionService(correction='romano_wolf') instantiates correctly."""
    from forecastability.services.significance_correction_service import (
        SignificanceCorrectionService,
    )

    svc = SignificanceCorrectionService(correction="romano_wolf", alpha=0.05)
    assert svc is not None


# ---------------------------------------------------------------------------
# Section 4 — Domain module import paths changed
# ---------------------------------------------------------------------------


def test_section4_stable_facade_import_works() -> None:
    """TriageResult is importable from the stable public facade."""
    from forecastability import TriageResult  # noqa: F401

    assert TriageResult is not None


# ---------------------------------------------------------------------------
# Section 5 — Agent adapter module paths changed
# (Import test only — agent extras may not be installed in the core env)
# ---------------------------------------------------------------------------


def test_section5_old_pydantic_ai_shim_raises() -> None:
    """Importing from the old adapters.pydantic_ai_agent shim raises ImportError."""
    with pytest.raises(ImportError):
        import forecastability.adapters.pydantic_ai_agent  # noqa: F401


# ---------------------------------------------------------------------------
# Section 6 — Public API surface shrunk
# ---------------------------------------------------------------------------


def test_section6_stable_names_importable() -> None:
    """Core stable public names are importable from forecastability."""
    from forecastability import TriageRequest, TriageResult, run_triage  # noqa: F401

    assert run_triage is not None
    assert TriageRequest is not None
    assert TriageResult is not None


# ---------------------------------------------------------------------------
# Section 7 — n_surrogates default raised from 99 to 999
# ---------------------------------------------------------------------------


def test_section7_explicit_99_accepted() -> None:
    """TriageRequest with explicit n_surrogates=99 is accepted (ge=99 floor)."""
    from forecastability import TriageRequest

    series = _ar1_series(n=200)
    req = TriageRequest(series=series, n_surrogates=99, random_state=42)
    assert req.n_surrogates == 99


def test_section7_default_is_999() -> None:
    """TriageRequest() default n_surrogates is 999."""
    from forecastability import TriageRequest

    series = _ar1_series(n=200)
    req = TriageRequest(series=series, random_state=42)
    assert req.n_surrogates == 999


def test_section7_below_floor_raises() -> None:
    """TriageRequest(n_surrogates=98) raises ValidationError."""
    from pydantic import ValidationError

    from forecastability import TriageRequest

    series = _ar1_series(n=200)
    with pytest.raises(ValidationError):
        TriageRequest(series=series, n_surrogates=98)


# ---------------------------------------------------------------------------
# Section 8 — compute_pami_linear_residual emits UserWarning on low cardinality
# ---------------------------------------------------------------------------


def test_section8_low_cardinality_warning() -> None:
    """compute_pami_linear_residual emits UserWarning on low-cardinality input."""
    import warnings

    from forecastability import compute_pami_linear_residual

    # Create a low-cardinality series: only 5 unique values in 300 points
    rng = np.random.default_rng(42)
    integer_series = rng.integers(0, 5, size=300).astype(float)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        compute_pami_linear_residual(integer_series, max_lag=5)

    warning_messages = [str(w.message) for w in caught if issubclass(w.category, UserWarning)]
    assert any(
        "low cardinality" in m.lower() or "cardinality" in m.lower()
        for m in warning_messages
    ), f"Expected low-cardinality UserWarning; got: {warning_messages}"


def test_section8_warning_suppression_works() -> None:
    """Suppressing low-cardinality warning with filterwarnings does not raise."""
    import warnings

    from forecastability import compute_pami_linear_residual

    rng = np.random.default_rng(42)
    integer_series = rng.integers(0, 5, size=300).astype(float)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*low cardinality.*")
        result = compute_pami_linear_residual(integer_series, max_lag=5)

    assert result is not None


# ---------------------------------------------------------------------------
# Section 9 — signal_to_noise renamed to informative_mass_fraction
# ---------------------------------------------------------------------------


def test_section9_informative_mass_fraction_accessible() -> None:
    """informative_mass_fraction is accessible on AmiInformationGeometryResult."""
    from forecastability import compute_ami_information_geometry

    series = _ar1_series(n=300)
    result = compute_ami_information_geometry(series)
    # The new field name must exist
    assert hasattr(result, "informative_mass_fraction")
    # The old field name must not exist (or must raise AttributeError)
    with pytest.raises(AttributeError):
        _ = result.signal_to_noise


# ---------------------------------------------------------------------------
# "What did NOT change" section — compatibility invariants
# ---------------------------------------------------------------------------


def test_compat_ksg1_and_ksg2_both_run_on_same_series() -> None:
    """KSG-I and KSG-II both return curves of the same shape for the same series."""
    from forecastability import compute_ami

    series = _ar1_series(n=300)
    curve_ksg2 = compute_ami(series, max_lag=10)
    curve_ksg1 = compute_ami(series, max_lag=10, estimator="ksg1_sklearn")
    assert len(curve_ksg2) == len(curve_ksg1)


def test_compat_forecast_prep_contract_importable() -> None:
    """ForecastPrepContract and build_forecast_prep_contract are importable."""
    from forecastability import ForecastPrepContract, build_forecast_prep_contract  # noqa: F401

    assert ForecastPrepContract is not None
    assert build_forecast_prep_contract is not None


def test_compat_generate_ar1_deterministic() -> None:
    """generate_ar1 with the same seed produces identical output."""
    from forecastability import generate_ar1

    s1 = generate_ar1(n_samples=100, phi=0.8, random_state=42)
    s2 = generate_ar1(n_samples=100, phi=0.8, random_state=42)
    np.testing.assert_array_equal(s1, s2)
