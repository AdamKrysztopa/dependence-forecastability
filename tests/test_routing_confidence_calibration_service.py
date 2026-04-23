"""Tests for the routing confidence calibration service (plan v0.3.3 §2.5)."""

from __future__ import annotations

from forecastability.services.routing_confidence_calibration_service import (
    calibrate_confidence_label,
)
from forecastability.utils.types import RoutingPolicyAuditConfig

_CFG = RoutingPolicyAuditConfig()


class TestAbstainLabel:
    def test_empty_primary_families_always_abstain(self) -> None:
        label = calibrate_confidence_label(
            fingerprint_penalty_count=0,
            threshold_margin=1.0,
            rule_stability=1.0,
            primary_families=[],
            config=_CFG,
        )
        assert label == "abstain"

    def test_empty_families_overrides_otherwise_high_signals(self) -> None:
        """The abstain row is first in the decision table; it must win unconditionally."""
        label = calibrate_confidence_label(
            fingerprint_penalty_count=0,
            threshold_margin=0.99,
            rule_stability=0.99,
            primary_families=[],
        )
        assert label == "abstain"


class TestHighLabel:
    def test_zero_penalty_far_from_threshold_high_stability(self) -> None:
        label = calibrate_confidence_label(
            fingerprint_penalty_count=0,
            threshold_margin=_CFG.tau_margin,  # exactly at threshold
            rule_stability=_CFG.tau_stable_high,  # exactly at high threshold
            primary_families=["arima"],
        )
        assert label == "high"

    def test_zero_penalty_above_all_high_thresholds(self) -> None:
        label = calibrate_confidence_label(
            fingerprint_penalty_count=0,
            threshold_margin=0.50,
            rule_stability=1.0,
            primary_families=["ets", "arima"],
        )
        assert label == "high"

    def test_one_penalty_never_high(self) -> None:
        """Penalty count 1 must not reach 'high', even with ideal margin and stability."""
        label = calibrate_confidence_label(
            fingerprint_penalty_count=1,
            threshold_margin=0.50,
            rule_stability=1.0,
            primary_families=["arima"],
        )
        assert label != "high"


class TestMediumLabel:
    def test_one_penalty_medium_margin_and_stability(self) -> None:
        label = calibrate_confidence_label(
            fingerprint_penalty_count=1,
            threshold_margin=_CFG.tau_margin_medium,  # exactly at medium margin floor
            rule_stability=_CFG.tau_stable_medium,    # exactly at medium stability floor
            primary_families=["arima"],
        )
        assert label == "medium"

    def test_zero_penalty_medium_when_stability_below_high_threshold(self) -> None:
        """Zero penalty but stability < tau_stable_high falls through to medium."""
        label = calibrate_confidence_label(
            fingerprint_penalty_count=0,
            threshold_margin=_CFG.tau_margin,
            rule_stability=_CFG.tau_stable_medium,  # below tau_stable_high
            primary_families=["arima"],
        )
        assert label == "medium"

    def test_two_penalties_never_medium(self) -> None:
        """Penalty count >= 2 must always produce 'low'."""
        label = calibrate_confidence_label(
            fingerprint_penalty_count=2,
            threshold_margin=0.50,
            rule_stability=1.0,
            primary_families=["arima"],
        )
        assert label == "low"


class TestLowLabel:
    def test_high_penalty_always_low(self) -> None:
        label = calibrate_confidence_label(
            fingerprint_penalty_count=3,
            threshold_margin=0.50,
            rule_stability=1.0,
            primary_families=["arima"],
        )
        assert label == "low"

    def test_low_stability_produces_low(self) -> None:
        label = calibrate_confidence_label(
            fingerprint_penalty_count=0,
            threshold_margin=0.50,
            rule_stability=0.10,  # well below tau_stable_medium
            primary_families=["arima"],
        )
        assert label == "low"

    def test_low_margin_produces_low(self) -> None:
        label = calibrate_confidence_label(
            fingerprint_penalty_count=0,
            threshold_margin=0.001,  # well below tau_margin_medium
            rule_stability=1.0,
            primary_families=["arima"],
        )
        assert label == "low"


class TestDecisionTableOrder:
    def test_first_matching_row_wins_high_over_medium(self) -> None:
        """When all high conditions hold, label must be 'high' not 'medium'."""
        label = calibrate_confidence_label(
            fingerprint_penalty_count=0,
            threshold_margin=_CFG.tau_margin + 0.01,
            rule_stability=_CFG.tau_stable_high + 0.001,
            primary_families=["arima"],
        )
        assert label == "high"

    def test_custom_config_respected(self) -> None:
        strict_cfg = RoutingPolicyAuditConfig(
            tau_margin=0.10,
            tau_margin_medium=0.05,
            tau_stable=0.90,
            tau_stable_high=0.98,
            tau_stable_medium=0.80,
        )
        # Below strict high thresholds → not high
        label = calibrate_confidence_label(
            fingerprint_penalty_count=0,
            threshold_margin=0.09,   # below tau_margin (0.10)
            rule_stability=0.98,
            primary_families=["arima"],
            config=strict_cfg,
        )
        assert label != "high"

    def test_result_is_valid_literal_value(self) -> None:
        valid_labels = {"high", "medium", "low", "abstain"}
        for penalty in (0, 1, 2):
            for margin in (0.001, 0.03, 0.10):
                for stability in (0.10, 0.75, 1.0):
                    label = calibrate_confidence_label(
                        fingerprint_penalty_count=penalty,
                        threshold_margin=margin,
                        rule_stability=stability,
                        primary_families=["arima"],
                    )
                    assert label in valid_labels
