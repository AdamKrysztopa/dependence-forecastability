"""Tests for the routing policy audit service (plan v0.3.3 §2.2–2.3)."""

from __future__ import annotations

import pytest

from forecastability.services.routing_confidence_calibration_service import (
    calibrate_confidence_label,
)
from forecastability.services.routing_policy_audit_service import (
    audit_routing_case,
    build_routing_threshold_vector,
)
from forecastability.services.routing_policy_service import (
    RoutingPolicyConfig,
    route_fingerprint,
)
from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.utils.synthetic import generate_routing_validation_archetypes
from forecastability.utils.types import (
    ForecastabilityFingerprint,
    RoutingPolicyAuditConfig,
    RoutingRecommendation,
    RoutingValidationCase,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fp(
    *,
    structure: str = "monotonic",
    mass: float = 0.20,
    nl_share: float = 0.05,
    signal_to_noise: float = 0.50,
    horizon: int = 5,
    informative_horizons: list[int] | None = None,
    directness_ratio: float | None = None,
    metadata: dict[str, str | int | float] | None = None,
) -> ForecastabilityFingerprint:
    """Convenience fingerprint factory for audit-service tests."""
    return ForecastabilityFingerprint(
        information_mass=mass,
        information_horizon=horizon,
        information_structure=structure,  # type: ignore[arg-type]
        nonlinear_share=nl_share,
        signal_to_noise=signal_to_noise,
        directness_ratio=directness_ratio,
        informative_horizons=informative_horizons or [1, 2, 3, 4, 5],
        metadata=metadata or {},
    )


def _route(fingerprint: ForecastabilityFingerprint) -> RoutingRecommendation:
    return route_fingerprint(fingerprint)


_AUDIT_CFG = RoutingPolicyAuditConfig()


# ---------------------------------------------------------------------------
# build_routing_threshold_vector tests
# ---------------------------------------------------------------------------


class TestBuildRoutingThresholdVector:
    def test_returns_expected_keys_without_directness(self) -> None:
        fp = _fp(directness_ratio=None)
        vector = build_routing_threshold_vector(fp)
        assert set(vector.keys()) == {
            "information_mass_low_max",
            "information_mass_high_min",
            "nonlinear_share",
        }

    def test_includes_directness_key_when_present(self) -> None:
        fp = _fp(directness_ratio=0.70)
        vector = build_routing_threshold_vector(fp)
        assert "directness_ratio" in vector

    def test_threshold_values_match_routing_policy_defaults(self) -> None:
        fp = _fp(directness_ratio=0.70)
        vector = build_routing_threshold_vector(fp)
        cfg = RoutingPolicyConfig()
        assert vector["information_mass_low_max"] == cfg.low_mass_max
        assert vector["information_mass_high_min"] == cfg.high_mass_min
        assert vector["nonlinear_share"] == cfg.high_nonlinear_share_min
        assert vector["directness_ratio"] == cfg.high_directness_min

    def test_custom_routing_config_reflected(self) -> None:
        custom = RoutingPolicyConfig(low_mass_max=0.05, high_mass_min=0.15)
        fp = _fp(directness_ratio=None)
        vector = build_routing_threshold_vector(fp, routing_config=custom)
        assert vector["information_mass_low_max"] == 0.05
        assert vector["information_mass_high_min"] == 0.15


# ---------------------------------------------------------------------------
# Four-outcome predicate tests
# ---------------------------------------------------------------------------


class TestPassOutcome:
    def test_far_from_threshold_and_stable_produces_pass(self) -> None:
        """A clearly monotonic fingerprint far from all thresholds should pass."""
        fp = _fp(
            structure="monotonic",
            mass=0.35,  # far above high_mass_min (0.10)
            nl_share=0.05,  # far below high_nonlinear_share_min (0.30)
            signal_to_noise=0.80,
            informative_horizons=[1, 2, 3, 4, 5, 6, 7],
        )
        rec = _route(fp)
        vector = build_routing_threshold_vector(fp)
        case = audit_routing_case(
            case_name="test_pass",
            source_kind="synthetic",
            expected_primary_families=list(rec.primary_families),  # guaranteed match
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=vector,
            config=_AUDIT_CFG,
        )
        assert case.outcome == "pass"

    def test_pass_case_returns_frozen_validation_case(self) -> None:
        fp = _fp(mass=0.35, nl_share=0.05, signal_to_noise=0.80)
        rec = _route(fp)
        vector = build_routing_threshold_vector(fp)
        case = audit_routing_case(
            case_name="test_return_type",
            source_kind="synthetic",
            expected_primary_families=list(rec.primary_families),
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=vector,
        )
        assert isinstance(case, RoutingValidationCase)
        assert case.case_name == "test_return_type"
        assert case.source_kind == "synthetic"


class TestFailOutcome:
    def test_disjoint_families_produce_fail(self) -> None:
        """Expected families disjoint from observed must yield 'fail'."""
        fp = _fp(
            structure="monotonic",
            mass=0.35,
            nl_share=0.05,
            signal_to_noise=0.80,
        )
        rec = _route(fp)
        # Declare expected families from the OPPOSITE routing arm
        case = audit_routing_case(
            case_name="test_fail",
            source_kind="synthetic",
            expected_primary_families=["tree_on_lags", "tcn"],  # nonlinear arm
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=build_routing_threshold_vector(fp),
        )
        assert case.outcome == "fail"

    def test_wrong_expected_families_real_source(self) -> None:
        fp = _fp(structure="periodic", mass=0.18, nl_share=0.05)
        rec = _route(fp)
        case = audit_routing_case(
            case_name="real_fail",
            source_kind="real",
            expected_primary_families=["arima"],  # periodic arm produces seasonal families
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=build_routing_threshold_vector(fp),
        )
        # periodic arm produces ["seasonal_naive", "harmonic_regression", "tbats"]
        # which does not intersect ["arima"]
        assert case.outcome == "fail"


class TestAbstainOutcome:
    def test_empty_observed_produces_abstain(self) -> None:
        """When the recommendation carries no primary families the outcome is abstain."""
        fp = _fp(mass=0.35, nl_share=0.05)
        rec = RoutingRecommendation(
            primary_families=[],
            secondary_families=[],
            rationale=["test"],
            caution_flags=[],
            confidence_label="low",
            metadata={},
        )
        case = audit_routing_case(
            case_name="test_abstain",
            source_kind="synthetic",
            expected_primary_families=["arima"],
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=build_routing_threshold_vector(fp),
        )
        assert case.outcome == "abstain"
        assert case.observed_primary_families == []


class TestDowngradeOutcome:
    def test_near_threshold_with_matching_family_produces_downgrade(self) -> None:
        """A fingerprint sitting right on a threshold boundary should downgrade.

        We place mass just above high_mass_min (0.10) by exactly the perturbation
        radius (0.05), which means at least one corner of the stability grid will
        dip below the threshold and flip the routing arm — reducing rule_stability
        below tau_stable (0.80).  Alternatively we can set margin < tau_margin.
        """
        # Place mass exactly at high_mass_min (0.10) — distance to that threshold is 0
        # This guarantees threshold_margin = 0 < tau_margin (0.05)
        fp = _fp(
            structure="monotonic",
            mass=0.10,  # exactly at threshold → margin = 0
            nl_share=0.05,
            signal_to_noise=0.50,
            informative_horizons=[1, 2, 3, 4, 5],
        )
        rec = _route(fp)
        vector = build_routing_threshold_vector(fp)
        case = audit_routing_case(
            case_name="test_downgrade",
            source_kind="synthetic",
            expected_primary_families=list(rec.primary_families),
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=vector,
            config=_AUDIT_CFG,
        )
        # margin = 0.0 < tau_margin = 0.05 → must be downgrade (not pass)
        assert case.outcome == "downgrade"

    def test_downgrade_is_not_fail(self) -> None:
        """Downgrade means the family intersection is non-empty."""
        fp = _fp(structure="monotonic", mass=0.10, nl_share=0.05)
        rec = _route(fp)
        case = audit_routing_case(
            case_name="downgrade_not_fail",
            source_kind="synthetic",
            expected_primary_families=list(rec.primary_families),
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=build_routing_threshold_vector(fp),
        )
        assert case.outcome in ("pass", "downgrade")
        assert bool(set(case.expected_primary_families) & set(case.observed_primary_families))


class TestConfidenceCalibration:
    def test_audit_case_recalibrates_confidence_for_near_threshold_bundle(self) -> None:
        panel = generate_routing_validation_archetypes(n=200, seed=42)
        series, metadata = panel["weak_seasonal_near_threshold"]
        bundle = run_forecastability_fingerprint(
            series,
            target_name="weak_seasonal_near_threshold",
            max_lag=10,
            n_surrogates=99,
            random_state=42,
        )

        case = audit_routing_case(
            case_name="weak_seasonal_near_threshold",
            source_kind="synthetic",
            expected_primary_families=metadata.expected_primary_families,
            fingerprint=bundle.fingerprint,
            recommendation=bundle.recommendation,
            threshold_vector=build_routing_threshold_vector(bundle.fingerprint),
        )
        expected_label = calibrate_confidence_label(
            fingerprint_penalty_count=case.fingerprint_penalty_count,
            threshold_margin=case.threshold_margin,
            rule_stability=case.rule_stability,
            primary_families=case.observed_primary_families,
        )

        assert expected_label != bundle.recommendation.confidence_label
        assert case.confidence_label == expected_label


# ---------------------------------------------------------------------------
# Threshold margin tests
# ---------------------------------------------------------------------------


class TestThresholdMargin:
    def test_margin_is_positive_float(self) -> None:
        fp = _fp(mass=0.35, nl_share=0.05)
        rec = _route(fp)
        case = audit_routing_case(
            case_name="margin_check",
            source_kind="synthetic",
            expected_primary_families=list(rec.primary_families),
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=build_routing_threshold_vector(fp),
        )
        assert case.threshold_margin >= 0.0

    def test_margin_zero_when_exactly_at_threshold(self) -> None:
        """mass = high_mass_min (0.10) → |mass - high_mass_min| / 1.0 = 0.0."""
        fp = _fp(mass=0.10, nl_share=0.05, directness_ratio=None)
        rec = _route(fp)
        case = audit_routing_case(
            case_name="margin_zero",
            source_kind="synthetic",
            expected_primary_families=list(rec.primary_families),
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=build_routing_threshold_vector(fp),
        )
        assert case.threshold_margin == pytest.approx(0.0, abs=1e-10)


# ---------------------------------------------------------------------------
# Rule stability field tests
# ---------------------------------------------------------------------------


class TestRuleStabilityField:
    def test_stability_in_unit_interval(self) -> None:
        fp = _fp(mass=0.35, nl_share=0.05)
        rec = _route(fp)
        case = audit_routing_case(
            case_name="stability_range",
            source_kind="synthetic",
            expected_primary_families=list(rec.primary_families),
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=build_routing_threshold_vector(fp),
        )
        assert 0.0 <= case.rule_stability <= 1.0

    def test_fingerprint_far_from_all_thresholds_has_high_stability(self) -> None:
        """A fingerprint well inside a routing arm should be maximally stable."""
        fp = _fp(mass=0.50, nl_share=0.05, signal_to_noise=0.80)
        rec = _route(fp)
        case = audit_routing_case(
            case_name="high_stability",
            source_kind="synthetic",
            expected_primary_families=list(rec.primary_families),
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=build_routing_threshold_vector(fp),
        )
        assert case.rule_stability == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Validation / error-handling tests
# ---------------------------------------------------------------------------


class TestAuditInputValidation:
    def test_empty_expected_families_raises(self) -> None:
        fp = _fp(mass=0.35, nl_share=0.05)
        rec = _route(fp)
        with pytest.raises(ValueError):
            audit_routing_case(
                case_name="bad_case",
                source_kind="synthetic",
                expected_primary_families=[],
                fingerprint=fp,
                recommendation=rec,
                threshold_vector=build_routing_threshold_vector(fp),
            )

    def test_does_not_mutate_input_fingerprint(self) -> None:
        fp = _fp(mass=0.35, nl_share=0.05)
        rec = _route(fp)
        original_mass = fp.information_mass
        audit_routing_case(
            case_name="no_mutation",
            source_kind="synthetic",
            expected_primary_families=list(rec.primary_families),
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=build_routing_threshold_vector(fp),
        )
        assert fp.information_mass == original_mass

    def test_does_not_mutate_input_recommendation(self) -> None:
        fp = _fp(mass=0.35, nl_share=0.05)
        rec = _route(fp)
        original_families = list(rec.primary_families)
        audit_routing_case(
            case_name="no_mutation_rec",
            source_kind="synthetic",
            expected_primary_families=original_families,
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=build_routing_threshold_vector(fp),
        )
        assert list(rec.primary_families) == original_families


# ---------------------------------------------------------------------------
# Optional metadata / notes fields
# ---------------------------------------------------------------------------


class TestOptionalFields:
    def test_notes_attached_to_case(self) -> None:
        fp = _fp(mass=0.35, nl_share=0.05)
        rec = _route(fp)
        case = audit_routing_case(
            case_name="with_notes",
            source_kind="synthetic",
            expected_primary_families=list(rec.primary_families),
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=build_routing_threshold_vector(fp),
            notes=["first note", "second note"],
        )
        assert case.notes == ["first note", "second note"]

    def test_metadata_attached_to_case(self) -> None:
        fp = _fp(mass=0.35, nl_share=0.05)
        rec = _route(fp)
        case = audit_routing_case(
            case_name="with_meta",
            source_kind="real",
            expected_primary_families=list(rec.primary_families),
            fingerprint=fp,
            recommendation=rec,
            threshold_vector=build_routing_threshold_vector(fp),
            metadata={"source": "air_passengers", "n": 144},
        )
        assert case.metadata["source"] == "air_passengers"
        assert case.metadata["n"] == 144
