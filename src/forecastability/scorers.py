"""Scorer registry for method-independent dependence measures."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import permutations
from typing import Literal, Protocol, runtime_checkable

import numpy as np
from scipy.spatial.distance import pdist, squareform
from scipy.stats import kendalltau, spearmanr
from sklearn.feature_selection import mutual_info_regression

from forecastability.spectral_utils import compute_normalised_psd, spectral_entropy


@runtime_checkable
class DependenceScorer(Protocol):
    """Protocol for dependence scoring functions.

    A scorer takes two aligned 1-D arrays (past, future) and returns
    a non-negative scalar measuring statistical dependence.
    """

    def __call__(
        self,
        past: np.ndarray,
        future: np.ndarray,
        *,
        random_state: int = 42,
    ) -> float: ...


@runtime_checkable
class SeriesDiagnosticScorer(Protocol):
    """Protocol for univariate diagnostic scoring functions.

    A scorer takes a single 1-D series and returns a non-negative scalar
    measuring a univariate property (entropy, spectral predictability, etc.).

    This is distinct from :class:`DependenceScorer` which takes ``(past, future)``
    pairs.  Used by F4 (SpectralPredictabilityScorer) and F6
    (PermutationEntropyScorer).
    """

    def __call__(
        self,
        series: np.ndarray,
        *,
        random_state: int = 42,
    ) -> float: ...


@dataclass(slots=True)
class ScorerInfo:
    """Metadata for a registered scorer.

    Attributes:
        name: Short identifier (e.g. ``"mi"``, ``"pearson"``).
        scorer: Callable implementing :class:`DependenceScorer` or
            :class:`SeriesDiagnosticScorer`.
        family: Scorer family used to auto-select triage thresholds.
        description: One-line description of the scorer.
        kind: Whether the scorer operates on ``(past, future)`` pairs
            (``"bivariate"``) or a single series (``"univariate"``).
    """

    name: str
    scorer: DependenceScorer | SeriesDiagnosticScorer
    family: Literal["nonlinear", "linear", "rank", "bounded_nonlinear"]
    description: str
    kind: Literal["bivariate", "univariate"] = "bivariate"


@runtime_checkable
class ScorerRegistryProtocol(Protocol):
    """Minimal interface that internal services depend on.

    Any object satisfying this protocol may be used wherever a scorer
    registry is expected, enabling dependency inversion and test doubles.
    """

    def get(self, name: str) -> ScorerInfo: ...

    def register(
        self,
        name: str,
        scorer: DependenceScorer | SeriesDiagnosticScorer,
        *,
        family: Literal["nonlinear", "linear", "rank", "bounded_nonlinear"],
        description: str,
        kind: Literal["bivariate", "univariate"] = "bivariate",
    ) -> None: ...

    def list_scorers(self) -> list[ScorerInfo]: ...


class ScorerRegistry:
    """Registry of named dependence scorers.

    Example::

        registry = default_registry()
        info = registry.get("mi")
        score = info.scorer(past, future, random_state=42)
    """

    def __init__(self) -> None:
        self._scorers: dict[str, ScorerInfo] = {}

    def register(
        self,
        name: str,
        scorer: DependenceScorer | SeriesDiagnosticScorer,
        *,
        family: Literal["nonlinear", "linear", "rank", "bounded_nonlinear"],
        description: str,
        kind: Literal["bivariate", "univariate"] = "bivariate",
    ) -> None:
        """Register a scorer under *name*.

        Args:
            name: Unique identifier for the scorer.
            scorer: Callable matching :class:`DependenceScorer` or
                :class:`SeriesDiagnosticScorer`.
            family: Scorer family (``"nonlinear"``, ``"linear"``, ``"rank"``,
                or ``"bounded_nonlinear"``).
            description: One-line description.
            kind: ``"bivariate"`` for ``(past, future)`` scorers (default) or
                ``"univariate"`` for single-series scorers.
        """
        self._scorers[name] = ScorerInfo(
            name=name,
            scorer=scorer,
            family=family,
            description=description,
            kind=kind,
        )

    def register_scorer(
        self,
        name: str,
        *,
        family: Literal["nonlinear", "linear", "rank", "bounded_nonlinear"],
        description: str,
    ) -> Callable[[DependenceScorer], DependenceScorer]:
        """Decorator to register a scorer function.

        Example::

            @registry.register_scorer("my_metric", family="nonlinear",
                                      description="Custom metric")
            def my_scorer(past, future, *, random_state=42):
                ...

        Args:
            name: Unique identifier for the scorer.
            family: Scorer family.
            description: One-line description.

        Returns:
            Decorator that registers the function and returns it unchanged.
        """

        def decorator(fn: DependenceScorer) -> DependenceScorer:
            self.register(name, fn, family=family, description=description)
            return fn

        return decorator

    def get(self, name: str) -> ScorerInfo:
        """Retrieve a scorer by name.

        Args:
            name: Scorer identifier.

        Returns:
            The corresponding :class:`ScorerInfo`.

        Raises:
            KeyError: If *name* is not registered. The error message lists
                available scorers.
        """
        try:
            return self._scorers[name]
        except KeyError:
            available = ", ".join(sorted(self._scorers)) or "(none)"
            raise KeyError(f"Unknown scorer {name!r}. Available scorers: {available}") from None

    def list_scorers(self) -> list[ScorerInfo]:
        """Return all registered scorers in registration order.

        Returns:
            List of :class:`ScorerInfo` objects.
        """
        return list(self._scorers.values())

    def __contains__(self, name: str) -> bool:
        return name in self._scorers


# ---------------------------------------------------------------------------
# Built-in scorer implementations
# ---------------------------------------------------------------------------


def _mi_scorer(
    past: np.ndarray,
    future: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """kNN mutual information via sklearn ``mutual_info_regression``."""
    value = mutual_info_regression(
        past.reshape(-1, 1),
        future,
        n_neighbors=8,
        random_state=random_state,
    )[0]
    return max(float(value), 0.0)


def _pearson_scorer(
    past: np.ndarray,
    future: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Absolute Pearson correlation coefficient."""
    del random_state
    if len(past) < 2:
        return 0.0
    result = np.corrcoef(past, future)[0, 1]
    return 0.0 if np.isnan(result) else float(abs(result))


def _spearman_scorer(
    past: np.ndarray,
    future: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Absolute Spearman rank correlation."""
    del random_state
    rho, _ = spearmanr(past, future)
    return 0.0 if np.isnan(rho) else float(abs(rho))


def _kendall_scorer(
    past: np.ndarray,
    future: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Absolute Kendall tau-b correlation."""
    del random_state
    tau, _ = kendalltau(past, future)
    return 0.0 if np.isnan(tau) else float(abs(tau))


def _dcov_centred(x: np.ndarray) -> np.ndarray:
    """Compute a doubly-centred Euclidean distance matrix."""
    d = squareform(pdist(x.reshape(-1, 1), metric="euclidean"))
    row_mean = d.mean(axis=1, keepdims=True)
    col_mean = d.mean(axis=0, keepdims=True)
    grand_mean = d.mean()
    return d - row_mean - col_mean + grand_mean


def _distance_scorer(
    past: np.ndarray,
    future: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Distance correlation (Székely/Rizzo energy-distance formulation).

    Distance correlation is bounded [0, 1] and equals zero iff X and Y are
    independent.  Placed in the "bounded_nonlinear" family for triage
    threshold calibration.
    """
    del random_state
    a = _dcov_centred(past)
    b = _dcov_centred(future)
    n = past.size
    v2_xy = (a * b).sum() / (n * n)
    v2_xx = (a * a).sum() / (n * n)
    v2_yy = (b * b).sum() / (n * n)
    denom = np.sqrt(v2_xx * v2_yy)
    if denom < 1e-15:
        return 0.0
    return float(np.sqrt(max(v2_xy / denom, 0.0)))


# ---------------------------------------------------------------------------
# Univariate scorer implementations (SeriesDiagnosticScorer)
# ---------------------------------------------------------------------------

_ORDINAL_PATTERN_CACHE: dict[int, list[tuple[int, ...]]] = {}


def _get_ordinal_patterns(m: int) -> list[tuple[int, ...]]:
    """Return all ordinal patterns (permutations) of order *m*, cached."""
    if m not in _ORDINAL_PATTERN_CACHE:
        _ORDINAL_PATTERN_CACHE[m] = list(permutations(range(m)))
    return _ORDINAL_PATTERN_CACHE[m]


def _compute_permutation_entropy(series: np.ndarray, *, m: int) -> float:
    """Compute normalised permutation entropy for embedding order *m*.

    Tie-breaking rule: ``numpy.argsort`` with ``kind="stable"`` (documented
    and fixed; ties are broken by position, not by random jitter).

    H_perm_norm = (-sum_pi p(pi) * log(p(pi))) / log(m!)

    Args:
        series: 1-D float array, length >= m.
        m: Embedding order (number of consecutive elements per pattern).

    Returns:
        Normalised permutation entropy in [0, 1].

    Raises:
        ValueError: When ``len(series) < m`` or ``m < 2``.
    """
    if m < 2:
        raise ValueError(f"Embedding order m must be >= 2; got {m}")
    n = len(series)
    if n < m:
        raise ValueError(f"Series length {n} must be >= embedding order m={m}")

    # Build a lookup from pattern tuple to index for O(1) counting
    all_patterns = _get_ordinal_patterns(m)
    pattern_index = {p: i for i, p in enumerate(all_patterns)}
    counts = np.zeros(len(all_patterns), dtype=np.float64)

    for i in range(n - m + 1):
        window = series[i : i + m]
        # stable argsort: ties broken by earlier position
        rank = tuple(int(r) for r in np.argsort(window, kind="stable"))
        counts[pattern_index[rank]] += 1

    total = counts.sum()
    if total == 0:
        return 0.0

    p = counts[counts > 0] / total
    h_raw = -float(np.sum(p * np.log(p)))
    h_max = float(np.log(len(all_patterns)))  # = log(m!)
    if h_max < 1e-15:
        return 0.0
    return min(h_raw / h_max, 1.0)


def _choose_embedding_order(n: int) -> int:
    """Select a safe embedding order given series length *n*.

    Thresholds from Bandt & Pompe (2002) and the development plan:

    * n >= 1000 → m = 5
    * n >= 100  → m = 4
    * n >= 20   → m = 3

    Args:
        n: Number of observations.

    Returns:
        Embedding order m.
    """
    if n >= 1000:
        return 5
    if n >= 100:
        return 4
    return 3


def _permutation_entropy_scorer(
    series: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Normalised permutation entropy scorer (Bandt & Pompe, 2002).

    Implements :class:`SeriesDiagnosticScorer`.  Embedding order is chosen
    automatically from series length (see :func:`_choose_embedding_order`).
    Returns the normalised PE value in [0, 1].

    A value near 0 indicates a highly regular (predictable) series.
    A value near 1 indicates maximum ordinal complexity (stochastic-like).

    Args:
        series: 1-D float array, length >= 8.
        random_state: Unused; present for interface consistency.

    Returns:
        Normalised permutation entropy in [0, 1].
    """
    del random_state
    if series.ndim != 1 or len(series) < 8:
        raise ValueError(f"series must be 1-D with at least 8 samples; got shape {series.shape}")
    m = _choose_embedding_order(len(series))
    return _compute_permutation_entropy(series, m=m)


def _spectral_entropy_scorer(
    series: np.ndarray,
    *,
    random_state: int = 42,
) -> float:
    """Normalised spectral entropy scorer (Welch PSD, natural-log base).

    Implements :class:`SeriesDiagnosticScorer`.  Uses
    :func:`~forecastability.spectral_utils.compute_normalised_psd` then
    normalises by ``log(N_bins)`` where ``N_bins`` is the number of frequency
    bins in the Welch estimate.

    A value near 0 indicates a spectrally concentrated (predictable) series.
    A value near 1 indicates a flat spectrum (white-noise-like).

    Args:
        series: 1-D float array, length >= 8.
        random_state: Unused; present for interface consistency.

    Returns:
        Normalised spectral entropy in [0, 1].
    """
    del random_state
    _, p = compute_normalised_psd(series)
    h = spectral_entropy(p, base=np.e)
    h_max = float(np.log(len(p)))
    if h_max < 1e-15:
        return 0.0
    return min(h / h_max, 1.0)



# ---------------------------------------------------------------------------
# Default registry factory
# ---------------------------------------------------------------------------


def default_registry() -> ScorerRegistry:
    """Return a :class:`ScorerRegistry` pre-populated with the five built-in scorers.

    Built-in scorers:

    ============  ============  ========================================
    Name          Family        Description
    ============  ============  ========================================
    ``mi``        nonlinear     kNN mutual information (n_neighbors=8)
    ``pearson``   linear        Absolute Pearson correlation
    ``spearman``  rank          Absolute Spearman rank correlation
    ``kendall``   rank          Absolute Kendall tau-b correlation
    ``distance``  bounded_nonlinear  Distance correlation (energy-distance)
    ============  =================  ========================================

    Returns:
        A new :class:`ScorerRegistry` with all built-in scorers registered.
    """
    registry = ScorerRegistry()
    registry.register(
        "mi",
        _mi_scorer,
        family="nonlinear",
        description="kNN mutual information (n_neighbors=8)",
    )
    registry.register(
        "pearson",
        _pearson_scorer,
        family="linear",
        description="Absolute Pearson correlation",
    )
    registry.register(
        "spearman",
        _spearman_scorer,
        family="rank",
        description="Absolute Spearman rank correlation",
    )
    registry.register(
        "kendall",
        _kendall_scorer,
        family="rank",
        description="Absolute Kendall tau-b correlation",
    )
    registry.register(
        "distance",
        _distance_scorer,
        family="bounded_nonlinear",
        description="Distance correlation (energy-distance)",
    )
    registry.register(
        "permutation_entropy",
        _permutation_entropy_scorer,
        family="nonlinear",
        description="Normalised permutation entropy (Bandt & Pompe, 2002)",
        kind="univariate",
    )
    registry.register(
        "spectral_entropy",
        _spectral_entropy_scorer,
        family="nonlinear",
        description="Normalised spectral entropy from Welch PSD",
        kind="univariate",
    )
    return registry
