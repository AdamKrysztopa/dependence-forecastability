"""Scorer contracts for method-independent dependence measures.

These are typed contracts (Protocols and a frozen metadata value object) that
adapters and services implement or consume.  They live in ``ports`` so the
inner ring depends only inward (ports -> domain + ports).  Concrete scorer
functions and the registry stay in :mod:`forecastability.metrics.scorers`,
which imports these contracts from here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

import numpy as np

__all__ = [
    "DependenceScorer",
    "ScorerInfo",
    "SeriesDiagnosticScorer",
]


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
    kind: Literal["bivariate", "univariate", "diagnostic"] = "bivariate"
    experimental: bool = False
