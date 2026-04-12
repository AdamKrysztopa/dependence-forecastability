"""Scorer registry for method-independent dependence measures."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

import numpy as np
from scipy.spatial.distance import pdist, squareform
from scipy.stats import kendalltau, spearmanr
from sklearn.feature_selection import mutual_info_regression


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
    return registry
