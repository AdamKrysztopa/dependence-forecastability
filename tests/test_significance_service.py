"""Tests for surrogate significance service lag-range behavior."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.metrics.scorers import default_registry
from forecastability.services import significance_service
from forecastability.services.significance_service import (
    compute_significance_bands_generic,
    compute_significance_bands_transfer_entropy,
)
from forecastability.utils.synthetic import generate_white_noise


def test_generic_significance_rejects_too_few_surrogates_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct generic service calls should enforce the significance surrogate floor."""
    series = generate_white_noise(n=120, seed=1)
    info = default_registry().get("mi")

    def _raise_if_called(*_args: object, **_kwargs: object) -> np.ndarray:
        raise AssertionError("phase_surrogates should not be called")

    monkeypatch.setattr(significance_service, "phase_surrogates", _raise_if_called)

    with pytest.raises(ValueError, match="n_surrogates must be >= 99"):
        compute_significance_bands_generic(
            series,
            n_surrogates=98,
            random_state=42,
            max_lag=3,
            info=info,
            which="raw",
            min_pairs=30,
            n_jobs=1,
        )


def test_transfer_entropy_significance_rejects_too_few_surrogates_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct TE service calls should enforce the significance surrogate floor."""
    series = generate_white_noise(n=120, seed=2)

    def _raise_if_called(*_args: object, **_kwargs: object) -> np.ndarray:
        raise AssertionError("phase_surrogates should not be called")

    monkeypatch.setattr(significance_service, "phase_surrogates", _raise_if_called)

    with pytest.raises(ValueError, match="n_surrogates must be >= 99"):
        compute_significance_bands_transfer_entropy(
            series,
            n_surrogates=98,
            random_state=42,
            max_lag=3,
            min_pairs=30,
            n_jobs=1,
        )


def test_significance_default_matches_explicit_predictive_lag_range() -> None:
    """Default significance behavior should match explicit ``(1, max_lag)``."""
    series = generate_white_noise(n=400, seed=42)
    info = default_registry().get("mi")

    lower_default, upper_default = compute_significance_bands_generic(
        series,
        n_surrogates=99,
        random_state=42,
        max_lag=5,
        info=info,
        which="raw",
        min_pairs=30,
        n_jobs=1,
    )
    lower_explicit, upper_explicit = compute_significance_bands_generic(
        series,
        n_surrogates=99,
        random_state=42,
        max_lag=5,
        info=info,
        which="raw",
        min_pairs=30,
        n_jobs=1,
        lag_range=(1, 5),
    )

    np.testing.assert_allclose(lower_default, lower_explicit)
    np.testing.assert_allclose(upper_default, upper_explicit)


def test_significance_supports_zero_lag_when_requested() -> None:
    """Lag-0 significance should be computed only on explicit zero-lag requests."""
    series = generate_white_noise(n=400, seed=7)
    info = default_registry().get("mi")

    lower_with_zero, upper_with_zero = compute_significance_bands_generic(
        series,
        n_surrogates=99,
        random_state=11,
        max_lag=4,
        info=info,
        which="raw",
        min_pairs=30,
        n_jobs=1,
        lag_range=(0, 4),
    )
    lower_lag0, upper_lag0 = compute_significance_bands_generic(
        series,
        n_surrogates=99,
        random_state=11,
        max_lag=4,
        info=info,
        which="raw",
        min_pairs=30,
        n_jobs=1,
        lag_range=(0, 0),
    )

    assert lower_with_zero.shape == (5,)
    assert upper_with_zero.shape == (5,)
    assert lower_lag0.shape == (1,)
    assert upper_lag0.shape == (1,)
    np.testing.assert_allclose(lower_with_zero[0], lower_lag0[0])
    np.testing.assert_allclose(upper_with_zero[0], upper_lag0[0])


def test_significance_allows_max_lag_zero_default_path() -> None:
    """Default significance path should return empty bands for ``max_lag=0``."""
    series = generate_white_noise(n=400, seed=13)
    info = default_registry().get("mi")

    lower, upper = compute_significance_bands_generic(
        series,
        n_surrogates=99,
        random_state=4,
        max_lag=0,
        info=info,
        which="raw",
        min_pairs=30,
        n_jobs=1,
    )

    assert lower.shape == (0,)
    assert upper.shape == (0,)


def test_significance_accepts_zero_lag_only_range_with_max_lag_zero() -> None:
    """Lag-range pass-through should allow explicit ``(0, 0)`` when ``max_lag=0``."""
    series = generate_white_noise(n=400, seed=14)
    info = default_registry().get("mi")

    lower, upper = compute_significance_bands_generic(
        series,
        n_surrogates=99,
        random_state=5,
        max_lag=0,
        info=info,
        which="raw",
        min_pairs=30,
        n_jobs=1,
        lag_range=(0, 0),
    )

    assert lower.shape == (1,)
    assert upper.shape == (1,)


def test_significance_rejects_invalid_lag_ranges() -> None:
    """Significance wrapper should surface lag-range validation errors."""
    series = generate_white_noise(n=400, seed=15)
    info = default_registry().get("mi")

    for lag_range in [(-1, 1), (2, 1), (0, 3)]:
        try:
            _ = compute_significance_bands_generic(
                series,
                n_surrogates=99,
                random_state=6,
                max_lag=2,
                info=info,
                which="raw",
                min_pairs=30,
                n_jobs=1,
                lag_range=lag_range,
            )
        except ValueError as exc:
            assert "lag_range" in str(exc)
        else:
            raise AssertionError(f"Expected ValueError for lag_range={lag_range}")


def test_significance_partial_curve_supports_lag_range() -> None:
    """Partial significance path should accept lag-range pass-through."""
    series = generate_white_noise(n=420, seed=123)
    info = default_registry().get("mi")

    lower, upper = compute_significance_bands_generic(
        series,
        n_surrogates=99,
        random_state=21,
        max_lag=3,
        info=info,
        which="partial",
        min_pairs=50,
        n_jobs=1,
        lag_range=(0, 3),
    )

    assert lower.shape == (4,)
    assert upper.shape == (4,)


def _raise_phase_surrogates(*_args: object, **_kwargs: object) -> np.ndarray:
    raise AssertionError("phase_surrogates should not be called")


def test_generic_significance_rejects_invalid_which_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    series = generate_white_noise(n=120, seed=1)
    info = default_registry().get("mi")
    monkeypatch.setattr(significance_service, "phase_surrogates", _raise_phase_surrogates)
    with pytest.raises(ValueError, match="which"):
        compute_significance_bands_generic(
            series,
            n_surrogates=99,
            random_state=42,
            max_lag=3,
            info=info,
            which="bogus",
            min_pairs=30,
            n_jobs=1,
        )


def test_generic_significance_rejects_negative_max_lag_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    series = generate_white_noise(n=120, seed=1)
    info = default_registry().get("mi")
    monkeypatch.setattr(significance_service, "phase_surrogates", _raise_phase_surrogates)
    with pytest.raises(ValueError, match="max_lag"):
        compute_significance_bands_generic(
            series,
            n_surrogates=99,
            random_state=42,
            max_lag=-1,
            info=info,
            which="raw",
            min_pairs=30,
            n_jobs=1,
        )


def test_generic_significance_rejects_min_pairs_zero_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    series = generate_white_noise(n=120, seed=1)
    info = default_registry().get("mi")
    monkeypatch.setattr(significance_service, "phase_surrogates", _raise_phase_surrogates)
    with pytest.raises(ValueError, match="min_pairs"):
        compute_significance_bands_generic(
            series,
            n_surrogates=99,
            random_state=42,
            max_lag=3,
            info=info,
            which="raw",
            min_pairs=0,
            n_jobs=1,
        )


def test_generic_significance_rejects_zero_n_jobs_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    series = generate_white_noise(n=120, seed=1)
    info = default_registry().get("mi")
    monkeypatch.setattr(significance_service, "phase_surrogates", _raise_phase_surrogates)
    with pytest.raises(ValueError, match="n_jobs"):
        compute_significance_bands_generic(
            series,
            n_surrogates=99,
            random_state=42,
            max_lag=3,
            info=info,
            which="raw",
            min_pairs=30,
            n_jobs=0,
        )


def test_generic_significance_rejects_exog_shape_mismatch_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    series = generate_white_noise(n=120, seed=1)
    exog = generate_white_noise(n=121, seed=2)
    info = default_registry().get("mi")
    monkeypatch.setattr(significance_service, "phase_surrogates", _raise_phase_surrogates)
    with pytest.raises(ValueError, match="exog"):
        compute_significance_bands_generic(
            series,
            n_surrogates=99,
            random_state=42,
            max_lag=3,
            info=info,
            which="raw",
            exog=exog,
            min_pairs=30,
            n_jobs=1,
        )


def test_te_significance_rejects_zero_max_lag_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    series = generate_white_noise(n=120, seed=1)
    monkeypatch.setattr(significance_service, "phase_surrogates", _raise_phase_surrogates)
    with pytest.raises(ValueError, match="max_lag"):
        compute_significance_bands_transfer_entropy(
            series,
            n_surrogates=99,
            random_state=42,
            max_lag=0,
            min_pairs=30,
            n_jobs=1,
        )


def test_te_significance_rejects_zero_n_jobs_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    series = generate_white_noise(n=120, seed=1)
    monkeypatch.setattr(significance_service, "phase_surrogates", _raise_phase_surrogates)
    with pytest.raises(ValueError, match="n_jobs"):
        compute_significance_bands_transfer_entropy(
            series,
            n_surrogates=99,
            random_state=42,
            max_lag=3,
            min_pairs=30,
            n_jobs=0,
        )


def test_generic_significance_n_jobs_serial_vs_parallel_bit_identical() -> None:
    series = generate_white_noise(n=200, seed=11)
    info = default_registry().get("mi")
    serial = compute_significance_bands_generic(
        series,
        n_surrogates=99,
        random_state=7,
        max_lag=4,
        info=info,
        which="raw",
        min_pairs=30,
        n_jobs=1,
    )
    parallel = compute_significance_bands_generic(
        series,
        n_surrogates=99,
        random_state=7,
        max_lag=4,
        info=info,
        which="raw",
        min_pairs=30,
        n_jobs=2,
    )
    assert np.array_equal(serial[0], parallel[0])
    assert np.array_equal(serial[1], parallel[1])


def test_generic_significance_fixed_seed_regression() -> None:
    """Pinned generic raw/partial bands guarding F05 preallocation/hoist parity."""
    series = generate_white_noise(n=200, seed=11)
    info = default_registry().get("mi")

    raw_lower, raw_upper = compute_significance_bands_generic(
        series,
        n_surrogates=99,
        random_state=7,
        max_lag=4,
        info=info,
        which="raw",
        min_pairs=30,
        n_jobs=1,
    )
    partial_lower, partial_upper = compute_significance_bands_generic(
        series,
        n_surrogates=99,
        random_state=7,
        max_lag=4,
        info=info,
        which="partial",
        min_pairs=30,
        n_jobs=1,
    )

    expected_raw_lower = np.array([0.0, 0.0, 0.0, 0.0])
    expected_raw_upper = np.array(
        [
            0.053734321302349675,
            0.03634542031334253,
            0.05994361852581409,
            0.05704183680198599,
        ]
    )
    expected_partial_lower = np.array([0.0, 0.0, 0.0, 0.0])
    expected_partial_upper = np.array(
        [
            0.053734321302349675,
            0.03808363780743239,
            0.06037951854169674,
            0.048159321685819934,
        ]
    )

    np.testing.assert_allclose(raw_lower, expected_raw_lower, rtol=0, atol=0)
    np.testing.assert_allclose(raw_upper, expected_raw_upper, rtol=0, atol=0)
    np.testing.assert_allclose(partial_lower, expected_partial_lower, rtol=0, atol=0)
    np.testing.assert_allclose(partial_upper, expected_partial_upper, rtol=0, atol=0)
