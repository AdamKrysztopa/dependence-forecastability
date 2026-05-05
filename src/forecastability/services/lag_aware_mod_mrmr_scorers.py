"""Pairwise scorer protocol, registry, normalizers, and built-in scorers.

Provides the scoring infrastructure for Lag-Aware ModMRMR:

- :class:`PairwiseDependenceScorer` — protocol for all pairwise scorers.
- :class:`_RawScore` — internal result before normalization.
- Concrete built-in scorer implementations (Pearson, Spearman, sklearn MI,
  Catt/KSG kNN MI, GCMI).
- :class:`_PoolNormalizer` — fits on a score pool and transforms to ``[0, 1]``.
- :func:`build_scorer` — factory from :class:`PairwiseScorerSpec`.
- :func:`build_normalizer` — factory for the normalization strategy.
- :func:`make_diagnostics` — assembles :class:`ScorerDiagnostics` after
  normalization.

ModMRMR is a project-defined mRMR variant proposed by Adam Krysztopa.
This module supplies the scoring primitives that ModMRMR plugs together; the
method-agnostic design means any compliant scorer can be used for relevance,
redundancy, or target-history novelty penalties.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.feature_selection import mutual_info_regression

from forecastability.diagnostics.gcmi import compute_gcmi
from forecastability.triage.lag_aware_mod_mrmr import (
    NormalizationStrategy,
    PairwiseScorerSpec,
    ScorerDiagnostics,
    SignificanceMethod,
)

# ---------------------------------------------------------------------------
# Internal raw-score container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _RawScore:
    """Internal result from a scorer before normalization.

    Attributes:
        raw_value: Original scorer output (unbounded non-negative float).
        n_pairs: Number of aligned non-missing sample pairs scored.
        estimator_settings: JSON-serialisable estimator settings.
        bands: Optional reliability bands or clipping notes.
        warnings: Low-sample, convergence, or estimator warnings.
        p_value: Unadjusted p-value; ``None`` when not computed.
    """

    raw_value: float
    n_pairs: int
    estimator_settings: dict[str, Any] = field(default_factory=dict)
    bands: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    p_value: float | None = None


# ---------------------------------------------------------------------------
# Scorer protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class PairwiseDependenceScorer(Protocol):
    """Protocol for pairwise dependence scorers.

    A scorer takes two aligned 1-D arrays and returns a :class:`_RawScore`
    with the raw dependence value and metadata.  Normalization is applied
    separately by a :class:`_PoolNormalizer` after collecting the full pool.
    """

    name: str

    def score_pair(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        random_state: int = 42,
    ) -> _RawScore:
        """Score one ``(x, y)`` pair.

        Args:
            x: First 1-D array (lagged covariate or feature).
            y: Second 1-D array (target or another feature).
            random_state: Random seed for stochastic components.

        Returns:
            :class:`_RawScore` with raw dependence value and metadata.
        """
        ...


# ---------------------------------------------------------------------------
# Built-in concrete scorers
# ---------------------------------------------------------------------------

_MIN_PAIRS = 10  # minimum pair count to attempt scoring


class _PearsonAbsScorer:
    """Absolute Pearson correlation.  Cheap linear baseline."""

    name: str = "pearson_abs"

    def score_pair(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        random_state: int = 42,
    ) -> _RawScore:
        n = int(np.sum(np.isfinite(x) & np.isfinite(y)))
        warn: list[str] = []
        if n < _MIN_PAIRS:
            warn.append(f"Only {n} finite pairs; score set to 0.")
            return _RawScore(raw_value=0.0, n_pairs=n, warnings=warn)
        mask = np.isfinite(x) & np.isfinite(y)
        xf, yf = x[mask], y[mask]
        result = pearsonr(xf, yf)
        raw = float(abs(result.statistic))
        if not math.isfinite(raw):
            raw = 0.0
        return _RawScore(
            raw_value=raw,
            n_pairs=n,
            estimator_settings={"scorer": "pearson_abs"},
        )


class _SpearmanAbsScorer:
    """Absolute Spearman rank correlation.  Monotonic nonparametric baseline."""

    name: str = "spearman_abs"

    def score_pair(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        random_state: int = 42,
    ) -> _RawScore:
        mask = np.isfinite(x) & np.isfinite(y)
        n = int(mask.sum())
        warn: list[str] = []
        if n < _MIN_PAIRS:
            warn.append(f"Only {n} finite pairs; score set to 0.")
            return _RawScore(raw_value=0.0, n_pairs=n, warnings=warn)
        xf, yf = x[mask], y[mask]
        result = spearmanr(xf, yf)
        raw = float(abs(result.statistic))
        if not math.isfinite(raw):
            raw = 0.0
        return _RawScore(
            raw_value=raw,
            n_pairs=n,
            estimator_settings={"scorer": "spearman_abs"},
        )


class _MutualInfoSklearnScorer:
    """Mutual information via sklearn KSG estimator.

    Fast practical baseline using ``n_neighbors=3`` (lighter than AMI's 8).
    """

    name: str = "mutual_info_sklearn"

    def __init__(self, *, n_neighbors: int = 3) -> None:
        self._n_neighbors = n_neighbors

    def score_pair(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        random_state: int = 42,
    ) -> _RawScore:
        mask = np.isfinite(x) & np.isfinite(y)
        n = int(mask.sum())
        warn: list[str] = []
        if n < _MIN_PAIRS:
            warn.append(f"Only {n} finite pairs; score set to 0.")
            return _RawScore(raw_value=0.0, n_pairs=n, warnings=warn)
        xf, yf = x[mask], y[mask]
        raw = float(
            mutual_info_regression(
                xf.reshape(-1, 1),
                yf,
                n_neighbors=self._n_neighbors,
                random_state=random_state,
            )[0]
        )
        if not math.isfinite(raw):
            raw = 0.0
        return _RawScore(
            raw_value=max(raw, 0.0),
            n_pairs=n,
            estimator_settings={
                "scorer": "mutual_info_sklearn",
                "n_neighbors": self._n_neighbors,
            },
        )


class _CattKnnMiScorer:
    """Catt-style AMI / kNN MI scorer.

    Uses the KSG mutual information estimator with ``n_neighbors=8``,
    aligned with the existing AMI computation lineage.

    This is the scientific native scoring mode for Lag-Aware ModMRMR.
    It provides nonlinear dependence estimates suitable for relevance
    scoring, selected-lag redundancy, and target-history novelty penalties.
    """

    name: str = "catt_knn_mi"

    def __init__(self, *, n_neighbors: int = 8) -> None:
        self._n_neighbors = n_neighbors

    def score_pair(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        random_state: int = 42,
    ) -> _RawScore:
        mask = np.isfinite(x) & np.isfinite(y)
        n = int(mask.sum())
        warn: list[str] = []
        if n < _MIN_PAIRS:
            warn.append(f"Only {n} finite pairs; score set to 0.")
            return _RawScore(raw_value=0.0, n_pairs=n, warnings=warn)
        xf, yf = x[mask], y[mask]
        raw = float(
            mutual_info_regression(
                xf.reshape(-1, 1),
                yf,
                n_neighbors=self._n_neighbors,
                random_state=random_state,
            )[0]
        )
        if not math.isfinite(raw):
            raw = 0.0
        return _RawScore(
            raw_value=max(raw, 0.0),
            n_pairs=n,
            estimator_settings={
                "scorer": "catt_knn_mi",
                "n_neighbors": self._n_neighbors,
            },
        )


class _GcmiScorer:
    """Gaussian-copula MI scorer.  Nonlinear proxy; experimental."""

    name: str = "gcmi"

    def score_pair(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        random_state: int = 42,
    ) -> _RawScore:
        mask = np.isfinite(x) & np.isfinite(y)
        n = int(mask.sum())
        warn: list[str] = []
        if n < _MIN_PAIRS:
            warn.append(f"Only {n} finite pairs; score set to 0.")
            return _RawScore(raw_value=0.0, n_pairs=n, warnings=warn)
        xf, yf = x[mask], y[mask]
        raw = compute_gcmi(xf, yf)
        if not math.isfinite(raw):
            raw = 0.0
        return _RawScore(
            raw_value=max(raw, 0.0),
            n_pairs=n,
            estimator_settings={"scorer": "gcmi"},
        )


# ---------------------------------------------------------------------------
# Scorer factory
# ---------------------------------------------------------------------------

_SCORER_REGISTRY: dict[str, PairwiseDependenceScorer] = {
    "pearson_abs": _PearsonAbsScorer(),
    "spearman_abs": _SpearmanAbsScorer(),
    "mutual_info_sklearn": _MutualInfoSklearnScorer(),
    "catt_knn_mi": _CattKnnMiScorer(),
    "ksg_mi": _CattKnnMiScorer(),
    "cross_ami_score": _CattKnnMiScorer(),
    "gcmi": _GcmiScorer(),
}

_SUPPORTED_SCORER_NAMES = frozenset(_SCORER_REGISTRY)


def build_scorer(spec: PairwiseScorerSpec) -> PairwiseDependenceScorer:
    """Build a concrete scorer from a :class:`PairwiseScorerSpec`.

    Args:
        spec: Scorer specification from the run configuration.

    Returns:
        A concrete :class:`PairwiseDependenceScorer` instance.

    Raises:
        ValueError: If ``spec.name`` is not a registered scorer.
    """
    name = spec.name
    if name not in _SCORER_REGISTRY:
        supported = ", ".join(sorted(_SUPPORTED_SCORER_NAMES))
        raise ValueError(
            f"Unknown scorer name {name!r}. Supported scorers: {supported}"
        )
    scorer = _SCORER_REGISTRY[name]
    n_neighbors = spec.settings.get("n_neighbors")
    if n_neighbors is not None and hasattr(scorer, "_n_neighbors"):
        if name in ("catt_knn_mi", "ksg_mi", "cross_ami_score"):
            return _CattKnnMiScorer(n_neighbors=int(n_neighbors))
        if name == "mutual_info_sklearn":
            return _MutualInfoSklearnScorer(n_neighbors=int(n_neighbors))
    return scorer


# ---------------------------------------------------------------------------
# Pool normalizers
# ---------------------------------------------------------------------------


class _PoolNormalizer:
    """Pool-relative normalizer for raw scorer values.

    Fits on a pool of raw scores collected from one selection run, then
    transforms individual values to a ``[0, 1]``-bounded range.  The fitted
    state is deterministic given the same pool.

    Supported strategies:

    - ``"rank_percentile"``: rank-percentile position in the pool.
    - ``"none"``: pass-through (raw value is used as-is; clip externally).

    Args:
        strategy: Normalization strategy to apply.
        fit_scope_id: Human-readable identifier for the normalization pool
            (e.g. ``"relevance_run_42"``).
    """

    def __init__(
        self,
        strategy: NormalizationStrategy,
        *,
        fit_scope_id: str = "",
    ) -> None:
        self._strategy = strategy
        self._fit_scope_id = fit_scope_id
        self._sorted_pool: list[float] = []
        self._fitted = False

    @property
    def strategy(self) -> NormalizationStrategy:
        """Normalization strategy."""
        return self._strategy

    @property
    def fit_scope_id(self) -> str:
        """Identifier for the pool used to fit this normalizer."""
        return self._fit_scope_id

    def fit(self, scores: list[float]) -> None:
        """Fit the normalizer on a pool of raw scores.

        Args:
            scores: Raw score values from one selection run pool.

        Raises:
            ValueError: If the pool is empty or contains non-finite values.
        """
        if len(scores) == 0:
            raise ValueError("Cannot fit normalizer on an empty pool")
        finite = [v for v in scores if math.isfinite(v)]
        if len(finite) == 0:
            raise ValueError("All pool scores are non-finite; cannot fit normalizer")
        self._sorted_pool = sorted(finite)
        self._fitted = True

    def transform(self, value: float) -> float:
        """Transform one raw value using the fitted pool.

        For ``"rank_percentile"`` the result is the fraction of pool values
        that are <= ``value`` (always in ``[0, 1]``).

        For ``"none"`` the raw value is returned unchanged; the caller is
        responsible for clipping to ``[0, 1]`` when used as a similarity
        penalty.

        Args:
            value: Raw scorer output to normalize.

        Returns:
            Normalized value.

        Raises:
            RuntimeError: If called before :meth:`fit`.
        """
        if self._strategy == "none":
            return value if math.isfinite(value) else 0.0

        if not self._fitted:
            raise RuntimeError(
                "Normalizer must be fitted before calling transform(). "
                "Call fit(pool) first."
            )

        if self._strategy == "rank_percentile":
            if not math.isfinite(value):
                return 0.0
            rank = bisect.bisect_right(self._sorted_pool, value)
            return float(rank) / len(self._sorted_pool)

        if self._strategy in ("surrogate_effect_clip", "nmi_min_entropy", "nmi_mean_entropy"):
            raise NotImplementedError(
                f"Normalization strategy {self._strategy!r} requires additional "
                "scorer infrastructure not yet available in Phase 1. "
                "Use 'rank_percentile' or 'none' instead."
            )

        return value  # fallback — should not be reached for defined strategies


def build_normalizer(
    strategy: NormalizationStrategy,
    *,
    fit_scope_id: str = "",
) -> _PoolNormalizer:
    """Build a pool normalizer for the given strategy.

    Args:
        strategy: Normalization strategy to apply.
        fit_scope_id: Human-readable pool identifier for diagnostics.

    Returns:
        An unfitted :class:`_PoolNormalizer` instance.
    """
    return _PoolNormalizer(strategy, fit_scope_id=fit_scope_id)


# ---------------------------------------------------------------------------
# Diagnostics assembler
# ---------------------------------------------------------------------------


def make_diagnostics(
    raw: _RawScore,
    *,
    normalized_value: float,
    normalization: NormalizationStrategy,
    significance_method: SignificanceMethod,
    adjusted_p_value: float | None = None,
) -> ScorerDiagnostics:
    """Assemble a :class:`ScorerDiagnostics` from a raw score and normalisation.

    Args:
        raw: Raw scorer output (before normalization).
        normalized_value: Transformed value produced by the pool normalizer.
        normalization: Normalization strategy that produced ``normalized_value``.
        significance_method: Significance method used during scoring.
        adjusted_p_value: Multiple-comparisons-adjusted p-value; ``None``
            unless ``significance_method="bh_fdr_adjustment"``.

    Returns:
        Frozen :class:`ScorerDiagnostics` ready for inclusion in result models.
    """
    clipped = max(normalized_value, 0.0)
    return ScorerDiagnostics(
        raw_value=raw.raw_value,
        normalized_value=clipped,
        p_value=raw.p_value,
        adjusted_p_value=adjusted_p_value,
        n_pairs=max(raw.n_pairs, 1),
        estimator_settings=raw.estimator_settings,
        normalization=normalization,
        significance_method=significance_method,
        bands=list(raw.bands),
        warnings=list(raw.warnings),
    )
