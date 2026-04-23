"""Tests for the rule-stability subroutine (plan v0.3.3 §2.4)."""

from __future__ import annotations

import pytest

from forecastability.services.routing_policy_audit_service import compute_rule_stability

# ---------------------------------------------------------------------------
# Deterministic routing callable helpers
# ---------------------------------------------------------------------------


def _always_arima(coords: dict[str, float]) -> list[str]:
    """Routing callable that never changes its output."""
    return ["arima", "ets"]


def _threshold_sensitive(coords: dict[str, float]) -> list[str]:
    """Routing callable that changes output based on a coordinate threshold."""
    if coords.get("information_mass", 0.0) >= 0.10:
        return ["arima", "ets"]
    return ["naive"]


def _mass_and_nonlinear_sensitive(coords: dict[str, float]) -> list[str]:
    """Two-threshold routing callable for grid interaction tests."""
    if coords.get("information_mass", 0.0) < 0.03:
        return ["naive"]
    if coords.get("nonlinear_share", 0.0) >= 0.30:
        return ["tree_on_lags"]
    return ["arima"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDeltaValidation:
    def test_negative_delta_raises(self) -> None:
        with pytest.raises(ValueError, match="delta must be > 0"):
            compute_rule_stability({"x": 0.5}, routing_callable=_always_arima, delta=-0.1)

    def test_zero_delta_raises(self) -> None:
        with pytest.raises(ValueError, match="delta must be > 0"):
            compute_rule_stability({"x": 0.5}, routing_callable=_always_arima, delta=0.0)


class TestPerfectStability:
    def test_invariant_callable_returns_one(self) -> None:
        """A routing callable that never changes must yield stability 1.0."""
        coords = {"information_mass": 0.50, "nonlinear_share": 0.10}
        score = compute_rule_stability(coords, routing_callable=_always_arima, delta=0.05)
        assert score == 1.0

    def test_single_coordinate_invariant(self) -> None:
        score = compute_rule_stability(
            {"information_mass": 0.50},
            routing_callable=_always_arima,
            delta=0.05,
        )
        assert score == 1.0


class TestPartialStability:
    def test_callable_changes_at_threshold(self) -> None:
        """Points that cross the 0.10 threshold should flip the routing decision.

        centre = 0.12 (above 0.10 → arima)
        delta  = 0.05
        Grid points (K=1): centre=0.12, low=0.07, high=0.17
        low=0.07 < 0.10 → naive (flips)
        high=0.17 >= 0.10 → arima (matches)
        Stable = 2/3 ≈ 0.6667 (centre + high match, low does not)
        """
        coords = {"information_mass": 0.12}
        score = compute_rule_stability(
            coords,
            routing_callable=_threshold_sensitive,
            delta=0.05,
        )
        # centre + 1 of 2 corners = 2/3 of grid
        assert abs(score - 2 / 3) < 1e-9

    def test_centre_far_from_threshold_maximises_stability(self) -> None:
        """Centre far from 0.10 threshold: all points should agree."""
        coords = {"information_mass": 0.50}
        score = compute_rule_stability(
            coords,
            routing_callable=_threshold_sensitive,
            delta=0.05,
        )
        assert score == 1.0

    def test_two_coordinate_grid_size(self) -> None:
        """K=2 → 2^2 + 1 = 5 grid points; centre far from both thresholds → 1.0."""
        coords = {"information_mass": 0.50, "nonlinear_share": 0.10}
        score = compute_rule_stability(
            coords,
            routing_callable=_mass_and_nonlinear_sensitive,
            delta=0.05,
        )
        # All 5 points should agree (all are > 0.03 mass and < 0.30 nonlinear)
        assert score == 1.0


class TestDeterminism:
    def test_same_result_on_repeated_calls(self) -> None:
        coords = {"information_mass": 0.12, "nonlinear_share": 0.28}
        scores = [
            compute_rule_stability(
                coords,
                routing_callable=_mass_and_nonlinear_sensitive,
                delta=0.05,
            )
            for _ in range(5)
        ]
        assert len(set(scores)) == 1

    def test_key_order_invariant(self) -> None:
        """The score must be identical regardless of input dict insertion order."""
        coords_ab = {"information_mass": 0.12, "nonlinear_share": 0.28}
        coords_ba = {"nonlinear_share": 0.28, "information_mass": 0.12}
        score_ab = compute_rule_stability(
            coords_ab, routing_callable=_mass_and_nonlinear_sensitive, delta=0.05
        )
        score_ba = compute_rule_stability(
            coords_ba, routing_callable=_mass_and_nonlinear_sensitive, delta=0.05
        )
        assert score_ab == score_ba


class TestGridSize:
    def test_k1_grid_has_three_points(self) -> None:
        """K=1: corner-plus-center grid has 2^1 + 1 = 3 points."""
        call_count = 0

        def counting_callable(coords: dict[str, float]) -> list[str]:
            nonlocal call_count
            call_count += 1
            return ["arima"]

        compute_rule_stability({"x": 0.5}, routing_callable=counting_callable, delta=0.05)
        assert call_count == 3

    def test_k2_grid_has_five_points(self) -> None:
        """K=2: corner-plus-center grid has 2^2 + 1 = 5 points."""
        call_count = 0

        def counting_callable(coords: dict[str, float]) -> list[str]:
            nonlocal call_count
            call_count += 1
            return ["arima"]

        compute_rule_stability(
            {"x": 0.5, "y": 0.3},
            routing_callable=counting_callable,
            delta=0.05,
        )
        assert call_count == 5

    def test_k3_grid_has_nine_points(self) -> None:
        """K=3: corner-plus-center grid has 2^3 + 1 = 9 points."""
        call_count = 0

        def counting_callable(coords: dict[str, float]) -> list[str]:
            nonlocal call_count
            call_count += 1
            return ["arima"]

        compute_rule_stability(
            {"x": 0.5, "y": 0.3, "z": 0.7},
            routing_callable=counting_callable,
            delta=0.05,
        )
        assert call_count == 9
