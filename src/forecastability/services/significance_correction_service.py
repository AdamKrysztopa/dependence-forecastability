"""SignificanceCorrectionService — RVH-F03.

Implements Romano-Wolf step-down FWER control, Benjamini-Hochberg FDR,
Benjamini-Yekutieli FDR, and raw (no-correction) modes for per-lag
significance testing against a pre-computed surrogate matrix.

Correction choice guidance
--------------------------
Romano-Wolf (``"romano_wolf"``) controls FWER using the max-statistic
null derived from the surrogate matrix.  It is the statistically honest
choice for formal significance when the goal is "find all significant
lags while controlling family-wise error".  The step-down procedure is
more powerful than single-step Bonferroni.

Benjamini-Yekutieli (``"by"``) controls FDR under *arbitrary* dependence,
including autocorrelated lags.  It is the correct FDR procedure when lag
statistics are not positively correlated.  It is conservative relative to
BH but does not assume any dependence structure.

Benjamini-Hochberg (``"bh"``) controls FDR assuming positive regression
dependence (PRDS).  Less conservative than BY but not valid for arbitrary
autocorrelation structures.  Suitable when lags are expected to be
positively dependent (e.g. monotonically decaying AMI).

``"none"`` applies no correction; each lag is tested at the nominal alpha
independently.  Preserved for backward compatibility.

The default ``"romano_wolf"`` is the statistically honest choice for
formal significance when structure-finding is the goal and FWER control
is desired.  Use ``"bh"`` or ``"by"`` when FDR control is more
appropriate (geometry-style queries where false negatives are costly).

Romano-Wolf implementation note
--------------------------------
The step-down algorithm follows Romano & Wolf (2005) Algorithm 4.1.  At
step j (testing the j-th most-significant hypothesis, hypotheses sorted by
ascending raw p-value / descending observed statistic), the max-statistic
null is the maximum over the *remaining untested subset* ``{j, j+1, ..., m}``
of surrogate columns.  This subset-max null is strictly more powerful than
the Westfall-Young single-step procedure, which pools the full-set maximum
for every hypothesis.

Phase surrogates are exchangeable under H0 (no temporal dependence at any
lag): the spectrum is preserved, so the joint null of "all lags are noise"
is respected.

A separate monotonicity (coherence) constraint is also enforced: if step
j-1 was not rejected, step j cannot be either.  This is a standard
step-down bookkeeping rule, not a source of power gain.

References: Romano & Wolf (2005) "Exact and approximate stepdown methods
for multiple hypothesis testing", JASA 100(469):94-108.  Westfall & Young
(1993) "Resampling-based multiple testing".
"""

from __future__ import annotations

from typing import Literal

import numpy as np

from forecastability.domain.results.significance_correction import (
    SignificanceCorrectionResult,
)

__all__ = ["SignificanceCorrectionService"]

CorrectionMode = Literal["romano_wolf", "bh", "by", "none"]


class SignificanceCorrectionService:
    """Apply family-wise or FDR significance correction to per-lag test results.

    This service consumes the surrogate matrix already produced by the
    kernel — no surrogate recomputation occurs here.

    Parameters
    ----------
    correction:
        Correction method.  One of ``"romano_wolf"``, ``"bh"``, ``"by"``,
        ``"none"``.  Default ``"romano_wolf"``.
    alpha:
        Nominal error rate.  For Romano-Wolf: FWER.  For bh/by: FDR.
        For none: per-lag alpha.  Default 0.05.

    Notes
    -----
    ``low_surrogate_warning`` is set when ``n_surrogates < 999`` and
    ``correction="romano_wolf"``.  With 99 surrogates the max-statistic
    null has only 99 quantile steps; the achievable FWER resolution is
    1/99 ≈ 0.0101, which means the test at α=0.05 is effectively α=0.04
    or α=0.05 depending on rounding.  For formal significance testing
    ``n_surrogates >= 999`` is recommended.
    """

    def __init__(
        self,
        correction: CorrectionMode = "romano_wolf",
        alpha: float = 0.05,
    ) -> None:
        if correction not in {"romano_wolf", "bh", "by", "none"}:
            raise ValueError(
                f"correction must be one of 'romano_wolf', 'bh', 'by', 'none'; got {correction!r}"
            )
        if not (0.0 < alpha < 1.0):
            raise ValueError(f"alpha must be in (0, 1); got {alpha}")
        self._correction: CorrectionMode = correction
        self._alpha = alpha

    def correct(
        self,
        surrogate_matrix: np.ndarray,
        observed: np.ndarray,
    ) -> SignificanceCorrectionResult:
        """Apply the configured correction and return a frozen result.

        Parameters
        ----------
        surrogate_matrix:
            Shape ``(n_surrogates, H)``.  Each row is one surrogate's
            per-lag MI/AMI curve.  Values may be NaN for invalid horizons.
        observed:
            Shape ``(H,)``.  Observed per-lag MI/AMI values.

        Returns
        -------
        SignificanceCorrectionResult
            Frozen Pydantic result with corrected mask, raw p-values, and
            diagnostic metadata.
        """
        surrogate_matrix = np.asarray(surrogate_matrix, dtype=float)
        observed = np.asarray(observed, dtype=float)

        if surrogate_matrix.ndim != 2:
            raise ValueError(
                f"surrogate_matrix must be 2-D (n_surrogates, H); "
                f"got shape {surrogate_matrix.shape}"
            )
        if observed.ndim != 1:
            raise ValueError(f"observed must be 1-D (H,); got shape {observed.shape}")
        n_surrogates, n_lags = surrogate_matrix.shape
        if n_lags != observed.size:
            raise ValueError(
                f"surrogate_matrix has {n_lags} lags but observed has "
                f"{observed.size} entries; they must match."
            )
        if n_surrogates < 1:
            raise ValueError("surrogate_matrix must have at least 1 row")

        raw_p = self._compute_raw_p_values(surrogate_matrix, observed)

        if self._correction == "romano_wolf":
            mask = self._romano_wolf(surrogate_matrix, observed, raw_p)
        elif self._correction == "bh":
            mask = self._bh(raw_p)
        elif self._correction == "by":
            mask = self._by(raw_p)
        else:  # "none"
            mask = raw_p <= self._alpha

        low_surrogate_warning = self._correction == "romano_wolf" and n_surrogates < 999

        return SignificanceCorrectionResult(
            correction=self._correction,
            family_wise_alpha=self._alpha,
            corrected_mask=mask,
            raw_p_values=raw_p,
            n_surrogates=n_surrogates,
            low_surrogate_warning=low_surrogate_warning,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_raw_p_values(
        self,
        surrogate_matrix: np.ndarray,
        observed: np.ndarray,
    ) -> np.ndarray:
        """Estimate per-lag p-values from surrogate rank.

        p-value at lag h = fraction of surrogates with value >= observed[h],
        using NaN-safe comparison.
        """
        # surrogate_matrix: (n_surrogates, H)
        # observed: (H,)
        # Count how many surrogates exceed the observed value at each lag.
        # NaN surrogates are treated as not exceeding the observed value.
        n_surrogates = surrogate_matrix.shape[0]
        nan_obs = np.isnan(observed)
        # Replace NaN observed with +inf so no surrogate can exceed them;
        # these entries are overwritten with NaN below.
        obs_safe = np.where(nan_obs, np.inf, observed)
        exceed = np.nansum(surrogate_matrix >= obs_safe[np.newaxis, :], axis=0)
        # Add 1 to numerator and denominator (Davison & Hinkley correction for
        # Monte-Carlo p-values: p = (B_exceed + 1) / (B + 1) is more conservative
        # and avoids p=0 for observed > all surrogates).
        raw_p = (exceed + 1.0) / (n_surrogates + 1.0)
        # NaN observed → NaN p-value so BH/BY correctly skip those lags.
        raw_p = np.where(nan_obs, np.nan, raw_p)
        return raw_p.astype(float)

    def _romano_wolf(
        self,
        surrogate_matrix: np.ndarray,
        observed: np.ndarray,
        raw_p: np.ndarray,
    ) -> np.ndarray:
        """Romano-Wolf (2005) step-down max-T FWER correction.

        Algorithm (Romano & Wolf 2005, Algorithm 4.1):

        1. Sort observed lags from most significant (largest value) to least.
           NaN observed values are ranked last (treated as least significant).
        2. At step j (testing the j-th hypothesis in sorted order), compute the
           subset-max null distribution: for each surrogate replicate, take the
           maximum value across only the *remaining untested* lags
           {j, j+1, ..., m}.  This subset-max null is strictly more powerful
           than the full-set max-T used by the Westfall-Young single-step
           procedure.
        3. The adjusted p-value for the lag at step j is the fraction of
           subset-max null surrogates that exceed the observed value at that lag
           (with +1 Monte-Carlo correction).
        4. Enforce step-down coherence (monotonicity): if step j-1 was not
           rejected, step j also cannot be rejected.  This is a separate
           coherence constraint, not a source of power gain.
        5. Return boolean mask: lag is significant iff adjusted p <= alpha.

        References: Romano & Wolf (2005) "Exact and approximate stepdown
        methods for multiple hypothesis testing", JASA 100(469):94-108.

        Note: this operates on the observed MI values directly as test
        statistics.  Higher observed MI = more significant.
        """
        n_surrogates, n_lags = surrogate_matrix.shape

        # Step 1: rank lags from most significant (highest observed) to least.
        # NaN observed values are ranked last (treated as least significant).
        nan_obs = np.isnan(observed)
        sort_order = np.argsort(np.where(nan_obs, -np.inf, observed))[
            ::-1
        ]  # descending: most significant first

        # Step 2 & 3: step-down with subset-max null at each step j.
        adjusted_p = np.ones(n_lags, dtype=float)
        rejected_so_far = True  # monotonicity gate: flip to False on first fail

        for j, lag_idx in enumerate(sort_order):
            if nan_obs[lag_idx]:
                # NaN horizon: not significant, cut the step-down chain.
                adjusted_p[lag_idx] = 1.0
                rejected_so_far = False
                continue

            obs_val = observed[lag_idx]

            # Subset-max null: maximum over remaining untested hypotheses
            # {j, j+1, ..., m} in sorted order (Romano-Wolf Algorithm 4.1).
            remaining = sort_order[j:]  # indices of hypotheses not yet tested
            surr_subset = surrogate_matrix[:, remaining]  # (n_surrogates, |remaining|)
            max_null_j = np.nanmax(surr_subset, axis=1)  # (n_surrogates,)
            # If all values in a row are NaN, nanmax returns NaN; treat as -inf
            # so those surrogates do not inflate the null.
            max_null_j = np.where(np.isnan(max_null_j), -np.inf, max_null_j)

            # p = fraction of subset-max null surrogates >= obs_val
            # (+1 numerator and denominator: Davison & Hinkley MC correction).
            exceed = int(np.sum(max_null_j >= obs_val))
            p_adj = (exceed + 1.0) / (n_surrogates + 1.0)

            # Step 4: enforce monotonicity (step-down coherence).
            if not rejected_so_far:
                p_adj = 1.0
            elif p_adj > self._alpha:
                rejected_so_far = False

            adjusted_p[lag_idx] = p_adj

        return (adjusted_p <= self._alpha).astype(bool)

    def _bh(self, raw_p: np.ndarray) -> np.ndarray:
        """Benjamini-Hochberg FDR correction.

        Assumes positive regression dependence (PRDS) across lags.
        Only valid p-values (non-NaN) participate; NaN lags are not rejected.
        """
        n_lags = raw_p.size
        valid_mask = ~np.isnan(raw_p)
        result = np.zeros(n_lags, dtype=bool)

        valid_indices = np.flatnonzero(valid_mask)
        if valid_indices.size == 0:
            return result

        n_valid = valid_indices.size
        p_valid = raw_p[valid_indices]

        # Sort by p-value ascending.
        sort_idx = np.argsort(p_valid)
        sorted_p = p_valid[sort_idx]
        sorted_orig_idx = valid_indices[sort_idx]

        # BH threshold: p[i] <= alpha * (i+1) / n_valid
        thresholds = self._alpha * (np.arange(1, n_valid + 1) / n_valid)
        below = sorted_p <= thresholds

        # Reject all hypotheses up to and including the last one below threshold.
        if not np.any(below):
            return result

        last_rejected = int(np.flatnonzero(below)[-1])
        rejected_sorted = sorted_orig_idx[: last_rejected + 1]
        result[rejected_sorted] = True
        return result

    def _by(self, raw_p: np.ndarray) -> np.ndarray:
        """Benjamini-Yekutieli FDR correction.

        Valid under arbitrary (including negative) dependence.  More
        conservative than BH by a factor of c(n) = sum(1/i, i=1..n).
        Suitable for autocorrelated lag structures.
        """
        n_lags = raw_p.size
        valid_mask = ~np.isnan(raw_p)
        result = np.zeros(n_lags, dtype=bool)

        valid_indices = np.flatnonzero(valid_mask)
        if valid_indices.size == 0:
            return result

        n_valid = valid_indices.size
        p_valid = raw_p[valid_indices]

        # BY harmonic correction factor c(n_valid) = sum(1/i for i in 1..n_valid)
        cn = float(np.sum(1.0 / np.arange(1, n_valid + 1)))

        # Sort by p-value ascending.
        sort_idx = np.argsort(p_valid)
        sorted_p = p_valid[sort_idx]
        sorted_orig_idx = valid_indices[sort_idx]

        # BY threshold: p[i] <= alpha * (i+1) / (n_valid * c(n_valid))
        thresholds = self._alpha * (np.arange(1, n_valid + 1) / (n_valid * cn))
        below = sorted_p <= thresholds

        if not np.any(below):
            return result

        last_rejected = int(np.flatnonzero(below)[-1])
        rejected_sorted = sorted_orig_idx[: last_rejected + 1]
        result[rejected_sorted] = True
        return result
