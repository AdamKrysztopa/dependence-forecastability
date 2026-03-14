"""Tests for the scorer registry module."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.scorers import ScorerRegistry, default_registry


@pytest.fixture()
def registry() -> ScorerRegistry:
    """Return a fresh default registry."""
    return default_registry()


@pytest.fixture()
def sine_pair() -> tuple[np.ndarray, np.ndarray]:
    """Return a simple sinusoidal (past, future) pair."""
    t = np.linspace(0.0, 8 * np.pi, 200)
    past = np.sin(t[:-1])
    future = np.sin(t[1:])
    return past, future


class TestDefaultScorers:
    """All 5 default scorers return float >= 0 on sinusoidal input."""

    @pytest.mark.parametrize("name", ["mi", "pearson", "spearman", "kendall", "distance"])
    def test_scorer_returns_nonnegative_float(
        self,
        registry: ScorerRegistry,
        sine_pair: tuple[np.ndarray, np.ndarray],
        name: str,
    ) -> None:
        info = registry.get(name)
        past, future = sine_pair
        score = info.scorer(past, future, random_state=42)
        assert isinstance(score, float)
        assert score >= 0.0


class TestRegistryContains:
    """__contains__ works for presence and absence."""

    def test_known_scorer(self, registry: ScorerRegistry) -> None:
        assert "mi" in registry

    def test_unknown_scorer(self, registry: ScorerRegistry) -> None:
        assert "nonexistent" not in registry


class TestRegistryGet:
    """get() raises KeyError with a helpful message for unknown names."""

    def test_unknown_raises_keyerror(self, registry: ScorerRegistry) -> None:
        with pytest.raises(KeyError, match="no_such"):
            registry.get("no_such")


class TestDecoratorRegistration:
    """register_scorer decorator registers a scorer."""

    def test_decorator(self) -> None:
        registry = ScorerRegistry()

        @registry.register_scorer("dummy", family="linear", description="test")
        def _dummy(
            past: np.ndarray,
            future: np.ndarray,
            *,
            random_state: int = 42,
        ) -> float:
            del past, future, random_state
            return 1.0

        assert "dummy" in registry
        info = registry.get("dummy")
        assert info.family == "linear"
        assert info.description == "test"


class TestMIReproducibility:
    """MI scorer respects random_state: same state → same result."""

    def test_same_state_same_result(
        self,
        registry: ScorerRegistry,
        sine_pair: tuple[np.ndarray, np.ndarray],
    ) -> None:
        mi = registry.get("mi").scorer
        past, future = sine_pair
        a = mi(past, future, random_state=123)
        b = mi(past, future, random_state=123)
        assert a == b

    def test_different_state_may_differ(
        self,
        registry: ScorerRegistry,
        sine_pair: tuple[np.ndarray, np.ndarray],
    ) -> None:
        mi = registry.get("mi").scorer
        past, future = sine_pair
        a = mi(past, future, random_state=1)
        b = mi(past, future, random_state=9999)
        # They *may* differ; just check both are valid
        assert isinstance(a, float) and a >= 0.0
        assert isinstance(b, float) and b >= 0.0


class TestListScorers:
    """list_scorers returns all registered entries."""

    def test_default_count(self, registry: ScorerRegistry) -> None:
        scorers = registry.list_scorers()
        assert len(scorers) == 5

    def test_names(self, registry: ScorerRegistry) -> None:
        names = {s.name for s in registry.list_scorers()}
        assert names == {"mi", "pearson", "spearman", "kendall", "distance"}


class TestDistanceCorrelationBounded:
    """Distance correlation must return values in [0, 1]."""

    @pytest.mark.parametrize(
        "past,future",
        [
            (np.linspace(0, 1, 50), np.linspace(0, 1, 50)),
            (np.sin(np.linspace(0, 6, 50)), np.cos(np.linspace(0, 6, 50))),
            (
                np.random.default_rng(0).standard_normal(100),
                np.random.default_rng(1).standard_normal(100),
            ),
        ],
        ids=["linear", "trig", "random"],
    )
    def test_distance_correlation_bounded(
        self,
        registry: ScorerRegistry,
        past: np.ndarray,
        future: np.ndarray,
    ) -> None:
        score = registry.get("distance").scorer(past, future, random_state=42)
        assert 0.0 <= score <= 1.0

    def test_distance_family_is_bounded_nonlinear(self, registry: ScorerRegistry) -> None:
        assert registry.get("distance").family == "bounded_nonlinear"


class TestConstantArrayReturnsZero:
    """Scorers return 0.0 when one input is constant (NaN guard)."""

    def test_pearson_constant_array_returns_zero(self, registry: ScorerRegistry) -> None:
        past = np.ones(50)
        future = np.linspace(0, 1, 50)
        score = registry.get("pearson").scorer(past, future, random_state=42)
        assert score == 0.0

    def test_spearman_constant_array_returns_zero(self, registry: ScorerRegistry) -> None:
        past = np.ones(50)
        future = np.linspace(0, 1, 50)
        score = registry.get("spearman").scorer(past, future, random_state=42)
        assert score == 0.0
