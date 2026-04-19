"""Unit tests for fingerprint agent payload models (V3_1-F05.1 — A1 layer)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from forecastability.adapters.agents.fingerprint_agent_payload_models import (
    FingerprintAgentPayload,
    fingerprint_agent_payload,
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
    mass: float = 0.12,
    horizon: int = 8,
    nonlinear_share: float = 0.10,
    signal_to_noise: float = 0.35,
    directness_ratio: float | None = 0.72,
    informative_horizons: list[int] | None = None,
    primary_families: list[str] | None = None,
    secondary_families: list[str] | None = None,
    confidence_label: str = "high",
    caution_flags: list[str] | None = None,
    rationale: list[str] | None = None,
) -> FingerprintBundle:
    """Build a minimal :class:`FingerprintBundle` for testing."""
    informative = informative_horizons if informative_horizons is not None else [1, 2, 3, 8]
    geometry = AmiInformationGeometry(
        signal_to_noise=signal_to_noise,
        information_horizon=horizon,
        information_structure=structure,  # type: ignore[arg-type]
        informative_horizons=list(informative),
        curve=[
            AmiGeometryCurvePoint(
                horizon=item,
                ami_raw=0.20,
                ami_bias=0.05,
                ami_corrected=0.15,
                tau=0.04,
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
        secondary_families=secondary_families or ["ets"],  # type: ignore[list-item]
        confidence_label=confidence_label,  # type: ignore[arg-type]
        caution_flags=caution_flags or [],  # type: ignore[list-item]
        rationale=rationale or ["monotonic decay with high directness"],
    )
    return FingerprintBundle(
        target_name="test_series",
        geometry=geometry,
        fingerprint=fp,
        recommendation=rec,
        profile_summary={"n_sig_lags": 4, "max_ami": 0.30},
    )


class TestFingerprintAgentPayloadFields:
    """Test that all four Peter Catt metrics and routing fields are present."""

    def test_four_catt_metrics_present(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle)

        assert payload.information_mass == bundle.fingerprint.information_mass
        assert payload.information_horizon == bundle.fingerprint.information_horizon
        assert payload.information_structure == str(bundle.fingerprint.information_structure)
        assert payload.nonlinear_share == bundle.fingerprint.nonlinear_share

    def test_geometry_fields_present(self) -> None:
        bundle = _make_bundle(signal_to_noise=0.41)
        payload = fingerprint_agent_payload(bundle)

        assert payload.geometry_method == bundle.geometry.method
        assert payload.signal_to_noise == bundle.geometry.signal_to_noise
        assert payload.geometry_information_horizon == bundle.geometry.information_horizon
        assert (
            payload.geometry_information_structure
            == bundle.geometry.information_structure
        )

    def test_routing_fields_present(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle)

        assert payload.primary_families == ["arima"]
        assert payload.secondary_families == ["ets"]
        assert payload.confidence_label == "high"
        assert payload.caution_flags == []
        assert len(payload.rationale) == 1

    def test_informative_horizons_propagated(self) -> None:
        bundle = _make_bundle(informative_horizons=[1, 3, 5])
        payload = fingerprint_agent_payload(bundle)

        assert payload.informative_horizons == [1, 3, 5]

    def test_directness_ratio_none_propagated(self) -> None:
        bundle = _make_bundle(directness_ratio=None)
        payload = fingerprint_agent_payload(bundle)

        assert payload.directness_ratio is None

    def test_target_name_propagated(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle)

        assert payload.target_name == "test_series"

    def test_profile_summary_propagated(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle)

        assert payload.profile_summary == {"n_sig_lags": 4, "max_ami": 0.30}


def test_fingerprint_agent_payload_preserves_bundle_fields() -> None:
    """Payload conversion must preserve deterministic bundle metrics and routing."""
    bundle = _make_bundle(
        structure="mixed",
        mass=0.17,
        horizon=6,
        nonlinear_share=0.42,
        signal_to_noise=0.28,
        directness_ratio=0.33,
        primary_families=["tree_on_lags", "tcn"],
        confidence_label="medium",
        caution_flags=["mixed_structure", "low_directness"],
    )
    payload = fingerprint_agent_payload(bundle)

    assert payload.information_mass == bundle.fingerprint.information_mass
    assert payload.information_horizon == bundle.fingerprint.information_horizon
    assert payload.information_structure == bundle.fingerprint.information_structure
    assert payload.nonlinear_share == bundle.fingerprint.nonlinear_share
    assert payload.signal_to_noise == bundle.geometry.signal_to_noise
    assert payload.primary_families == bundle.recommendation.primary_families
    assert payload.confidence_label == bundle.recommendation.confidence_label


class TestFingerprintAgentPayloadNarrative:
    """Test narrative field handling for strict vs live paths."""

    def test_strict_mode_narrative_is_none(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle, narrative=None)

        assert payload.narrative is None

    def test_live_mode_narrative_propagated(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle, narrative="This series is forecastable.")

        assert payload.narrative == "This series is forecastable."


class TestFingerprintAgentPayloadImmutability:
    """Test frozen / immutability contract."""

    def test_payload_is_frozen(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle)

        with pytest.raises(ValidationError):
            payload.information_mass = 0.5  # noqa: PGH003

    def test_extra_fields_rejected(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle)
        raw = payload.model_dump()
        raw["unexpected_field"] = "oops"

        with pytest.raises(ValidationError):
            FingerprintAgentPayload.model_validate(raw)


class TestFingerprintAgentPayloadJsonRoundtrip:
    """Test JSON serialisation roundtrip."""

    def test_json_roundtrip(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle, narrative="roundtrip test")

        raw = payload.model_dump(mode="json")
        roundtripped = FingerprintAgentPayload.model_validate(json.loads(json.dumps(raw)))

        assert roundtripped == payload

    def test_schema_version_present(self) -> None:
        bundle = _make_bundle()
        payload = fingerprint_agent_payload(bundle)

        assert payload.schema_version == "1"


class TestFingerprintAgentPayloadNoneStructure:
    """Test payload construction for the none-structure case."""

    def test_none_structure_zero_horizon(self) -> None:
        bundle = _make_bundle(
            structure="none",
            mass=0.0,
            horizon=0,
            nonlinear_share=0.0,
            informative_horizons=[],
            primary_families=["naive"],
            caution_flags=[],
        )
        payload = fingerprint_agent_payload(bundle)

        assert payload.information_structure == "none"
        assert payload.information_horizon == 0
        assert payload.informative_horizons == []
        assert payload.information_mass == 0.0
