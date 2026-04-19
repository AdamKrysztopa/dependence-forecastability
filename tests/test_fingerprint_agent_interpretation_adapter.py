"""Unit tests for fingerprint A3 interpretation adapter (V3_1-F05.1)."""

from __future__ import annotations

import pytest

from forecastability.adapters.agents.fingerprint_agent_interpretation_adapter import (
    FingerprintAgentInterpretation,
    interpret_fingerprint_batch,
    interpret_fingerprint_payload,
)
from forecastability.adapters.agents.fingerprint_agent_payload_models import (
    fingerprint_agent_payload,
)
from forecastability.adapters.agents.fingerprint_summary_serializer import (
    serialise_fingerprint_payload,
)
from forecastability.utils.types import (
    AmiGeometryCurvePoint,
    AmiInformationGeometry,
    FingerprintBundle,
    ForecastabilityFingerprint,
    RoutingRecommendation,
)


def _make_bundle(
    *,
    structure: str = "monotonic",
    mass: float = 0.20,
    horizon: int = 8,
    nonlinear_share: float = 0.08,
    signal_to_noise: float = 0.36,
    directness_ratio: float | None = 0.75,
    informative_horizons: list[int] | None = None,
    primary_families: list[str] | None = None,
    caution_flags: list[str] | None = None,
    confidence_label: str = "high",
) -> FingerprintBundle:
    informative = informative_horizons or [1, 2, 3, 8]
    geometry = AmiInformationGeometry(
        signal_to_noise=signal_to_noise,
        information_horizon=horizon,
        information_structure=structure,  # type: ignore[arg-type]
        informative_horizons=list(informative),
        curve=[
            AmiGeometryCurvePoint(
                horizon=item,
                ami_raw=0.16,
                ami_bias=0.03,
                ami_corrected=0.13,
                tau=0.02,
                accepted=item in informative,
                valid=True,
            )
            for item in range(1, horizon + 1)
        ],
    )
    fp = ForecastabilityFingerprint(
        information_mass=mass,
        information_horizon=horizon,
        information_structure=structure,  # type: ignore[arg-type]
        nonlinear_share=nonlinear_share,
        signal_to_noise=signal_to_noise,
        directness_ratio=directness_ratio,
        informative_horizons=list(informative),
    )
    rec = RoutingRecommendation(
        primary_families=primary_families or ["arima"],  # type: ignore[list-item]
        secondary_families=["ets"],
        confidence_label=confidence_label,  # type: ignore[arg-type]
        caution_flags=caution_flags or [],  # type: ignore[list-item]
        rationale=["test rationale"],
    )
    return FingerprintBundle(
        target_name="interp_test",
        geometry=geometry,
        fingerprint=fp,
        recommendation=rec,
        profile_summary={"n_sig_lags": 4},
    )


class TestInterpretFingerprintPayload:
    """Test the A3 interpretation builder."""

    def test_returns_interpretation_model(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert isinstance(result, FingerprintAgentInterpretation)

    def test_structure_bucket_propagated(self) -> None:
        bundle = _make_bundle(structure="periodic")
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert result.structure_bucket == "periodic"

    def test_confidence_label_propagated_unchanged(self) -> None:
        bundle = _make_bundle(confidence_label="low")
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert result.confidence_label == "low"

    def test_primary_families_propagated_unchanged(self) -> None:
        bundle = _make_bundle(primary_families=["tbats", "harmonic_regression"])
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert result.primary_families == ["tbats", "harmonic_regression"]

    def test_target_name_propagated(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert result.source_target_name == "interp_test"

    def test_deterministic_summary_contains_structure(self) -> None:
        bundle = _make_bundle(structure="mixed")
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert "mixed" in result.deterministic_summary

    def test_none_structure_produces_cautionary_narrative(self) -> None:
        bundle = _make_bundle(
            structure="none",
            mass=0.0,
            horizon=0,
            nonlinear_share=0.0,
            informative_horizons=[],
            primary_families=["naive"],
        )
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert result.cautionary_narrative is not None
        assert result.rich_signal_narrative is None

    def test_monotonic_high_mass_produces_rich_narrative(self) -> None:
        bundle = _make_bundle(
            structure="monotonic",
            mass=0.25,  # > 0.15 threshold → "high" bucket
        )
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert result.rich_signal_narrative is not None

    def test_low_mass_produces_cautionary_narrative(self) -> None:
        bundle = _make_bundle(
            structure="monotonic",
            mass=0.02,  # < 0.05 threshold → "low" bucket
        )
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert result.cautionary_narrative is not None

    def test_caution_flags_propagated(self) -> None:
        bundle = _make_bundle(
            caution_flags=["near_threshold", "mixed_structure"],
            confidence_label="medium",
        )
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert "near_threshold" in result.caution_flags
        assert "mixed_structure" in result.caution_flags

    def test_evidence_informative_horizon_count(self) -> None:
        bundle = _make_bundle(informative_horizons=[1, 2, 5, 6, 7])
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert result.evidence.informative_horizon_count == 5

    def test_evidence_has_directness_ratio_flag(self) -> None:
        bundle_with = _make_bundle(directness_ratio=0.6)
        bundle_without = _make_bundle(directness_ratio=None)

        result_with = interpret_fingerprint_payload(fingerprint_agent_payload(bundle_with))
        result_without = interpret_fingerprint_payload(fingerprint_agent_payload(bundle_without))

        assert result_with.evidence.has_directness_ratio is True
        assert result_without.evidence.has_directness_ratio is False

    def test_evidence_has_signal_to_noise_bucket(self) -> None:
        bundle = _make_bundle(signal_to_noise=0.05)
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert result.evidence.signal_to_noise_bucket == "low"

    def test_source_payload_type_constant(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle)
        result = interpret_fingerprint_payload(payload)

        assert result.source_payload_type == "FingerprintAgentPayload"


class TestInterpretFromSerialisedSummary:
    """Test that A3 can reconstruct from A2 serialised input."""

    def test_interpret_from_serialised_summary(self) -> None:
        bundle = _make_bundle(structure="periodic")
        payload = fingerprint_agent_payload(bundle)
        serialised = serialise_fingerprint_payload(payload)

        result = interpret_fingerprint_payload(serialised)

        assert result.structure_bucket == "periodic"
        assert result.source_serialised_at == serialised.serialised_at

    def test_serialised_at_propagated(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle)
        serialised = serialise_fingerprint_payload(payload)

        result = interpret_fingerprint_payload(serialised)

        assert result.source_serialised_at is not None


class TestInterpretFingerprintBatch:
    """Test batch interpretation."""

    def test_batch_length_preserved(self) -> None:
        from forecastability.adapters.agents.fingerprint_agent_interpretation_adapter import (
            FingerprintInterpretationInput,
        )

        payloads: list[FingerprintInterpretationInput] = [
            fingerprint_agent_payload(_make_bundle(structure="monotonic")),
            fingerprint_agent_payload(_make_bundle(structure="periodic")),
            fingerprint_agent_payload(
                _make_bundle(
                    structure="none",
                    mass=0.0,
                    horizon=0,
                    nonlinear_share=0.0,
                    informative_horizons=[],
                )
            ),
        ]

        results = interpret_fingerprint_batch(payloads)

        assert len(results) == 3

    def test_batch_structures_preserved(self) -> None:
        from forecastability.adapters.agents.fingerprint_agent_interpretation_adapter import (
            FingerprintInterpretationInput,
        )

        structures = ["monotonic", "periodic", "mixed"]
        payloads: list[FingerprintInterpretationInput] = [
            fingerprint_agent_payload(_make_bundle(structure=s)) for s in structures
        ]

        results = interpret_fingerprint_batch(payloads)

        assert [r.structure_bucket for r in results] == structures


class TestInterpretFingerprintTypeError:
    """Test error handling for unsupported input types."""

    def test_type_error_on_unsupported_input(self) -> None:
        with pytest.raises(TypeError):
            interpret_fingerprint_payload("not a valid input")  # type: ignore[arg-type]
