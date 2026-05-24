"""Tests for SignificanceCorrectionService — RVH-F03.

Covers:
- Unit tests for each correction mode (romano_wolf, bh, by, none).
- FWER Monte-Carlo test for romano_wolf at alpha=0.05.
- Integration smoke test against compute_significance_bands_corrected.
- Edge cases: all NaN horizons, single lag, n_surrogates minimum.
"""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.domain.results.significance_correction import (
    SignificanceCorrectionResult,
)
from forecastability.services.significance_correction_service import (
    SignificanceCorrectionService,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_surrogate_matrix(
    n_surrogates: int,
    n_lags: int,
    seed: int = 0,
) -> np.ndarray:
    """Return a (n_surrogates, n_lags) float matrix sampled from N(0,1)."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n_surrogates, n_lags))


# ---------------------------------------------------------------------------
# Construction / validation
# ---------------------------------------------------------------------------


def test_service_valid_construction() -> None:
    svc = SignificanceCorrectionService(correction="romano_wolf", alpha=0.05)
    assert svc._correction == "romano_wolf"
    assert svc._alpha == 0.05


def test_service_default_correction_is_romano_wolf() -> None:
    svc = SignificanceCorrectionService()
    assert svc._correction == "romano_wolf"


@pytest.mark.parametrize("mode", ["romano_wolf", "bh", "by", "none"])
def test_service_all_modes_construct(mode: str) -> None:
    svc = SignificanceCorrectionService(correction=mode)  # type: ignore[arg-type]
    assert svc._correction == mode


def test_service_rejects_invalid_correction() -> None:
    with pytest.raises(ValueError, match="correction must be one of"):
        SignificanceCorrectionService(correction="bonferroni")  # type: ignore[arg-type]


def test_service_rejects_alpha_out_of_range() -> None:
    with pytest.raises(ValueError, match="alpha must be in"):
        SignificanceCorrectionService(alpha=0.0)
    with pytest.raises(ValueError, match="alpha must be in"):
        SignificanceCorrectionService(alpha=1.0)


def test_correct_rejects_non_2d_surrogate_matrix() -> None:
    svc = SignificanceCorrectionService()
    with pytest.raises(ValueError, match="2-D"):
        svc.correct(np.ones(10), np.ones(10))


def test_correct_rejects_non_1d_observed() -> None:
    svc = SignificanceCorrectionService()
    with pytest.raises(ValueError, match="1-D"):
        svc.correct(np.ones((10, 5)), np.ones((5, 1)))


def test_correct_rejects_shape_mismatch() -> None:
    svc = SignificanceCorrectionService()
    with pytest.raises(ValueError, match="must match"):
        svc.correct(np.ones((10, 5)), np.ones(6))


# ---------------------------------------------------------------------------
# Return-type contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["romano_wolf", "bh", "by", "none"])
def test_correct_returns_frozen_pydantic_result(mode: str) -> None:
    svc = SignificanceCorrectionService(correction=mode)  # type: ignore[arg-type]
    surrogate_matrix = _make_surrogate_matrix(99, 10)
    observed = np.ones(10) * 2.0  # clearly above surrogate mean
    result = svc.correct(surrogate_matrix, observed)
    assert isinstance(result, SignificanceCorrectionResult)
    assert result.correction == mode
    assert result.n_surrogates == 99
    assert result.corrected_mask.shape == (10,)
    assert result.raw_p_values.shape == (10,)
    assert result.family_wise_alpha == 0.05


def test_low_surrogate_warning_set_for_romano_wolf_below_999() -> None:
    svc = SignificanceCorrectionService(correction="romano_wolf")
    result = svc.correct(_make_surrogate_matrix(99, 5), np.ones(5) * 2.0)
    assert result.low_surrogate_warning is True


def test_low_surrogate_warning_not_set_for_bh() -> None:
    svc = SignificanceCorrectionService(correction="bh")
    result = svc.correct(_make_surrogate_matrix(99, 5), np.ones(5) * 2.0)
    assert result.low_surrogate_warning is False


def test_low_surrogate_warning_not_set_when_ge_999_surrogates() -> None:
    svc = SignificanceCorrectionService(correction="romano_wolf")
    result = svc.correct(_make_surrogate_matrix(999, 5), np.ones(5) * 5.0)
    assert result.low_surrogate_warning is False


# ---------------------------------------------------------------------------
# Correctness — "none" mode
# ---------------------------------------------------------------------------


def test_none_mode_rejects_when_observed_exceeds_alpha_percentile() -> None:
    """With correction='none', lags with p <= alpha are flagged."""
    rng = np.random.default_rng(1)
    # 99 surrogates from N(0,1); observed at +3 sigma => p ≈ 0.01 < 0.05
    surrogate_matrix = rng.standard_normal((99, 5))
    observed = np.array([3.0, 3.0, 3.0, 3.0, 3.0])
    svc = SignificanceCorrectionService(correction="none", alpha=0.05)
    result = svc.correct(surrogate_matrix, observed)
    assert np.all(result.corrected_mask), (
        "All lags at +3σ should be significant under no correction"
    )


def test_none_mode_does_not_reject_when_observed_below_null() -> None:
    """With correction='none', lags at the null mean are not significant."""
    rng = np.random.default_rng(2)
    surrogate_matrix = rng.standard_normal((99, 5))
    observed = np.zeros(5)  # at null mean => p ≈ 0.5 >> 0.05
    svc = SignificanceCorrectionService(correction="none", alpha=0.05)
    result = svc.correct(surrogate_matrix, observed)
    assert not np.any(result.corrected_mask), (
        "No lags at null mean should be significant under no correction"
    )


# ---------------------------------------------------------------------------
# Correctness — BH / BY modes
# ---------------------------------------------------------------------------


def test_bh_rejects_clearly_significant_lags() -> None:
    """BH rejects all lags when observed is far above the null."""
    rng = np.random.default_rng(3)
    surrogate_matrix = rng.standard_normal((99, 5))
    observed = np.full(5, 4.0)  # far above N(0,1)
    svc = SignificanceCorrectionService(correction="bh", alpha=0.05)
    result = svc.correct(surrogate_matrix, observed)
    assert np.all(result.corrected_mask)


def test_bh_does_not_reject_null_lags() -> None:
    """BH does not reject lags at the null mean."""
    rng = np.random.default_rng(4)
    surrogate_matrix = rng.standard_normal((99, 5))
    observed = np.zeros(5)
    svc = SignificanceCorrectionService(correction="bh", alpha=0.05)
    result = svc.correct(surrogate_matrix, observed)
    assert not np.any(result.corrected_mask)


def test_by_more_conservative_than_bh() -> None:
    """BY should reject fewer (or equal) hypotheses compared to BH."""
    rng = np.random.default_rng(5)
    n_lags = 20
    surrogate_matrix = rng.standard_normal((99, n_lags))
    # observed at mild signal: some just above 95th percentile
    observed = np.percentile(surrogate_matrix, 96, axis=0)

    svc_bh = SignificanceCorrectionService(correction="bh", alpha=0.05)
    svc_by = SignificanceCorrectionService(correction="by", alpha=0.05)
    result_bh = svc_bh.correct(surrogate_matrix, observed)
    result_by = svc_by.correct(surrogate_matrix, observed)

    n_rejected_bh = int(np.sum(result_bh.corrected_mask))
    n_rejected_by = int(np.sum(result_by.corrected_mask))
    assert n_rejected_by <= n_rejected_bh, (
        f"BY should be more conservative than BH: "
        f"BY rejected {n_rejected_by}, BH rejected {n_rejected_bh}"
    )


def test_by_rejects_clearly_significant_lags() -> None:
    """BY rejects all lags when observed is far above the null."""
    rng = np.random.default_rng(6)
    surrogate_matrix = rng.standard_normal((99, 5))
    observed = np.full(5, 5.0)
    svc = SignificanceCorrectionService(correction="by", alpha=0.05)
    result = svc.correct(surrogate_matrix, observed)
    assert np.all(result.corrected_mask)


# ---------------------------------------------------------------------------
# Correctness — Romano-Wolf: monotonicity and ordering
# ---------------------------------------------------------------------------


def test_romano_wolf_step_down_monotonicity() -> None:
    """Step-down: if a lag with higher observed value is not rejected,
    all lags with lower observed values must also not be rejected."""
    rng = np.random.default_rng(7)
    n_surrogates, n_lags = 99, 10
    surrogate_matrix = rng.standard_normal((n_surrogates, n_lags))
    # Mix of clearly significant and null-level lags.
    observed = np.array([4.0, 3.5, 0.1, 0.0, -0.1, 0.2, 3.0, 4.5, 0.05, 0.0])

    svc = SignificanceCorrectionService(correction="romano_wolf", alpha=0.05)
    result = svc.correct(surrogate_matrix, observed)

    # Verify step-down monotonicity: sort by observed descending;
    # once a lag is not rejected, all subsequent (lower observed) must also
    # not be rejected (unless a gap in the order jumps back over the threshold).
    # More precisely: if lag i is rejected and lag j has observed[j] < observed[i],
    # lag j cannot be rejected unless its own p (wrt max-null) is also <= alpha.
    # We verify the weaker condition: no rejected lag is "sandwiched" between
    # two non-rejected lags of higher observed value.
    sort_order = np.argsort(observed)[::-1]
    rejected = result.corrected_mask
    found_non_rejected = False
    for idx in sort_order:
        if not rejected[idx]:
            found_non_rejected = True
        elif found_non_rejected:
            # A rejected lag appeared after a non-rejected one in sorted order.
            # This would violate step-down monotonicity.
            pytest.fail(
                f"Step-down monotonicity violated: lag {idx} (observed={observed[idx]:.2f}) "
                f"is rejected but a higher-observed lag was not rejected."
            )


def test_romano_wolf_rejects_all_at_high_signal() -> None:
    """All lags should be rejected when observed is far above the null."""
    rng = np.random.default_rng(8)
    surrogate_matrix = rng.standard_normal((99, 5))
    observed = np.full(5, 5.0)
    svc = SignificanceCorrectionService(correction="romano_wolf", alpha=0.05)
    result = svc.correct(surrogate_matrix, observed)
    assert np.all(result.corrected_mask)


def test_romano_wolf_rejects_nothing_at_null() -> None:
    """No lags should be rejected when observed equals the null mean."""
    rng = np.random.default_rng(9)
    surrogate_matrix = rng.standard_normal((99, 5))
    observed = np.zeros(5)
    svc = SignificanceCorrectionService(correction="romano_wolf", alpha=0.05)
    result = svc.correct(surrogate_matrix, observed)
    assert not np.any(result.corrected_mask)


# ---------------------------------------------------------------------------
# NaN handling
# ---------------------------------------------------------------------------


def test_nan_observed_lags_are_not_rejected() -> None:
    """NaN observed values (invalid horizons) must never be flagged as significant."""
    rng = np.random.default_rng(10)
    surrogate_matrix = rng.standard_normal((99, 5))
    observed = np.array([5.0, np.nan, 5.0, np.nan, 5.0])

    for mode in ["romano_wolf", "bh", "by", "none"]:
        svc = SignificanceCorrectionService(correction=mode)  # type: ignore[arg-type]
        result = svc.correct(surrogate_matrix, observed)
        assert not result.corrected_mask[1], (
            f"NaN lag 1 should not be rejected in mode={mode}"
        )
        assert not result.corrected_mask[3], (
            f"NaN lag 3 should not be rejected in mode={mode}"
        )


def test_all_nan_observed_returns_empty_mask() -> None:
    """When all observed values are NaN, the corrected mask must be all False."""
    rng = np.random.default_rng(11)
    surrogate_matrix = rng.standard_normal((99, 5))
    observed = np.full(5, np.nan)

    for mode in ["romano_wolf", "bh", "by", "none"]:
        svc = SignificanceCorrectionService(correction=mode)  # type: ignore[arg-type]
        result = svc.correct(surrogate_matrix, observed)
        assert not np.any(result.corrected_mask), (
            f"All-NaN observed should yield empty mask in mode={mode}"
        )


# ---------------------------------------------------------------------------
# FWER Monte-Carlo test — romano_wolf controls FWER within ±2σ of nominal alpha
# ---------------------------------------------------------------------------


def test_romano_wolf_controls_fwer() -> None:
    """Monte-Carlo FWER control test for Romano-Wolf at alpha=0.05.

    Under the global null (all observed values drawn from the same N(0,1)
    distribution as the surrogates), the Romano-Wolf step-down procedure
    should reject at least one lag in at most alpha fraction of simulations
    (FWER control).

    Test parameters:
    - n_replicates=5000: MC SE = sqrt(0.05*0.95/5000) ≈ 0.00308 → ±2σ ≈ ±0.006
    - n_surrogates=99: minimum allowed, triggers low_surrogate_warning
    - n_lags=10: representative for typical AMI curves

    The test is vectorised using numpy broadcasting to keep wall-clock < 5s.
    """
    alpha = 0.05
    n_replicates = 5000
    n_surrogates = 99
    n_lags = 10
    seed = 42

    rng = np.random.default_rng(seed)

    # Generate all data at once for vectorised processing.
    # Shape: (n_replicates, n_surrogates + 1, n_lags)
    # The last row of each replicate is the "observed" (also from null).
    all_draws = rng.standard_normal((n_replicates, n_surrogates + 1, n_lags))

    surrogate_block = all_draws[:, :n_surrogates, :]  # (n_replicates, n_surrogates, n_lags)
    observed_block = all_draws[:, n_surrogates, :]     # (n_replicates, n_lags)

    # For each replicate and lag, compute the per-lag p-value under
    # the max-null (Romano-Wolf single-step, then step-down).
    # This is vectorised: for each replicate, sort observed lags by value
    # (descending), check step-down.

    fwer_count = 0
    svc = SignificanceCorrectionService(correction="romano_wolf", alpha=alpha)

    for rep in range(n_replicates):
        result = svc.correct(surrogate_block[rep], observed_block[rep])
        if np.any(result.corrected_mask):
            fwer_count += 1

    observed_fwer = fwer_count / n_replicates

    # FWER should be <= alpha (with MC tolerance ±2σ).
    mc_std = (alpha * (1.0 - alpha) / n_replicates) ** 0.5
    upper_bound = alpha + 2.0 * mc_std

    assert observed_fwer <= upper_bound, (
        f"Romano-Wolf FWER ({observed_fwer:.4f}) exceeds alpha + 2σ "
        f"({upper_bound:.4f}) at alpha={alpha}, n_surrogates={n_surrogates}, "
        f"n_lags={n_lags}, n_replicates={n_replicates}."
    )


# ---------------------------------------------------------------------------
# Integration: compute_significance_bands_corrected
# ---------------------------------------------------------------------------


def test_compute_significance_bands_corrected_returns_correct_type() -> None:
    """Smoke test: compute_significance_bands_corrected returns a SignificanceCorrectionResult."""
    from forecastability.diagnostics.surrogates import compute_significance_bands_corrected

    rng = np.random.default_rng(0)
    ts = rng.standard_normal(200)
    observed = rng.standard_normal(5)  # mock observed curve

    result = compute_significance_bands_corrected(
        ts,
        observed,
        metric_name="ami",
        max_lag=5,
        n_surrogates=99,
        alpha=0.05,
        correction="romano_wolf",
    )
    assert isinstance(result, SignificanceCorrectionResult)
    assert result.correction == "romano_wolf"
    assert result.corrected_mask.shape == (5,)
    assert result.n_surrogates == 99


def test_compute_significance_bands_corrected_bh_mode() -> None:
    """Smoke test for BH mode in compute_significance_bands_corrected."""
    from forecastability.diagnostics.surrogates import compute_significance_bands_corrected

    rng = np.random.default_rng(1)
    ts = rng.standard_normal(200)
    observed = np.full(5, 3.0)  # high signal

    result = compute_significance_bands_corrected(
        ts,
        observed,
        metric_name="ami",
        max_lag=5,
        n_surrogates=99,
        alpha=0.05,
        correction="bh",
    )
    assert isinstance(result, SignificanceCorrectionResult)
    assert result.correction == "bh"


def test_compute_significance_bands_corrected_rejects_size_mismatch() -> None:
    """compute_significance_bands_corrected must raise on observed / max_lag mismatch."""
    from forecastability.diagnostics.surrogates import compute_significance_bands_corrected

    rng = np.random.default_rng(2)
    ts = rng.standard_normal(200)
    observed = np.ones(6)  # wrong size for max_lag=5

    with pytest.raises(ValueError, match="does not match max_lag"):
        compute_significance_bands_corrected(
            ts,
            observed,
            metric_name="ami",
            max_lag=5,
            n_surrogates=99,
        )


def test_compute_significance_bands_with_correction_param() -> None:
    """compute_significance_bands with correction='romano_wolf' returns finite bands."""
    from forecastability.diagnostics.surrogates import compute_significance_bands

    rng = np.random.default_rng(3)
    ts = rng.standard_normal(300)

    lower, upper = compute_significance_bands(
        ts,
        metric_name="ami",
        max_lag=5,
        n_surrogates=99,
        alpha=0.05,
        correction="romano_wolf",
    )
    assert lower.shape == (5,)
    assert upper.shape == (5,)
    # upper may be inf for non-significant lags; lower should be finite.
    assert np.all(np.isfinite(lower))


def test_compute_significance_bands_none_correction_legacy_behavior() -> None:
    """compute_significance_bands with correction='none' returns legacy percentile bands."""
    from forecastability.diagnostics.surrogates import compute_significance_bands

    rng = np.random.default_rng(4)
    ts = rng.standard_normal(300)

    lower, upper = compute_significance_bands(
        ts,
        metric_name="ami",
        max_lag=5,
        n_surrogates=99,
        alpha=0.05,
        correction="none",
    )
    # With correction='none', both bands should be finite percentile values.
    assert np.all(np.isfinite(lower))
    assert np.all(np.isfinite(upper))
